# LifeLog — Developer Specification (MVP)

Version: 1.0  
Author: Product Owner / Engineering Lead  
Target: Backend + API-first implementation with minimal web UI and CLI (FastAPI, PostgreSQL, MinIO)

---

Table of contents
- Summary & Goals
- Scope & Non-goals
- High-level architecture
- Components & responsibilities
- Data model & DB schema
- Search & indexing
- API specification (endpoints, examples, errors)
- Authentication & authorization
- Attachments & storage design
- Web UI & CLI overview
- Docker Compose & deployment
- Environment variables (.env.example)
- Error handling conventions
- Validation, limits & security controls
- Concurrency, performance & operational notes
- Migrations & schema evolution
- Logging, observability & backups
- Testing plan (unit / integration / e2e)
- CI / CD suggestions
- Acceptance criteria
- Implementation plan / milestones
- Appendix: SQL & snippets, sample docker-compose, sample API request/response

---

Summary & Goals
- Provide a self-hosted, low-maintenance personal life-log (events with metadata and attachments).
- API-first design: FastAPI backend, Jinja2 + HTMX minimal web UI, Python CLI.
- Persist events in PostgreSQL; attachments stored in MinIO (S3-compatible).
- Single docker-compose stack for local deploy.
- Focus on fast reliable capture, search, and export.
- Target single admin user (single API token + admin password).

Scope (MVP)
- API:
  - CRUD endpoints for events
  - Attachments upload/download via MinIO
  - Search endpoint (Postgres full-text + tag/date filters)
  - Export endpoint (JSON with attachment keys)
  - Token-based API auth
- Web UI (Jinja2 + HTMX):
  - Timeline, quick-add, full event form, event detail, settings
- CLI:
  - create-event, attach-file, export
- Storage & infra:
  - Postgres with tsvector & GIN index
  - MinIO with default bucket
  - pgAdmin bound to 127.0.0.1
- Security & limits:
  - Admin password via env for UI
  - API token via env/generated
  - Attachment size limits & MIME whitelist
- No automated backups in MVP (manual export endpoint only).

Non-goals for MVP
- Multi-user/multi-tenant support
- Automated backups / snapshotting (beyond manual export)
- Complex media processing (thumbnails/transcoding)
- Public production-grade hardening (e.g., TLS handled externally)

---

High-level architecture
- FastAPI app exposing REST endpoints + server-rendered UI (Jinja2 + HTMX).
- SQLAlchemy (async) for DB models; Alembic for migrations.
- PostgreSQL for relational storage and full-text search (tsvector + GIN).
- MinIO as S3-compatible object store for attachments.
- Docker-compose to run app, db, minio, pgadmin.
- CLI: Python script using API (token auth).

Components & responsibilities
- app (FastAPI)
  - Routing, business logic, authentication, validation
  - Database access (SQLAlchemy async + asyncpg)
  - MinIO client interactions
  - Runs migrations on startup (Alembic)
- db (Postgres)
  - events, attachments tables
  - tsvector column and GIN index
- minio (MinIO)
  - attachments bucket
- pgadmin (management UI, bound to localhost)
- CLI (Python)
  - Simplified client for quick event ingestion / export / attach

---

Data model & DB schema

Core tables:

1) events
- id: BIGSERIAL PRIMARY KEY
- created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
- timestamp: TIMESTAMPTZ NOT NULL DEFAULT now()  -- user-specified occurrence time
- title: TEXT NOT NULL
- description: TEXT NULL
- tags: TEXT[] NULL
- metadata: JSONB NULL
- search_vector: tsvector GENERATED STORED or updated via trigger
- NOTE: tags may be text[] for convenience, or normalized tags table later.

2) attachments
- id: BIGSERIAL PRIMARY KEY
- event_id: BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE
- key: TEXT NOT NULL UNIQUE  -- S3/MinIO object key (UUID-based)
- filename: TEXT NOT NULL
- content_type: TEXT NOT NULL
- size_bytes: BIGINT NOT NULL
- uploaded_at: TIMESTAMPTZ NOT NULL DEFAULT now()

Indexes
- GIN index on events.search_vector
- B-tree index on events.timestamp
- Index on tags if using array type: CREATE INDEX ON events USING GIN (tags);

Schema SQL (initial migration snippet)
- Example SQL for events with generated tsvector (Postgres 12+):

CREATE TABLE events (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
  title TEXT NOT NULL,
  description TEXT,
  tags TEXT[],
  metadata JSONB,
  search_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('english',
      coalesce(title,'') || ' ' ||
      coalesce(description,'') || ' ' ||
      coalesce(array_to_string(tags, ' '), '')
    )
  ) STORED
);
CREATE INDEX events_search_idx ON events USING GIN (search_vector);
CREATE INDEX events_timestamp_idx ON events (timestamp);

CREATE TABLE attachments (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  key TEXT NOT NULL UNIQUE,
  filename TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX attachments_event_idx ON attachments (event_id);

Notes:
- If you need earlier Postgres versions or prefer explicit trigger, use tsvector_trigger via tsvector_update_trigger.

Search & indexing
- Use Postgres tsvector stored in search_vector (as generated column or via trigger).
- GIN index on search_vector for fast full-text queries.
- Query semantics:
  - q=<text>: full-text search using plainto_tsquery or websearch_to_tsquery
  - tags=tag1,tag2: treat as AND across tags by default; support parameter to choose AND/OR
  - start, end: timestamp filtering (inclusive)
  - sort: newest/oldest; default newest-first
  - pagination via limit+offset (page, page_size) — simple and predictable.

Search example (SQL)
SELECT id, title, description, timestamp, tags
FROM events
WHERE (search_vector @@ websearch_to_tsquery('english', :q) OR :q IS NULL)
  AND (:tags IS NULL OR tags && :tags_array) -- tags overlap
  AND timestamp BETWEEN :start AND :end
ORDER BY timestamp DESC
LIMIT :limit OFFSET :offset;

Ranking (optional)
- Use ts_rank_cd(search_vector, query) for ordering by relevance when q present.

---

API specification (contract-level)

Base path: /api

Authentication:
- Header: Authorization: Bearer <API_TOKEN>
- Web UI uses session cookie established after admin password login.

Response format:
- JSON for structured endpoints.
- Error responses follow consistent schema: { "detail": "...", "error_code": "STRING", "info": { ... } }.
- Dates in ISO 8601 with timezone (RFC3339).

Pagination:
- Query params: page (default 1), page_size (default 25, max 200).
- Response includes: items[], total, page, page_size.

Key endpoints (representative request/response shapes):

1) POST /api/events
- Create event.
- Request (multipart/json):
  {
    "title": "Bought coffee",
    "description": "Latte near office",
    "timestamp": "2025-10-10T08:00:00Z",  // optional default now
    "tags": ["coffee","daily"],
    "metadata": { "price": 3.5, "currency": "USD" }
  }
- Response 201 Created:
  {
    "id": 123,
    "created_at": "2025-10-10T08:01:00Z",
    "timestamp": "2025-10-10T08:00:00Z",
    "title": "Bought coffee",
    "description": "...",
    "tags": ["coffee","daily"],
    "metadata": { ... },
    "attachments": []
  }
- Errors:
  - 400 Bad Request: validation errors
  - 401 Unauthorized: missing/invalid token

2) GET /api/events
- List events with filters.
- Query: ?q=coffee&tags=coffee,daily&start=2025-10-01&end=2025-10-31&page=1&page_size=20&sort=newest
- Response 200:
  {
    "items": [ { <event> }, ... ],
    "total": 512,
    "page": 1,
    "page_size": 20
  }

3) GET /api/events/{id}
- Returns full event with attachment metadata.
- Response attachment list includes signed URLs optionally.

4) PATCH /api/events/{id}
- Partial update payload allowed (JSON Merge):
  { "title": "New title", "tags": ["x"] }
- Response 200 updated event.

5) DELETE /api/events/{id}
- Delete event and cascade-delete attachments in DB and optionally delete objects in MinIO.
- Response 204 No Content

6) POST /api/events/{id}/attachments
- Upload single attachment or multiple (multipart/form-data) with files.
- Server-side validates mime, size and per-event count.
- For each file:
  - Generate key: uuid4 hex + ext
  - Stream upload to MinIO and create attachments DB row atomically (DB transaction).
  - Return attachment metadata: { "id": 1, "filename": "...", "key": "...", "content_type": "...", "size_bytes": ... , "uploaded_at": "..." }
- Responses:
  - 201 Created with list of attachments
  - 400 Bad Request for validation
  - 413 Payload Too Large if > FILE_MAX_BYTES
  - 415 Unsupported Media Type for disallowed MIME

7) GET /api/attachments/{key}
- Download endpoint or redirect to presigned URL.
- Two modes (configurable):
  - Server generates presigned URL from MinIO and returns JSON { "url": "https://..." } OR
  - App proxies stream the object while enforcing auth.
- Recommended: return presigned URL (short-lived), unless proxied mode requested.

8) GET /api/search
- Convenience route mapping to GET /api/events with search params; may be identical.

9) GET /api/export
- Returns an NDJSON or JSON array of all events and attachment keys (no binary).
- Optionally returns presigned URLs for attachments if include_urls=true and admin token used.
- Response 200 application/json

10) POST /api/auth/token/rotate
- Rotate API token (admin only). If accepted, invalidates previous token.
- Request: { "admin_password": "..." } or require admin UI session.
- Response 200: { "api_token": "newtoken" } (show once; store hashed after that).

Auth & session endpoints:
- POST /api/auth/login (web UI only) - Accepts ADMIN_PASSWORD and sets secure session cookie.

Examples:
- Use OpenAPI spec generation from FastAPI; make sure required headers and security schemes are included.

Error codes & types (examples)
- 400 Bad Request - validation errors:
  { "detail": "Field 'title' required", "error_code": "validation_error", "info": { "field": "title" } }
- 401 Unauthorized:
  { "detail": "Invalid token", "error_code": "auth_error" }
- 403 Forbidden:
  { "detail": "Admin only", "error_code": "forbidden" }
- 404 Not Found:
  { "detail": "Event not found", "error_code": "not_found" }
- 413 Payload Too Large:
  { "detail": "File exceeds maximum size 10485760", "error_code": "file_too_large", "info": { "max_bytes": 10485760 } }
- 415 Unsupported Media Type:
  { "detail": "Unsupported content type", "error_code": "unsupported_media_type" }

---

Authentication & authorization

Primary mechanisms
- Web UI:
  - Single admin password provided via ADMIN_PASSWORD env var on first run.
  - Login endpoint verifies password (constant-time), sets server-side session cookie (HttpOnly, Secure when proxying TLS).
  - Session TTL configurable; for MVP can be long (e.g., 7 days).

- API:
  - Bearer token (Authorization: Bearer <API_TOKEN>).
  - Token provided via env var on deploy or generated on first run; stored hashed in DB or file.
  - Rotating token endpoint invalidates previous token.

Token storage & security
- Store server-side token hashed (e.g., using passlib.pbkdf2_sha256) to avoid storing plaintext tokens at rest.
- On generation, show token once in logs and require admin to copy/store; allow re-generation.

Admin-only endpoints
- /api/auth/token/rotate
- Settings UI
- Export endpoints may be admin-only or require token with admin scope (single-user model simplifies this).

Session/cookie security
- Set SameSite=Lax or Strict depending on desired behavior.
- Use secure cookies when deployed behind TLS.
- Session storage can be server memory (fast) or signed cookie — prefer server-side (fastapi-users/Starlette session middleware, or simple secure cookie).

---

Attachments & storage design

Attachment upload flow
1. Client sends multipart/form-data to POST /api/events/{id}/attachments.
2. Server receives UploadFile objects (FastAPI's UploadFile streams to temporary file/IO in memory/disk).
3. Validate:
   - total attachments for event (ATTACHMENT_MAX_PER_EVENT)
   - file content-type vs ALLOWED_MIME_TYPES
   - size limit (FILE_MAX_BYTES)
   - Optionally detect content-type by reading first bytes (magic) for stronger validation.
4. Generate object key: <uuid4 hex>/<timestamp>__<safe-filename>
   - Keep original filename as metadata in DB and object metadata.
5. Upload to MinIO:
   - Use minio-py or boto3; since they are blocking, perform upload in an I/O thread (asyncio.to_thread) or use an async wrapper.
   - Set content-type and metadata (filename).
6. On successful upload, create attachments DB row inside same transaction scope where possible; if object uploaded but DB insert fails, delete the object to avoid orphan objects.
7. Return attachment metadata.

Serving attachments
- Preferred: return presigned URL (signed, short-lived) from MinIO SDK.
  - API: GET /api/attachments/{key}?presign=1 returns { "url": "..." }
- Alternate: app proxies the object and streams to client while enforcing auth. This increases CPU/bandwidth load on app.

Object lifecycle
- Deleting an event should:
  - Delete attachments DB rows (ON DELETE CASCADE).
  - Delete objects from MinIO (best-effort; do in background job if too many).
- Garbage collection: optional cron to find orphaned objects.

Security
- Disallow executable content types (e.g., application/x-msdownload, application/x-sh, application/x-executable).
- Validate filenames; do not use user-provided filename as storage key without normalization.
- Limit per-event and per-file sizes, reject early.

MinIO best practices
- Require MinIO bucket at startup; app should create bucket if missing.
- Use server-side encryption on MinIO if available (optional).
- Configure MinIO credentials via env variables and avoid embedding in logs.

Uploading large files
- Use streaming UploadFile handling; avoid fully reading file into memory.
- For large file support in FastAPI, read upload chunks and stream to MinIO SDK put_object which can accept file-like objects or direct streaming.

---

Web UI & CLI overview

Web UI (Jinja2 + HTMX)
- Timeline view (index): paginated events newest-first; show timestamp, title, snippet, tags, attachment icons.
- Quick-add bar: single-line title input + tags + Add button (creates minimal event).
- Full event form: timestamp, title, description, tags (tokenized input), attachments input, metadata JSON (advanced).
- Event detail: show event, list attachments (preview images), edit/delete buttons.
- Settings page: rotate API token (requires admin password), change admin password (update APR hashed), view file-size limit.
- Use HTMX for small inline interactions (add event, edit forms, attachments preview).

CLI (Python)
- Commands:
  - create-event --title "..." [--description "..."] [--tags "a,b"] [--timestamp "..."]
  - attach-file --event-id 123 --file ./photo.jpg
  - export --out events.json
- Authentication via env LIFLOG_API_TOKEN or config file.
- CLI uses requests or httpx to talk with API.

UX notes
- Keep UI minimal; favor API for automation and CLI use.
- Provide feedback on upload progress and validation errors.

---

Docker Compose & deployment

Services:
- app (FastAPI)
  - Build from repo Dockerfile
  - Ports: 8000:8000
  - Depends on: db, minio
  - Env: DATABASE_URL, MINIO_ENDPOINT, MINIO_* credentials, ADMIN_PASSWORD, etc.
  - Entrypoint: run migrations (alembic upgrade head) then start uvicorn
  - Mount volumes for logs if desired

- db (postgres:15)
  - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
  - Volume: pgdata

- minio (minio/minio)
  - Command: server /data --console-address ":9001"
  - Ports: 9000:9000, 9001:9001
  - Env: MINIO_ROOT_USER, MINIO_ROOT_PASSWORD
  - Volume: minio-data

- pgadmin (dpage/pgadmin4)
  - Expose on 127.0.0.1:8080 only (host bound)
  - Env: PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD
  - Volume: pgadmin-data

Volumes:
- pgdata, minio-data, pgadmin-data

App responsibilities at startup:
- Wait for Postgres and MinIO readiness.
- Run Alembic migrations automatically.
- Ensure MinIO bucket exists; create if missing.
- Generate API token if not provided (log a warning to stdout with token; store hashed in DB).
- Initialize admin password state (optionally persist hashed admin password in DB).

Sample docker-compose snippet is in appendix.

---

Environment variables (.env.example)
- ADMIN_PASSWORD=CHANGE_ME
- API_TOKEN=  # optional; auto-generated if blank
- DATABASE_URL=postgresql+asyncpg://lifelog:lifelogpass@db:5432/lifelog
- POSTGRES_USER=lifelog
- POSTGRES_PASSWORD=lifelogpass
- POSTGRES_DB=lifelog
- MINIO_ROOT_USER=minioadmin
- MINIO_ROOT_PASSWORD=minioadmin
- MINIO_ENDPOINT=minio:9000
- MINIO_BUCKET=lifelog-attachments
- FILE_MAX_BYTES=10485760
- ATTACHMENT_MAX_PER_EVENT=10
- ALLOWED_MIME_TYPES=image/jpeg,image/png,image/webp,application/pdf,text/plain,text/markdown,text/csv,video/mp4
- PGADMIN_EMAIL=admin@example.com
- PGADMIN_PASSWORD=pgadminpass
- LOG_LEVEL=INFO

---

Error handling conventions

Principles
- Use consistent JSON error responses.
- Validate inputs early; return 400 with field-level details when possible.
- For server/internal errors, return 500 with generic message and unique error id logged for debugging; do not expose stack traces.

Error response structure
{
  "detail": "Human readable message",
  "error_code": "snake_case_code",
  "info": { /* optional extra data for clients */ }
}

Implementation notes
- Use FastAPI exception handlers to transform exceptions into standard responses.
- Catch DB integrity errors and translate to 409 Conflict where appropriate.
- For file upload exceptions, raise HTTPExceptions with status codes 413, 415, or 400.

Transaction and consistency
- Use DB transactions for operations that involve both DB and storage. Where atomicity is not possible (object store + DB), implement compensating actions:
  - If object uploaded but DB insert fails, delete object.
  - If DB insert succeeds but object upload fails, rollback DB insertion.

---

Validation, limits & security controls

Validation
- Title required and length-limited (e.g., max 1024 chars).
- Description length cap (e.g., 10k chars).
- Tags limited per event (e.g., 50 tags, tag length max 64).
- metadata JSON size limited (e.g., 16k bytes).

Attachment limits
- FILE_MAX_BYTES default 10 MB (env-configurable)
- ATTACHMENT_MAX_PER_EVENT default 10
- Allowed MIME types configured via ALLOWED_MIME_TYPES env var; default whitelist provided.

Security
- Store admin password & API token hashed.
- pgAdmin bound to localhost.
- Avoid exposing MinIO console outside trusted network.
- If publicly exposing app, place a reverse proxy (Caddy/Traefik) with TLS and optional extra auth.

Rate limiting (optional)
- Not required for MVP, but advise adding an API rate limiter in future if publicly exposed.

---

Concurrency, performance & operational notes

Concurrency model
- Use async FastAPI + async SQLAlchemy + asyncpg for DB concurrency.
- MinIO SDK likely blocking (minio-py); run pushes in thread pool (asyncio.to_thread / run_in_executor) or use aioboto3/aiobotocore wrapper.

Resource controls
- Limit max concurrent uploads to prevent memory pressure (e.g., semaphore).
- Configure uvicorn workers appropriately (gunicorn uvicorn workers for production). For single-host MVP, 1-4 workers depending on CPU/memory.

Streaming & memory usage
- Use streaming UploadFile to avoid loading entire file into memory.
- Use chunked uploads to MinIO.

Scaling notes
- MVP is single instance; future scaling requires separating services (object store, DB replica, web server behind reverse proxy).

Operational tasks
- Ensure healthchecks for db and minio in docker-compose.
- Provide script to run Alembic migrations locally and in CI.

---

Migrations & schema evolution

- Use Alembic with autogenerate disabled/enabled per team preference.
- Keep one initial migration creating events and attachments tables and indexes.
- For search_vector as generated column, ensure SQL in migration supports PG version; fallback to trigger-based approach if needed.
- Example Alembic revision head creation:
  - create tables
  - create search vector generated column or trigger function + trigger
  - create GIN index

Downgrades
- For MVP, downgrades optional; reversible Alembic scripts recommended.

---

Logging, observability & backups

Logging
- Structured JSON logs (recommended) with LOG_LEVEL environment.
- Sensitive info must not be logged (tokens, passwords).
- On token generation, log only once and indicate secured storage required.

Metrics & health
- /health endpoint that checks DB connectivity and MinIO access.
- Expose /metrics (prometheus) if desired (optional).

Backups
- MVP: manual export endpoint and CLI export.
- Post-MVP: scheduled pg_dump + upload to MinIO or remote backup.

Disaster recovery
- Provide scripts to:
  - dump DB with pg_dump
  - export attachments from MinIO
  - restore procedure documented in README

---

Testing plan

Testing goals
- Ensure correctness of API behavior, DB interactions, file upload/serve, auth flows.
- Provide reliable integration testing with real Postgres and MinIO containers.

Test types
1) Unit tests
- Test business logic, validation, utilities (tag parsing, key generation).
- Use pytest and monkeypatch dependencies (MinIO client wrappers) for fast runs.

2) Integration tests
- Use testcontainers-python or docker-compose for ephemeral Postgres and MinIO.
- Run real migrations, create bucket, run full HTTP tests using httpx AsyncClient or requests.
- Tests:
  - Event lifecycle (create, read, update, delete)
  - Attachment flows (upload small binary, invalid mime, oversized file)
  - Search queries with relevance & tag filtering
  - Export endpoint includes correct events and keys

3) End-to-end tests
- Spin up full stack via docker-compose in CI (or Testcontainers) and run a few end-to-end flows:
  - CLI create-event -> verify via API GET
  - Web login flow (optional)

4) Security tests
- Ensure file-type blocking works
- Ensure token-only endpoints reject wrong tokens
- Ensure pgAdmin accessible only via localhost (test in integration)

Test harness & utilities
- Provide test fixtures for:
  - ephemeral DB URL (from testcontainers)
  - MinIO client creds and bucket pre-creation
  - cleanup routines for buckets and DB between tests

CI-friendly
- CI pipeline should start containers via testcontainers so tests are isolated and deterministic.
- Tests should be parallelizable but avoid shared state; use unique resource names in tests.

Sample testcases (priority)
- Create event via API; confirm created_at, timestamp and search_vector generate correctly.
- Upload a valid image file; verify row in attachments and object in MinIO.
- Reject oversized file (413).
- Search by text and tag; confirm results ordering and counts.
- Rotate API token; previous token fails after rotation.

---

CI / CD suggestions

CI pipeline
- Steps:
  1. Checkout code
  2. Install dependencies (use pinned pip requirements)
  3. Lint (ruff/flake8), format check (black)
  4. Run unit tests
  5. Start testcontainers (Postgres + MinIO) and run integration tests
  6. Build Docker image (optionally)
- Use GitHub Actions or GitLab CI. Use matrix if testing multiple Python versions.

CD
- For local deployments, docker-compose up is sufficient.
- For more advanced deployments, provide Dockerfile and publish image on build.

---

Acceptance criteria (MVP)
- Deployable with docker-compose up.
- Admin can log into web UI using ADMIN_PASSWORD env var.
- API token present (either generated or provided) and can be used for CLI.
- Create events via quick-add and full form.
- Upload attachments (subject to MIME/size limits) stored in MinIO.
- Search works: full-text + tag + date range.
- Export endpoint returns JSON for all events with attachment keys.
- pgAdmin available at http://127.0.0.1:8080 and can connect to Postgres container.
- File size and MIME limits are enforced and configurable.

---

Implementation plan & milestones (recommended 6-week plan)

Week 0 — scaffolding
- Repo setup, Dockerfile, docker-compose, base FastAPI application
- CI skeleton and linter config
- DB connection and Alembic configured

Week 1 — models & DB
- Implement events/attachments models (SQLAlchemy async)
- Create initial Alembic migration with search_vector and indexes
- Integrate migrations into app startup

Week 2 — API basics
- Implement CRUD endpoints for events
- Add pagination and GET list endpoints
- Unit tests for event endpoints

Week 3 — attachments & storage
- Integrate MinIO client, create bucket at startup
- Implement attachments upload/download endpoints
- Validate MIME & size; ensure streaming uploads
- Test upload flows thoroughly

Week 4 — search & web UI
- Implement search endpoint with tsvector queries and tag/date filters
- Build initial timeline view + quick-add (HTMX)
- Add full event form and event detail pages

Week 5 — CLI & utility endpoints
- Implement CLI commands using API
- Implement export endpoint and token rotation
- Add settings page for admin tasks

Week 6 — polish & testing
- Add tests (integration using testcontainers)
- Finalize docker-compose and docs
- Prepare README and runbook

---

Appendix

A. Sample Alembic migration (simplified)
- See Data model SQL snippet in Data model section. Implement via Alembic with SQL execution if autogenerate not perfect.

B. Example object key generation (python)
def make_object_key(filename: str) -> str:
    import uuid, time, os
    uid = uuid.uuid4().hex
    ts = int(time.time())
    ext = os.path.splitext(filename)[1] or ""
    safe = secure_filename(filename)[:128]  # implement sanitize
    return f"{uid}/{ts}__{safe}"

C. MinIO interactions (notes)
- Use minio-py for simplicity and reliability (synchronous):
  - from minio import Minio
  - client.put_object(bucket, object_name, data_stream, length, content_type=...)
- For async app, wrap blocking calls:
  - await asyncio.to_thread(minio_client.put_object, ...)
- Create bucket on startup:
  if not client.bucket_exists(bucket):
      client.make_bucket(bucket)

D. Sample docker-compose (abbreviated)
version: "3.8"
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: ["db","minio"]
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data
  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: ${PGADMIN_EMAIL}
      PGADMIN_DEFAULT_PASSWORD: ${PGADMIN_PASSWORD}
    ports:
      - "127.0.0.1:8080:80"
volumes:
  pgdata:
  minio-data:

E. Example API request (curl)
# Create event
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"title":"Morning run","description":"5km run", "tags":["health","run"]}'

F. Example error response
HTTP/1.1 400 Bad Request
Content-Type: application/json
{
  "detail": "Field 'title' is required",
  "error_code": "validation_error",
  "info": {"field": "title"}
}

G. Testing recommendations (technical)
- Use pytest-asyncio to test async endpoints.
- Use testcontainers-python (PostgresContainer, GenericContainer for MinIO) to run integrations reliably in CI.
- Fixtures:
  - give each test a randomly named MinIO bucket or use a test prefix to avoid interference.
  - create and teardown buckets in fixture scope.

H. Security checklist (MVP)
- Set ADMIN_PASSWORD in .env on deploy; do not commit secrets.
- Ensure pgAdmin port is host-bound.
- Enforce ALLOWED_MIME_TYPES and FILE_MAX_BYTES server-side.
- Use presigned URLs for object downloads to avoid exposing MinIO.
- Store tokens hashed; rotate tokens via admin route.

---

If you want next artifacts, I can produce:
- OpenAPI (YAML/JSON) for all endpoints (full request/response schemas).
- Initial Alembic migration SQL file.
- Full docker-compose.yml and .env.example file.
- Starter repo layout with skeleton FastAPI app, models, and a single-file prototype.
Which would you like first?