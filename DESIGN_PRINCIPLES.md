# Design Principles

Architectural decisions and rejected alternatives. Treat this as the authoritative "why" behind implementation choices.

---

## P1 — Access control is enforced at retrieval, not post-filter

**Decision:** Tag every chunk at ingest time with `allowed_roles` / `allowed_users`. Filter is applied in the pgvector WHERE clause. The retriever never receives unauthorized chunks.

**Policy model:** Allowlist only. A chunk is retrievable iff it has ≥1 tag matching the user's effective policy. No explicit deny at retrieval level.

**Rejected:** Post-filter (retrieve top-k, then drop unauthorized chunks). Rejected because it leaks information through chunk count and LLM context shape, and makes access a soft guarantee rather than a hard boundary.

---

## P2 — Embedding unit is a row, not a column or semantic aggregate

**Decision:** Each DB row is serialized to plain text and embedded as one chunk. Column exclusion list applied at ingest for PII/sensitive fields.

**Implication:** Access tags are applied at row level. The LLM receives isolated rows; cross-row relationships must be inferred from context, not from joined views.

**Rejected:**
- Column-level: loses row context entirely; a retrieved value is meaningless without its neighbors.
- Semantic aggregation (group related rows): better retrieval quality for narrative queries, but chunking logic becomes domain-specific and fragile. Documented as a retrieval quality improvement for post-prototype.

---

## P3 — No SQL tool for the LLM

**Decision:** The LLM has no DB connection and no tool to generate or execute SQL. It only sees chunks passed by the access-filtered retriever.

**Implication:** Retrieval quality is the ceiling for answer quality. For structured queries (exact joins, aggregations), the answer may be incomplete.

**Rejected:** SQL generation via LLM tool call. Rejected because it creates a fundamentally different threat model — every generated query must be sanitized and access-authorized, which is harder to audit and exposes a prompt injection surface that this system is not designed to defend.

**Future path:** If SQL generation becomes a requirement, it must be treated as a separate, independently secured subsystem — not bolted onto the RAG chain.

---

## P4 — Policy resolved from DB on every request, no caching

**Decision:** JWT carries `user_id` and `role_ids` only. Effective permissions (resolved from `role_policies` + `user_policies`) are re-read from DB on each request.

**Implication:** Policy changes (role revocation, user deactivation, user-level deny) take effect immediately on the next request.

**Rejected:** Baking resolved permissions into the JWT. Rejected because policy changes would be ineffective until token expiry — unacceptable for a fintech system where access revocation must be immediate.

**Future path:** Short-TTL read-through cache (e.g. Redis, 30s TTL) per `user_id` is the correct production optimization. Not needed at prototype scale.

---

## P5 — Fail secure; no degraded mode

**Decision:** On any system failure — policy engine exception, pgvector unavailable, guardrail unable to complete, LLM timeout — the request returns an error. No partial responses, no fallback modes.

**Failure contract:**

| Component fails | Response | chat_messages written? |
|----------------|----------|------------------------|
| Policy engine | 500 | No |
| pgvector | 503 | No |
| Guardrail (can't verify) | 403 | No |
| LLM timeout | 504 | No |

All failures logged to `request_log`.

**Rejected:** Degraded mode (return cached or partial results on failure). Rejected because a fintech audit trail with partial responses is a compliance liability, not a feature.

---

## P6 — Multi-turn chat context excluded from LLM; every turn is stateless

**Decision:** The LLM context contains only: system prompt + current turn's retrieved chunks + user's current message. Prior assistant messages are not included.

**Implication:** The system has no conversational memory. Each question is answered independently. Multi-turn coherence is sacrificed for correctness and implementation simplicity.

**Rejected:** Re-verifying chunk IDs from prior turns before including them in context. Correct in principle — re-runs guardrail against the user's *current* effective policy for every cited chunk in chat history. Rejected for prototype because:
- Adds non-trivial complexity (chunk ID tracking per turn, truncation logic)
- A subtle re-verification bug in a prototype is worse than an honest stateless design
- Timeline: 2 weeks

**Future path (Option A):** Before building the LLM context for turn N, fetch chunk IDs from all prior `chat_messages` rows in the session. Run guardrail against current effective policy. If any chunk is now unauthorized, truncate history at that turn and continue with a reduced context window.

---

## P7 — Three separate databases; ingestion CLI is the only write path to vector_db

**Decision:** Three PostgreSQL instances with distinct roles:

| DB | Owns | Written by |
|----|------|-----------|
| `source_db` | Fintech domain data | External (seeded for prototype) |
| `vector_db` | Chunks + embeddings | Ingestion CLI only |
| `system_db` | Users, roles, policies, logs, chat history | Backend runtime |

`vector_db` is read-only from the runtime's perspective. No API endpoint, no background job, no LLM tool can write to it. The only write path is the explicit ingestion CLI (`ingest.py`).

**Implication:** Access tagging is fully auditable — every chunk in `vector_db` was tagged by the CLI, which reads from a `policies.yaml` under version control. A compromised backend cannot inject or re-tag chunks.

**Rejected:** Single PostgreSQL instance for all three concerns. Rejected because it conflates the security boundary between source data, embeddings, and runtime state, and makes it harder to reason about what the runtime can and cannot touch.

**Prototype:** `source_db` is seeded with role-scoped test data per role (SUPPORT, FINANCE, BIZDEV) via `scripts/seed_source_db.py`. Seed is idempotent.

---

## P8 — System prompt must not expose access control internals

**Decision:** The LLM receives chunks as anonymous context with no metadata. The system prompt explicitly instructs the LLM not to reference or reveal: `allowed_roles`, `allowed_users`, chunk IDs, table names, DB structure, or any hint of the policy model.

**Enforced by:**
- Chunk serialization strips all metadata before building LLM context — LLM sees only the text content
- System prompt includes explicit prohibition: "Do not reference where information comes from, how it is stored, or who else may have access to it"
- Guardrail operates on chunk IDs resolved before LLM call — metadata never enters the LLM context

**Implication:** Users cannot probe the system to infer what data other roles can see. A SUPPORT user asking "what financial data exists?" gets the same "no relevant information found" as any other out-of-scope query.

**Rejected:** Exposing data source citations (e.g. "Source: transactions table, row 42"). Rejected because it reveals schema structure and allows cross-role inference. If attribution is needed in future, it must be abstracted to a human-readable label defined at ingest time, never the raw table/row reference.

---

## Guardrail — Secondary access enforcement layer

Not a standalone principle but a system-wide constraint: after the LLM generates a response, the guardrail re-verifies every chunk ID used in generation against the user's current effective policy.

- **Pass:** response returned, turn persisted to `chat_messages`
- **Block:** 403 returned, violation logged to `request_log` with severity=HIGH, nothing written to `chat_messages`

The guardrail exists because the retrieval filter is the primary control but not the only line of defense. It catches tagging bugs, retriever edge cases, and any future code path that bypasses the WHERE clause.
