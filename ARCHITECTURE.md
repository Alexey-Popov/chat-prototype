# Architecture — Internal Assistant Prototype

## Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | FastAPI (Python) | Async, fast to scaffold, great LangChain support |
| Auth | Authlib (OAuth2) + JWT | Pluggable providers; extendable to SAML/LDAP |
| source_db | PostgreSQL | Fintech source data; read-only for the system; seeded with role-scoped test data |
| vector_db | PostgreSQL + pgvector | Embeddings + chunk metadata; written only by ingestion CLI |
| system_db | PostgreSQL | Users, roles, policies, chat history, request logs |
| Embeddings | OpenAI `text-embedding-3-small` | Cost-effective; easy to swap |
| LLM | OpenAI GPT-4o via LangChain | Abstracted — swappable via `BaseLLM` interface |
| Frontend | React + Vite | Minimal SPA; chat UI + admin panel |
| Infra | Docker Compose | Single `docker compose up` for local dev |

---

## Components

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  ┌──────────────┐   ┌──────────────────────────────┐   │
│  │  Chat UI     │   │  Admin UI                    │   │
│  │  (React SPA) │   │  users / roles / policies    │   │
│  └──────┬───────┘   └──────────────┬───────────────┘   │
└─────────┼──────────────────────────┼───────────────────┘
          │ REST / SSE               │ REST
┌─────────▼──────────────────────────▼───────────────────┐
│  FastAPI Backend                                        │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Auth       │  │ Chat API     │  │ Admin API      │  │
│  │ OAuth2/JWT │  │ /api/chat    │  │ /api/admin/... │  │
│  └────────────┘  └──────┬───────┘  └────────────────┘  │
│                         │                               │
│                  ┌──────▼──────────┐                   │
│                  │ RAG Chain        │                   │
│                  │ (LangChain)      │                   │
│                  │ 1. embed query   │                   │
│                  │ 2. filtered      │                   │
│                  │    vector search │                   │
│                  │ 3. LLM call      │                   │
│                  └──────┬──────────┘                   │
└─────────────────────────┼───────────────────────────────┘
                          │
┌──────────────┐    ┌──────────────────┐    ┌──────────────────────┐
│  source_db   │    │  vector_db       │    │  system_db           │
│  PostgreSQL  │    │  PostgreSQL      │    │  PostgreSQL          │
│              │    │  + pgvector      │    │                      │
│  Fintech     │CLI │                  │    │  users / roles       │
│  data        │───►│  chunks          │    │  role_policies       │
│  (read-only  │    │  embeddings      │    │  user_policies       │
│  for system) │    │  metadata        │    │  chat_sessions       │
│              │    │  (role/user tags)│    │  chat_messages       │
│  Seeded with │    │                  │    │  request_log         │
│  test data   │    │  read by         │    │                      │
│  per role    │    │  retriever only  │    │  written by runtime  │
└──────────────┘    └──────────────────┘    └──────────────────────┘
```

---

## Data Flow — Chat Request

```
1. User logs in via OAuth2  →  JWT issued (contains user_id, role_ids)
2. POST /api/chat {message}  →  JWT validated by middleware
3. Access policy resolved    →  effective {role_tags} ∪ {user_tags}
4. Query embedded            →  OpenAI embedding API
5. pgvector search           →  WHERE metadata @> {tags}  (retrieval-time filter, primary control)
6. Metadata stripped         →  chunk text only passed to LLM; no table names, row IDs,
                                allowed_roles, or policy hints enter the LLM context (P8)
7. Top-k chunks + context    →  LangChain LLM chain → OpenAI (stateless: no prior turn messages)
8. *** GUARDRAIL ***         →  re-verify every chunk ID used in generation
                                against user's effective policy.
                                If any chunk unauthorized → block response, log violation.
9. Response streamed (SSE)   →  back to UI (only if guardrail passes)
10. Persist to chat_messages →  prompt + response + chunk IDs + guardrail result
```

> Retrieval filter = primary enforcement (allowlist WHERE clause).  
> Guardrail = secondary enforcement (post-generation re-verification).  
> Both must pass. A guardrail failure is a security event — logged with HIGH severity.

---

## Ingestion Pipeline

```
CLI: python ingest.py --source-dsn $SOURCE_DSN --vector-dsn $VECTOR_DSN --policy-config policies.yaml

1. Connect to source_db (read-only)
2. Introspect schema (SQLAlchemy)
3. Per table: select rows in batches
4. Serialize row → plain-text chunk  ("table: orders | id: 42 | amount: ...")
5. Tag chunk with allowed_roles / allowed_users from policies.yaml
6. Embed via OpenAI
7. Upsert into vector_db chunks table (chunk_id, embedding, metadata JSONB, schema_hash)

Only the ingestion CLI writes to vector_db. No runtime path touches it.
```

---

## Access Control Model

```
Role policy  :  role_id  →  [table_pattern, ...]        (allowlist, e.g. "finance_*")
User grant   :  user_id  →  additional table_patterns   (expands effective allowlist)
User restrict:  user_id  →  remove table_patterns       (reduces effective allowlist)

Effective allowlist = union(role policies) + user grants − user restrictions
Enforced at: vector query WHERE clause (allowlist only — no deny tags in vector store)
```

**DB tables:**

*source_db* — fintech data, read-only for the system

| Table | Purpose |
|-------|---------|
| *(domain tables)* | transactions, customers, reports, etc. Seeded with role-scoped test data for prototype |

*vector_db* — embeddings, written only by ingestion CLI

| Table | Purpose |
|-------|---------|
| `chunks` | embedding, metadata JSONB `{allowed_roles, allowed_users, table, row_id, schema_hash}` |

*system_db* — runtime state, written by backend

| Table | Purpose |
|-------|---------|
| `users` | Identity, OAuth sub, active flag |
| `roles` | Named roles |
| `user_roles` | M:N assignment |
| `role_policies` | role → table patterns (allowlist only) |
| `user_policies` | user → table patterns, overrides role policy |
| `chat_sessions` | Groups messages per user session |
| `chat_messages` | user prompt, assistant response, retrieved chunk IDs, guardrail result, timestamp |
| `request_log` | Every API request: user_id, endpoint, latency_ms, status_code, violation_chunk_ids |

> **Access policy**: allowlist only. A chunk is retrievable iff it has ≥1 matching tag. No explicit deny.
>
> **Audit requirement**: all chat messages and API requests are persisted. Deletion is not permitted. Retained for compliance audit.
>
> **Fail-secure contract**: on any system failure (policy engine, pgvector, guardrail, LLM) the request returns an error (500/503/504). No partial responses. No degraded mode. Nothing written to `chat_messages` on failure.

---

## Extensibility Hooks

| What to extend | How |
|----------------|-----|
| Add LLM provider | Swap `ChatOpenAI` for any LangChain `BaseChatModel` via env var |
| Add OAuth provider | Add entry to Authlib provider registry (env-driven) |
| Add data source | Implement `DataConnector` abstract class; register in ingestion CLI |
| Swap vector store | Replace `PGVectorRetriever` with any LangChain `VectorStoreRetriever` |
| Scale auth | Authlib supports SAML2, OIDC — no code change needed |
