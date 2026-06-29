# Architecture

## Ingest path

```
CSV upload (POST /api/ingest/)
  │
  ├─ IngestView
  │    ├─ Reads tenant from JWT (never from request body)
  │    └─ Saves to temp file → calls ingest_csv()
  │
  └─ ingest_csv(file_path, tenant_name, source_name)
       ├─ Validates header: {name, category, question, answer}
       ├─ Collects valid rows; skips malformed with a warning
       ├─ Deletes existing DocumentChunk rows for (tenant, source)  ← idempotency
       ├─ embed_documents_batch(texts)                              ← local e5, one call
       │    └─ SentenceTransformer("intfloat/multilingual-e5-base")
       │         prefix: "passage: "
       └─ DocumentChunk.objects.bulk_create(objects)               ← one DB round-trip
```

**Tenant isolation enforced at:** ingest — every `DocumentChunk` carries a `tenant` FK.

---

## Query path

```
POST /api/query/  {query, template}
  │
  ├─ QueryView
  │    ├─ Reads tenant_id from JWT                    ← isolation boundary #1
  │    ├─ Checks requests_used < api_quota            ← quota gate
  │    └─ Increments requests_used atomically (F())
  │
  └─ rag_query(query, tenant_id, template)
       │
       ├─ retrieve_chunks(query, tenant_id)
       │    ├─ embed_query(query)                     ← local e5, prefix "query: "
       │    └─ DocumentChunk.objects
       │         .filter(tenant_id=tenant_id)         ← isolation boundary #2
       │         .annotate(CosineDistance(embedding, query_vec))
       │         .filter(distance < 0.65)
       │         .order_by("distance")[:5]
       │
       ├─ build_prompt(template, context, query)      ← prompts.py
       │
       └─ client.models.generate_content(gemini-2.5-flash)
            └─ retry on RESOURCE_EXHAUSTED (×2, backoff 1s / 3s)
```

**Tenant isolation enforced at:** retrieval — `.filter(tenant_id=tenant_id)` is the
single boundary. Every code path that calls `retrieve_chunks` must supply the tenant_id
from `request.user.userprofile.tenant_id`.

---

## Data model

```
Tenant
  id, name, domain (nullable unique), api_quota, requests_used, created_at
    │
    ├── DocumentChunk (FK tenant)
    │     id, source, category, content, embedding (vector 768), metadata, created_at
    │
    └── UserProfile (OneToOne User)
          id, user_id, tenant_id
```

---

## Component map

```
core/
  settings.py   — Django config, CORS, REST_FRAMEWORK, template dirs
  urls.py       — mounts /api/, /admin/, /api/docs/, / (SPA)

documents/
  models.py                         — Tenant, DocumentChunk, UserProfile
  auth.py                           — TenantTokenView (bakes tenant into JWT)
  views.py                          — QueryView, IngestView, HealthView,
                                      UsageView, RegisterView
  urls.py                           — API URL table
  services/
    embeddings.py                   — embed_document, embed_query,
                                      embed_documents_batch (e5, local)
    retrieval.py                    — retrieve_chunks (tenant-filtered cosine search)
    ingestion.py                    — ingest_csv (validate, idempotent, batch)
    rag.py                          — rag_query (retrieve → prompt → generate)
    prompts.py                      — 6 named templates + build_prompt()
  management/commands/
    ingest_csv.py                   — CLI ingestion
    reset_quotas.py                 — monthly quota reset

templates/
  index.html                        — SPA shell (served at /)

static/
  style.css                         — minimal design system
  app.js                            — all SPA logic (auth, query, upload, usage)
```
