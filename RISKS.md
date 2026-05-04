# Risk Register

## Legend
- **Likelihood**: H = High / M = Medium / L = Low  
- **Impact**: Critical / High / Medium / Low

---

## Security

| ID | Risk | L | Impact | Mitigation |
|----|------|---|--------|------------|
| S1 | Access policy bypass — user retrieves chunks from a restricted role via crafted query | H | Critical | Enforce tag filter **at vector query WHERE clause**, never post-filter. Integration test: each role × restricted query. |
| S2 | JWT stolen from browser (XSS) | M | Critical | Store JWT in memory only (not localStorage/cookie). Short expiry (15 min) + refresh token rotation. |
| S3 | PII / sensitive financial data in embeddings | H | High | Ingest only approved tables/columns. Column exclusion list in `policies.yaml`. Embeddings stored in vector_db — a separate, dedicated PostgreSQL instance (P7). |
| S4 | OAuth callback open redirect | L | High | Validate `state` param; whitelist redirect URIs in OAuth provider config. |
| S5 | Admin API exposed without auth | M | Critical | All `/api/admin/*` routes require `admin` role in JWT. Separate middleware guard. |

---

## Data & Accuracy

| ID | Risk | L | Impact | Mitigation |
|----|------|---|--------|------------|
| D1 | LLM hallucination on structured DB data | M | High | Evaluate retrieval quality with 10 golden Q&A pairs before demo. Add domain glossary to system prompt. No source citations exposed to user (P8). SQL-generation fallback is out of scope (P3). |
| D2 | Source DB schema changes break ingestion | M | Medium | Store `schema_hash` per table. Re-index automatically on hash change. Alert on schema drift. |
| D3 | Stale embeddings after data updates | H | Medium | Incremental re-ingestion by `updated_at` column. Full re-index as fallback via CLI flag. |
| D4 | Poor retrieval quality for domain-specific fintech terms | M | Medium | Add domain glossary to system prompt. Evaluate retrieval quality with 10 golden Q&A pairs before demo. |

---

## Timeline & Scope

| ID | Risk | L | Impact | Mitigation |
|----|------|---|--------|------------|
| T1 | Admin UI doesn't fit in 2 weeks | M | Low | Ship API-only admin first; UI is last priority. Policy YAML file is a viable fallback for demo. |
| T2 | OAuth setup blocked by corp network / provider approval | M | High | Build dev mode: env var `DEV_MOCK_USER` bypasses OAuth, injects a test JWT. Never enabled in prod. |
| T3 | pgvector performance too slow for demo dataset | L | Low | IVFFlat index on embedding column. For prototype, < 100k chunks is fine with exact search. |
| T4 | OpenAI API rate limits during ingestion | M | Low | Batch embedding requests. Exponential backoff in ingestion CLI. |

---

## Extensibility

| ID | Risk | L | Impact | Mitigation |
|----|------|---|--------|------------|
| E1 | LangChain version lock makes LLM swaps hard | M | Medium | Pin LangChain version. Wrap in `LLMProvider` ABC — swap is one class, not a refactor. |
| E2 | pgvector metadata filter syntax limits future query complexity | L | Medium | JSONB indexing covers prototype needs. Vector DB swap path is documented in ARCHITECTURE.md. |
| E3 | Policy YAML grows unwieldy with many users/roles | L | Low | YAML is prototype-only. Production path: policy management via Admin UI backed by DB tables (already modelled). |
