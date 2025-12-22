# LifeLog — Prompt Plan (Code-generation + Manual Blueprint)

This Prompt Plan translates the LifeLog devSpec into a step-by-step, test-driven, incremental implementation plan. It is structured so each component can be implemented, verified, and integrated before moving to the next. For each incremental chunk there is a code-generation LLM prompt (inside a code block) that asks the LLM to implement that chunk with tests, plus manual verification steps and a TODO checklist that can be checked off as the work completes.

Guiding principles applied
- Small, verifiable increments: each prompt is scoped to produce code + tests that verify behavior.
- Test-driven approach: every prompt asks for unit and/or integration tests and instructions to run them.
- No orphaned code: each new artifact must be integrated into the running app and CI; wiring steps included.
- Compensating actions: where DB + object store interactions are involved, tests must assert cleanup behavior.
- Clear manual verification steps when needed (UI checks, Docker Compose runs).
- All prompts build sequentially and reference prior steps; each prompt assumes completion of earlier prompts.

Repository layout (target)
- repo root
  - app/
    - main.py
    - api/
    - core/
    - db/
    - models/
    - schemas/
    - services/
    - templates/
    - static/
    - cli/
  - alembic/
  - tests/
  - docker-compose.yml
  - Dockerfile
  - pyproject.toml / requirements.txt
  - .env.example
  - README.md
  - .github/workflows/ci.yml
  - pre-commit config

How to use this document
1. Work prompts in order. Each prompt includes a code block that is the instruction for the code-generation LLM.
2. Execute generated code and run tests locally as directed by the prompt.
3. Check off TODOs after verification.
4. Proceed to next prompt only after the current prompt's checklist is fully completed.

-----------------------------
SECTION A — High-level staged milestones
-----------------------------
Stages (milestones):
1. Scaffolding & healthcheck (repo, Dockerfile, docker-compose, lint/test skeleton, /health endpoint).
2. Database connectivity & migrations (async SQLAlchemy, Alembic, run migrations on startup).
3. Models & migrations (events + attachments + indices + search vector).
4. CRUD API endpoints for events (with Pydantic schemas and validation, unit/integration tests).
5. Attachments: MinIO integration, upload endpoint, validated streaming uploads, DB rows.
6. Attachment serving: presigned URLs and optional proxy; deletion/cascade handling.
7. Search endpoint with full-text + tag/date filters and rank.
8. Auth (admin password web session + bearer token with rotation).
9. Export endpoint + CLI (create-event, attach-file, export).
10. Web UI (Jinja2 + HTMX minimal flow: timeline, quick-add, event detail, settings).
11. CI, final docker-compose, docs, and acceptance testing.

For each stage below you will find:
- A small set of concrete sub-steps.
- A code-generation prompt (to feed to a code-generation LLM).
- A checklist (markdown checkboxes) for verifying the work.

-----------------------------
SECTION B — Iteratively refined prompt chunks
-----------------------------
Note: Each prompt must be executed in order. Every code-generation prompt asks the LLM to produce code and tests. After the code is generated, run tests (automated) and perform manual verifications indicated.

PROMPT 0 — Scaffolding & Healthcheck (repo skeleton, Docker, lint/test config)
- Goal: Create a reproducible repo skeleton with a minimal FastAPI app, health endpoint, Dockerfile, docker-compose skeleton (db+minio stubs), basic lint/test config, and CI skeleton. Add a unit test for /health.
- Why first: Provides foundation for integration tests, CI, and incremental work.

Code-generation prompt:
```text
You are creating the initial scaffolding for the LifeLog project.

Tasks:
1. Create a Python project layout (use either pyproject.toml with poetry / pip + requirements.txt — choose requirements.txt for portability).
2. Implement a minimal FastAPI app at app/main.py exposing:
   - GET /health -> returns JSON { "status": "ok", "db": "unknown", "minio": "unknown" }
   - Configure uvicorn startup entry in app/main.py.
3. Add a Dockerfile for the app that installs requirements and runs uvicorn.
4. Add a docker-compose.yml with placeholders/services for:
   - app (build .), db (postgres image), minio (minio/minio), pgadmin (bound to 127.0.0.1:8080)
   - Ensure docker-compose keeps simple defaults but does not require secrets (pull values from .env).
5. Add .env.example with variables used in dev (DATABASE_URL, MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, ADMIN_PASSWORD, API_TOKEN).
6. Add basic dev tooling config:
   - requirements.txt with FastAPI, uvicorn, pytest, pytest-asyncio, httpx, sqlalchemy (latest async-compatible), alembic, python-dotenv, ruff, black.
   - pre-commit config specifying black and ruff hooks (optional).
7. Add a pytest test tests/test_health.py that:
   - Imports app.main.app and uses httpx (AsyncClient) or TestClient to assert GET /health returns 200 and correct JSON.
8. Add GitHub Actions CI skeleton .github/workflows/ci.yml that:
   - Runs lint (ruff), runs tests using python (no heavy integration yet).
9. Document in README.md how to run tests and start app in dev (python -m uvicorn app.main:app --reload).

Requirements for generated code:
- All code must be self-contained and runnable locally with only docker-compose (optional) and Python.
- Tests should pass in CI run (they should not depend on DB/MinIO at this step).
- Provide instructions in README for running the test and starting the app.

Deliverables:
- Files written/updated: requirements.txt, Dockerfile, docker-compose.yml, .env.example, app/main.py, tests/test_health.py, README.md, .github/workflows/ci.yml

After you generate code, run:
- pip install -r requirements.txt
- pytest -q

Return:
- A short summary of created files and how to run tests and start the app.
```

Verification & manual steps:
- Run pip install -r requirements.txt and pytest; ensure tests pass.
- Start app: python -m uvicorn app.main:app --reload; verify http://localhost:8000/health returns expected JSON.
- Optionally: docker-compose up to ensure app container builds (db/minio may show errors - that's ok for now).

Checklist:
- [ ] Create project layout and files per prompt
- [ ] Implement /health endpoint and app entrypoint
- [ ] Add Dockerfile, docker-compose.yml, .env.example
- [ ] Add requirements.txt and pre-commit (optional)
- [ ] Add tests/test_health.py and confirm pytest passes
- [ ] Add README.md instructions
- [ ] Create CI skeleton file

---

PROMPT 1 — DB connection & Alembic wiring
- Goal: Add async SQLAlchemy DB engine initialization, session dependency, Alembic config, and a DB readiness check endpoint. Add integration test scaffolding using testcontainers to validate migrations runnable in CI.
- Rationale: Required before models and migrations; ensures app can connect to Postgres and run Alembic on startup.

Code-generation prompt:
```text
Implement database connectivity and Alembic wiring for LifeLog.

Tasks:
1. Add an async DB module at app/db/ with:
   - create_async_engine using DATABASE_URL env var (asyncpg dialect).
   - AsyncSession factory and get_async_session dependency for FastAPI.
   - A startup function to attempt DB connection and optionally run a lightweight "SELECT 1" check.
2. Add Alembic scaffolding (alembic.ini, alembic/ env.py) configured to use the app/db async URL for migrations.
   - Provide an alembic revision command example in README.
3. Implement app startup code in app/main.py:
   - On startup wait for DB connectivity (retry loop with backoff).
   - Expose DB check in GET /health (db: "ok" if reachable).
4. Create tests/tests_db.py that:
   - Uses testcontainers-python (PostgresContainer) to spin up a temporary Postgres.
   - Runs alembic upgrade head against that Postgres URL (execute via subprocess calling alembic or via alembic API).
   - Asserts that connection succeeds and that "SELECT 1" returns 1.
   - These tests should be marked integration (pytest marker) so CI can skip if testcontainers is absent.
5. Document how to run alembic migrations and how app will wait for DB on startup.

Requirements:
- Use async SQLAlchemy 1.4+ async API.
- Keep DB connection code reusable by models and services.
- Tests should be robust (wait for container readiness).

Deliverables:
- app/db/__init__.py (engine, session, get_session)
- alembic/ scaffold + config entries to point to DATABASE_URL
- updated app/main.py with startup hook and modified /health output
- tests/tests_db.py integration test

After generating code, run:
- pip install -r requirements.txt
- pytest -q (unit tests should pass)
- Optional: run the integration test with testcontainers locally to verify migrations run.
```

Verification & manual steps:
- Run pytest (unit tests must still pass).
- Run integration test locally (requires docker).
- Start app and confirm GET /health shows db: "ok" when connected.

Checklist:
- [ ] Add async DB engine and session dependency
- [ ] Add Alembic scaffolding configured for async DB
- [ ] Startup DB readiness and /health updated
- [ ] Integration test using PostgresContainer added
- [ ] README updated with migration/run instructions

---

PROMPT 2 — Models & initial Alembic migration
- Goal: Implement SQLAlchemy models for events and attachments per devSpec and produce an Alembic migration that creates tables, tsvector (generated column or trigger), and indexes.
- Rationale: Foundation for storage and search.

Code-generation prompt:
```text
Implement SQLAlchemy models and create the initial Alembic migration.

Tasks:
1. Implement models using SQLAlchemy ORM (async-compatible) in app/models/:
   - Event model with columns:
     id BIGSERIAL PK
     created_at TIMESTAMPTZ default now()
     timestamp TIMESTAMPTZ default now()
     title TEXT NOT NULL
     description TEXT
     tags TEXT[] (postgres array)
     metadata JSONB
     search_vector tsvector (generated or via trigger) — ensure migration handles postgresql specifics
   - Attachment model with columns:
     id BIGSERIAL PK
     event_id FK to events(id) ON DELETE CASCADE
     key TEXT UNIQUE
     filename TEXT
     content_type TEXT
     size_bytes BIGINT
     uploaded_at TIMESTAMPTZ default now()
2. Create an Alembic revision (initial migration) that:
   - Creates the two tables
   - Adds GIN index on search_vector
   - Creates B-tree index on events.timestamp
   - Creates GIN index on tags (events) if using text[]
   - If generated column for tsvector is unsupported, implement trigger-based tsvector_update_trigger in migration
3. Modify app startup to run alembic upgrade head automatically (opt-in via env var RUN_MIGRATIONS=true) and create the MinIO bucket placeholder (we'll do actual creation in an attachments prompt).
4. Add unit/integration tests tests/test_models.py:
   - Use testcontainers Postgres to run migration, then connect and:
     - Insert an event via ORM and assert the row exists.
     - Insert an attachment row and verify foreign key constraint and cascade (delete event => attachment row deleted).
   - Verify that the search_vector column exists (query information_schema / pg_catalog).
5. Document any Postgres version specifics (tsvector generated column works Postgres >=12).

Requirements:
- Use Postgres-specific types via sqlalchemy.dialects.postgresql (ARRAY, JSONB, TSVECTOR); for ORM mapping use proper types.
- Alembic migration must be runnable via alembic upgrade head.

Deliverables:
- app/models/event.py, app/models/attachment.py
- Alembic revision file(s)
- Updated startup code to optionally run migrations
- tests/test_models.py

After generating code, run:
- pip install -r requirements.txt
- pytest tests/test_models.py (integration tests may require docker)
```

Verification & manual steps:
- Run migrations against a test Postgres; ensure tables and indexes created.
- Run tests to validate ORM behavior and cascade delete.

Checklist:
- [ ] Implement Event and Attachment models
- [ ] Create Alembic initial migration with tsvector/indexes
- [ ] Startup auto-migration via env toggle
- [ ] Integration tests for ORM and cascade behavior
- [ ] Documentation on Postgres specifics

---

PROMPT 3 — Event repository & CRUD API endpoints (test-driven)
- Goal: Implement repositories and CRUD REST API endpoints for events with Pydantic schemas, request validation, pagination, and unit/integration tests.
- Rationale: Core API for events must exist before attachments, search, UI.

Code-generation prompt:
```text
Implement repositories and CRUD endpoints for events.

Tasks:
1. Create Pydantic schemas in app/schemas/ for:
   - EventCreate, EventUpdate, EventOut, EventListOut (pagination wrapper).
   - Validate title (required, max length 1024), description max limit, tags as list[str], metadata as dict.
2. Implement a repository/service layer in app/services/event_service.py that:
   - Uses async SQLAlchemy sessions
   - Provides create_event, get_event, list_events (with pagination offset+limit), update_event, delete_event
   - list_events supports optional parameters: q (text), tags (list), start, end (timestamps), sort
     - For now q is ignored or simple implementation (later replaced by full-text search).
3. Implement FastAPI router in app/api/events.py with endpoints:
   - POST /api/events -> create event (201)
   - GET /api/events -> list events (with page/page_size or limit/offset)
   - GET /api/events/{id} -> event detail (200)
   - PATCH /api/events/{id} -> partial update (200)
   - DELETE /api/events/{id} -> 204
   - Ensure Authorization header is optional at this stage (we will add auth later).
4. Add tests/tests_events.py:
   - Unit tests for repository functions using test Postgres (testcontainers).
   - Integration tests using httpx AsyncClient against FastAPI app to verify endpoints behavior end-to-end (create -> list -> get -> update -> delete).
   - Tests assert JSON shape and status codes per devSpec.
5. Add validation and consistent error responses:
   - Use FastAPI HTTPException with structured error JSON pattern {"detail": "...", "error_code": "..."}.
6. Wiring:
   - Register router into app/main.py under prefix /api/events.
   - Ensure tests import the same app instance.

Requirements:
- All endpoints must be covered by tests.
- Keep business logic in service layer (not inside route handlers).
- Pagination default page_size 25, max 200.

Deliverables:
- app/schemas/*.py
- app/services/event_service.py
- app/api/events.py
- tests/tests_events.py

After generating code, run:
- pytest -q
- Run integration test to exercise endpoints
```

Verification & manual steps:
- Run unit and integration tests. Confirm CRUD lifecycle works.
- Manually hit endpoints with curl as ad-hoc verification.

Checklist:
- [ ] Implement Pydantic schemas
- [ ] Implement event service/repository layer
- [ ] Create FastAPI router for events
- [ ] Integration tests for CRUD endpoints
- [ ] Standardized error responses implemented

---

PROMPT 4 — Attachments backend (MinIO integration & upload endpoint)
- Goal: Integrate MinIO, implement attachment upload endpoint (multipart/form-data), streaming upload to MinIO, validation (MIME, size, per-event limit), atomic DB/object behavior, and tests using MinIO container.
- Rationale: Attachments are essential to LifeLog; must be robust and tested.

Code-generation prompt:
```text
Implement attachments support with MinIO integration and upload endpoints.

Tasks:
1. Add MinIO client wrapper in app/services/storage.py:
   - Use minio (minio-py). Because minio-py is blocking, wrap calls with asyncio.to_thread where appropriate.
   - Add functions: ensure_bucket(bucket_name), upload_object(bucket, object_name, fileobj, length, content_type, metadata), presign_get(bucket, object_name, expires_seconds), delete_object(bucket, object_name).
   - Configure via env vars: MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_BUCKET.
2. Implement endpoint POST /api/events/{id}/attachments:
   - Accept multipart/form-data with files (multiple).
   - Validate:
     - File size <= FILE_MAX_BYTES env var (default 10MB).
     - Content-Type in ALLOWED_MIME_TYPES env var.
     - Per-event attachments <= ATTACHMENT_MAX_PER_EVENT.
   - For each file:
     - Generate object key: uuid4hex + "/" + timestamp + "__" + safe_filename (implement safe sanitize).
     - Stream upload to MinIO via storage wrapper.
     - On success, insert attachments DB row in same logical operation; ensure if DB insert fails after object upload, delete object (compensating action).
   - Return attachment metadata list (id, filename, key, content_type, size_bytes, uploaded_at).
3. Ensure app startup calls ensure_bucket to create bucket if missing.
4. Tests:
   - tests/test_attachments.py using testcontainers MinIO container:
     - Upload a small valid file and assert DB row created and object exists in MinIO (use storage client to stat or presign URL fetch).
     - Attempt to upload an oversized file and assert 413 returned.
     - Attempt to upload disallowed MIME type and assert 415 returned.
     - Simulate DB failure after object upload (monkeypatch repository or raise exception) and assert object was deleted (no orphan).
5. Wiring:
   - Register attachments router in app/main.py under /api/events/{id}/attachments.
   - Ensure env vars default values set in .env.example.

Requirements:
- Use streaming upload, avoid loading entire file into memory.
- Tests must clean up objects they create.

Deliverables:
- app/services/storage.py
- app/api/attachments.py
- tests/test_attachments.py
- .env.example updates and startup ensure_bucket call

After generating code, run:
- pip install -r requirements.txt
- pytest tests/test_attachments.py (requires docker)
```

Verification & manual steps:
- Run the attachment upload tests locally (requires docker).
- Manual test: use curl to POST a small image to the endpoint and verify returned metadata and presence in MinIO console.

Checklist:
- [ ] Implement MinIO client wrapper with threaded calls
- [ ] Implement upload endpoint with full validation and compensating deletion
- [ ] Startup creates bucket if missing
- [ ] Attachment tests (upload success, oversize, bad MIME, orphan cleanup)
- [ ] Register router and document env vars

---

PROMPT 5 — Attachment serving (presigned URLs) & deletion cascade
- Goal: Implement attachment download endpoint that returns presigned URLs and implement event deletion cascade including object deletion (best-effort).
- Rationale: Serving attachments via presigned URLs is preferred for perf and security.

Code-generation prompt:
```text
Implement attachment serving and deletion handling.

Tasks:
1. Implement GET /api/attachments/{key}:
   - Returns { "url": "<presigned-url>" } signed with configured expiry (e.g., 300s).
   - Enforce Authorization header (Bearer token) — if missing, return 401 (we will implement token auth in next prompt; for now optionally bypass in test mode).
2. Implement DELETE /api/events/{id} to:
   - Delete event row (ON DELETE CASCADE removes attachments DB rows).
   - After DB deletion, attempt to delete objects from MinIO for attachments (best-effort). If many attachments, perform deletion synchronously for now.
   - If MinIO deletion fails, log and continue.
3. Tests:
   - tests/test_attachment_serve.py using MinIO container:
     - Upload a file in setup, call GET /api/attachments/{key}, fetch presigned URL and perform HTTP GET to confirm object content returned.
   - tests/test_delete_cascade.py:
     - Create event with attachments, call DELETE /api/events/{id}, assert DB rows removed and that MinIO objects are deleted.
4. Wiring:
   - Register new routes in app/main.py.
   - Add config for PRESIGN_EXPIRY_SECONDS env var.

Requirements:
- Use storage wrapper to generate presigned URLs.
- Tests must assert deletion attempts or successful deletion.

Deliverables:
- app/api/attachments.py additions for GET presign
- app/api/events.py delete logic enhanced to call storage.delete_object for attachments
- tests/test_attachment_serve.py and tests/test_delete_cascade.py

After generating code, run:
- pytest -q (integration tests require docker)
```

Verification & manual steps:
- Manually get presigned URLs via API and fetch object in browser/HTTP client.
- Confirm delete event cleans DB rows and removes object from MinIO.

Checklist:
- [ ] Implement presigned URL endpoint
- [ ] Ensure delete event triggers MinIO object deletion
- [ ] Tests for presign and cascade deletion pass
- [ ] Config for presign expiry added

---

PROMPT 6 — Search endpoint (Postgres full-text + tag/date filters)
- Goal: Implement GET /api/events search that uses Postgres full-text search (websearch_to_tsquery) with tag & date filters, ranking, and pagination. Add tests for search scenarios.
- Rationale: Search is a key capability.

Code-generation prompt:
```text
Implement full-text search and filters for events.

Tasks:
1. Implement /api/events search parameters:
   - q (text): full-text search using websearch_to_tsquery('english', q)
   - tags (comma separated or multiple query param): when provided, treat as AND by default
   - start, end timestamps to filter events.timestamp
   - sort: newest|oldest|relevance (relevance only when q provided)
   - pagination via page/page_size with defaults and max limit
2. Implement SQLAlchemy query integrating:
   - search_vector @@ websearch_to_tsquery when q present
   - tags overlap or contain semantics (for AND semantics, build queries using array containment)
   - timestamp range filters
   - ordering by ts_rank_cd(search_vector, query) for relevance
3. Ensure indexes exist in DB migration (done in earlier migration).
4. Add tests tests/test_search.py:
   - Insert sample events with titles/descriptions and tags and timestamps.
   - Test q searches return expected items and ordering.
   - Test tags filtering returns correct items.
   - Test date range filter works.
   - Test pagination works.
5. Wiring:
   - Expose search via GET /api/events endpoint (same route; search params optional).
   - Document query parameter usage in README.

Requirements:
- Use SQLAlchemy Core or ORM queries that can incorporate func.websearch_to_tsquery and func.ts_rank_cd.
- Tests should assert correctness and relative ordering for relevance.

Deliverables:
- Updated app/services/event_service.py list_events with search implementation
- tests/test_search.py

After generating code, run:
- pytest tests/test_search.py
```

Verification & manual steps:
- Run search tests.
- Manual test: create a few events and query via curl confirming search result ordering.

Checklist:
- [ ] Implement full-text search with websearch_to_tsquery
- [ ] Tag and date filters implemented
- [ ] Tests for search correctness and ranking pass
- [ ] README updated for search params

---

PROMPT 7 — Authentication & admin session
- Goal: Add token-based API auth, admin password web login for UI sessions, token rotation endpoint.
- Rationale: Security and token rotation needed for CLI/automation.

Code-generation prompt:
```text
Implement authentication for API and web UI.

Tasks:
1. Design and implement API token storage:
   - Use a simple single-token model persisted (either in DB table server_settings or hashed in file). Prefer DB table (app/models/setting.py) with key/value and hashed_token field.
   - Implement utilities to generate random token and store a hashed copy (use passlib pbkdf2_sha256 or bcrypt).
   - Provide function verify_token(plaintext_token) that checks against stored hash.
2. Add FastAPI dependency for token auth:
   - Security scheme: Authorization: Bearer <token>
   - A dependency get_current_user_or_401 that validates token and raises 401 if missing/invalid.
   - Apply dependency to API routes that require token (attachments endpoints, export, presigned URL, delete events). For now, apply to all /api/* endpoints (except health and auth).
3. Web UI admin password:
   - ADMIN_PASSWORD provided via env; store password hashed in DB on first run (or compare directly via constant-time compare). Implement login route POST /auth/login that sets a secure session cookie using itsdangerous or starlette session middleware.
   - Implement logout route to clear session.
   - Protect UI routes with session cookie check.
4. Token rotation endpoint POST /api/auth/token/rotate:
   - Accept admin password (or require session) to authorize rotation.
   - Generate new token, store hashed, and return plaintext token in response (show once).
   - Invalidate old token immediately.
5. Tests:
   - tests/test_auth.py:
     - Test that API endpoints return 401 without Bearer token.
     - Test token rotation: old token fails after rotation and new token works.
     - Test admin login route sets cookie and protects UI endpoints.
6. Wiring:
   - Add models/settings for hashed token and admin password storage
   - Add config env var RUN_MIGRATIONS to allow initial token generation/path.

Requirements:
- Never return stored hashed token; only show newly generated token once.
- Use secure cookie flags; for dev local, secure flag may be off.
- Password/hash functions via passlib recommended.

Deliverables:
- app/auth/* modules (token utilities, dependencies)
- app/api/auth.py endpoints for rotation and login
- tests/test_auth.py

After generating code, run:
- pytest tests/test_auth.py
- Manually test login flow via curl / simple HTML form later
```

Verification & manual steps:
- Run auth tests.
- Manually curl a protected endpoint without token (401) and with correct token (200). Test token rotation behavior.

Checklist:
- [ ] Implement token storage and verification
- [ ] Add FastAPI token auth dependency and apply to endpoints
- [ ] Implement admin web login session
- [ ] Implement token rotation endpoint
- [ ] Tests for auth behavior

---

PROMPT 8 — Export endpoint and CLI
- Goal: Implement export endpoint (/api/export) and a thin CLI to create events, attach files, and export. Ensure token-based CLI auth.
- Rationale: Users must export for backups and have a CLI for quick captures.

Code-generation prompt:
```text
Implement export API and CLI commands.

Tasks:
1. Implement GET /api/export API endpoint:
   - Return application/json of all events and their attachments metadata (no binary).
   - Optional query param include_presigned_urls=true to include short-lived presigned URLs for attachments (admin only).
   - Protect endpoint with token auth.
2. Implement CLI under app/cli/ using click or argparse:
   - Commands:
     - create-event --title --description --tags --timestamp
     - attach-file --event-id --file PATH
     - export --out FILE [--include-urls]
   - CLI reads API_TOKEN from env LIFLOG_API_TOKEN or config file.
   - CLI uses httpx to interact with API; proper error handling and exit codes.
3. Tests:
   - tests/test_cli.py:
     - Use a running test server or the FastAPI test client to run CLI commands pointing at local test server.
     - Test create-event and export flows.
4. Wiring:
   - Add entrypoint script (bin/lifelog-cli) or instructions in README to run `python -m app.cli`.
   - Make sure CLI uses same auth token mechanism.
5. Documentation:
   - README examples for using CLI and export.

Requirements:
- Export results must contain attachment keys and metadata so objects can be retrieved later.
- If include_presigned_urls requested, those are included when requested and admin token used.

Deliverables:
- app/api/export.py
- app/cli/__init__.py and command implementations
- tests/test_cli.py
- README CLI examples

After generating code, run:
- pytest tests/test_cli.py (may require running test server)
- Try CLI locally against running dev server
```

Verification & manual steps:
- Run CLI commands against dev server with a valid API token.
- Export JSON and inspect content.

Checklist:
- [ ] Implement export endpoint with include_presigned_urls option
- [ ] Implement CLI commands for create-event, attach-file, export
- [ ] Tests for CLI operations
- [ ] README updated with CLI usage

---

PROMPT 9 — Web UI: Jinja2 + HTMX minimal experience
- Goal: Implement minimal server-rendered UI: timeline view, quick-add, event detail, settings (rotate token). Use HTMX for quick-add and inline edits.
- Rationale: Provide minimal interactive web experience.

Code-generation prompt:
```text
Implement the minimal web UI with Jinja2 and HTMX.

Tasks:
1. Integrate Jinja2 templates into FastAPI (app/templates/).
2. Create views and routes:
   - GET / -> timeline page: shows paginated events (title, timestamp, tags snippet).
   - POST /quick-add -> endpoint that accepts simple form (title, optional tags) and creates event via event_service; Use HTMX to submit and update timeline fragment.
   - GET /events/{id} -> event detail page with attachments (image previews where possible) and edit/delete actions.
   - GET/POST /settings -> allow admin to rotate API token (calls POST /api/auth/token/rotate behind the scenes); only accessible when logged in.
3. UI elements:
   - Minimal CSS (or none); keep markup usable.
   - For attachments, show small thumbnail/icon and link to presigned URL (via GET /api/attachments/{key}).
4. Tests:
   - Basic integration tests to ensure pages render (tests/test_ui.py) using AsyncClient and template rendering checks. Full browser E2E not required for MVP.
5. Manual verification:
   - Run app, visit http://localhost:8000/, login using admin password, create quick-add event, navigate to event detail, upload an attachment, view presigned link.
6. Wiring:
   - Protect settings routes with session-based admin login.
   - HTMX endpoints should return partial templates for inline updates.

Requirements:
- Keep UI minimal; focus on functionality over styling.
- Ensure CSRF considerations for forms (for MVP, same-site cookies + session should suffice).

Deliverables:
- app/templates/*.html (base, timeline, event_detail, settings)
- app/api/ui_routes.py or app/ui.py (views)
- tests/test_ui.py
- README manual UI steps

After generating code, run:
- Start server and manually exercise UI features
- Run tests/test_ui.py
```

Verification & manual steps:
- Start server, login, use quick-add, create event, upload file, view event detail.
- Verify settings token rotation works via UI.

Checklist:
- [ ] Integrate Jinja2 templates and HTMX usage
- [ ] Implement timeline, quick-add, event detail, settings pages
- [ ] Basic UI integration tests
- [ ] Manual verification documented

---

PROMPT 10 — Cleanup, GC, logging, and operational polish
- Goal: Implement best-effort garbage collection and orphan object scan, structured logging, error id logging for 500s; finalize envs, limits, and README runbook.
- Rationale: Operational hygiene and safety.

Code-generation prompt:
```text
Implement operational polish: GC task, logging, limits, and documentation.

Tasks:
1. Implement an admin-only endpoint or CLI task `gc-orphans` that:
   - Scans MinIO bucket for objects with or without DB attachment rows (match by prefix or key).
   - Optionally deletes orphaned objects when `--delete` flag provided.
   - Provide tests (integration) that create an orphan object and confirm GC finds it and that `--delete` removes it.
2. Improve logging:
   - Structured logs (JSON or structured messages) with LOG_LEVEL env var.
   - For unhandled exceptions, generate a unique error_id (uuid) returned in user-facing 500 error response, and log stack trace with error_id.
3. Add telemetry/health endpoints:
   - /health already exists; add /ready that checks DB + MinIO.
4. Enforce limits:
   - Ensure FILE_MAX_BYTES, ATTACHMENT_MAX_PER_EVENT, ALLOWED_MIME_TYPES are respected in attachments service.
   - Add config validation at startup (fail fast if misconfigured).
5. Documentation:
   - Finalize README with deployment steps, env vars, backup/export instructions, troubleshooting, and acceptance criteria checklist.

Deliverables:
- app/management/gc.py (CLI / admin endpoint)
- logging configuration and exception handler
- readiness endpoint
- tests/test_gc.py
- Updated README and .env.example

After generating code, run:
- pytest -q (run GC tests and logging behavior tests)
- Manual GC run against dev MinIO
```

Verification & manual steps:
- Run GC with an orphan in MinIO and verify behavior.
- Trigger a server error to view error id in response and logs.

Checklist:
- [ ] Implement orphan GC scan and delete option
- [ ] Structured logging and 500 error ID
- [ ] Readiness endpoint added
- [ ] Limits enforced and validated at startup
- [ ] README operational docs completed

---

PROMPT 11 — CI finalization & docker-compose acceptance
- Goal: Finalize GitHub Actions CI to run unit and integration tests (optionally using testcontainers), build Docker image, and include docker-compose ready-to-run configuration with migrations on startup.
- Rationale: CI and reproducible local deployment.

Code-generation prompt:
```text
Finalize CI and deployment wiring.

Tasks:
1. Update .github/workflows/ci.yml:
   - Steps: checkout, set up Python, install dependencies, run static checks (ruff/black), run pytest (unit tests).
   - Optionally: run integration tests using testcontainers or run docker-compose services (only if CI runner supports docker).
2. Update Dockerfile for production image best practices (install dependencies, copy code, set environment default for RUN_MIGRATIONS).
3. Update docker-compose.yml:
   - app service entrypoint should run migrations (if RUN_MIGRATIONS=true) then start uvicorn.
   - Ensure services: db, minio, pgadmin configured properly with volumes.
   - Add healthchecks for db and minio in compose file.
4. Acceptance test instructions:
   - Provide commands: docker-compose up --build and curl to API endpoints to validate system works.
   - Add a small acceptance test script tests/acceptance/run_acceptance.sh that hits /health, creates an event, uploads attachment (small), and runs search.
5. Deliverables:
   - Updated CI workflow
   - Production-ready Dockerfile and docker-compose.yml
   - acceptance test script and README instructions

After generating code, run:
- Local: docker-compose up --build (verify app becomes ready and /health returns ok)
- CI: run pipeline locally or rely on GitHub Actions
```

Verification & manual steps:
- Run docker-compose up --build locally; ensure app migrates and is available.
- Run acceptance script and confirm flows.

Checklist:
- [ ] CI workflow updated to run lint & tests
- [ ] Dockerfile production-ready
- [ ] docker-compose runs migrations and starts app
- [ ] Acceptance test script created
- [ ] README updated with docker-compose instructions

---

PROMPT 12 — Final docs, runbook, and acceptance checklist
- Goal: Produce final README/runbook, provide acceptance checklist and troubleshooting, and prepare release notes for MVP.
- Rationale: Ensure others can deploy and maintain.

Code-generation prompt:
```text
Prepare final documentation, acceptance checklist, and release notes.

Tasks:
1. Complete README.md with:
   - Project summary and goals (from devSpec)
   - Quickstart (dev: pip & uvicorn; docker-compose)
   - Env variables reference (.env.example)
   - How to run tests and CI notes
   - How to generate/rotate tokens and login to UI
   - How to backup/export and restore
   - Troubleshooting common issues
2. Add ACCEPTANCE.md with:
   - Concrete acceptance tests (deploy via docker-compose, create event, upload, search, export, rotate token, login to UI).
   - Expected outputs and verification steps.
3. Add CHANGELOG.md for MVP release 1.0 with notable decisions (single-user token, MinIO attachments, Postgres full-text).
4. Final checklist:
   - Ensure no secrets in repository
   - Ensure pgAdmin bound to 127.0.0.1 instruction present
   - Ensure env.example up-to-date

Deliverables:
- README.md (complete)
- ACCEPTANCE.md
- CHANGELOG.md

After generating code, run:
- Manual: follow README quickstart to deploy and run acceptance checklist.
```

Verification & manual steps:
- Follow README and perform acceptance tests end-to-end.

Checklist:
- [ ] README completed with quickstart and troubleshooting
- [ ] ACCEPTANCE.md with step-by-step checks
- [ ] CHANGELOG.md created
- [ ] Ensure no secrets are committed

-----------------------------
SECTION C — Notes on testing strategy and CI
-----------------------------
- Unit tests: run in CI by default; should not require Docker.
- Integration tests (Postgres/MinIO): mark with pytest marker integration and run only when docker/testcontainers available; optionally enable a CI matrix job for integration tests that uses service containers.
- Use testcontainers-python for reproducible integration tests in developer machines and CI where supported.
- Keep tests idempotent and teardown-created resources.

-----------------------------
SECTION D — Example of one detailed prompt iteration (from milestone to tiny steps)
-----------------------------
The prompts above are high-level. Below is an example of how a single prompt (PROMPT 4: Attachments backend) can be further broken into very small steps for safe incremental implementation and testing. Use this pattern for other prompts if you prefer even smaller increments.

PROMPT 4a — Add MinIO client wrapper
```text
Implement a MinIO client wrapper (storage.py) that provides ensure_bucket, upload_object, presign_get, delete_object.

Tasks:
1. Add dependency minio to requirements.txt.
2. Create app/services/storage.py with Minio client initialization using MINIO_ENDPOINT, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD, MINIO_BUCKET.
3. Implement ensure_bucket(bucket_name): checks and creates bucket.
4. Implement upload_object(bucket, object_name, fileobj, length, content_type, metadata) wrapping blocking minio.put_object via asyncio.to_thread.
5. Implement presign_get(bucket, object_name, expires_seconds) using minio.presigned_get_object wrapped in to_thread.
6. Implement delete_object(bucket, object_name) via to_thread.

Tests:
- Unit tests that mock the minio client to ensure upload_object calls client.put_object appropriately (use monkeypatch).
- Integration test later will test real MinIO.

Deliverables:
- app/services/storage.py and updated requirements.txt
```

Checkable tasks:
- [ ] Install minio dependency
- [ ] Implement storage wrapper functions
- [ ] Create unit test for storage wrapper

PROMPT 4b — Implement upload endpoint that uses storage wrapper
```text
Implement POST /api/events/{id}/attachments that uses storage wrapper.

Tasks:
1. Create endpoint in app/api/attachments.py accepting files as UploadFile.
2. Validate file size via UploadFile.file.seek/read or content length header (prefer streaming read).
3. Implement safe filename sanitization.
4. Use storage.upload_object to stream file to MinIO and then insert attachment DB row.
5. Implement compensating deletion if DB insert fails.
6. Return created attachments metadata.

Tests:
- Functional test uploading small file using mocked storage wrapper; assert correct DB insert call and returned JSON.

Deliverables:
- app/api/attachments.py
- tests/test_attachments_unit.py
```

Continue PROMPT 4c for integration tests against real MinIO.

-----------------------------
SECTION E — Delivering prompts to a code-generation LLM
-----------------------------
- Feed each code-generation prompt (the code block content above) to the code-generation LLM in order.
- For each prompt you must:
  1. Generate code + tests.
  2. Run unit tests locally.
  3. If tests require Docker, run integration tests locally with Docker and only then mark checklist item as done.
  4. Commit changes and push or create a PR for review.
- When a prompt asks for "Return:" or "Deliverables", capture the exact file list and quick run instructions in the PR description.

-----------------------------
SECTION F — Final notes and acceptance criteria
-----------------------------
MVP acceptance criteria (from devSpec) mapped to prompts:
- docker-compose deployable — covered in PROMPT 11
- Admin web UI login — PROMPT 7 + PROMPT 9
- API token present & usable — PROMPT 7 + PROMPT 8
- Create events & upload attachments — PROMPT 3 + PROMPT 4
- Search — PROMPT 6
- Export endpoint — PROMPT 8
- pgAdmin host binding — PROMPT 0/.env and docker-compose updates in PROMPT 11
- Limits & MIME enforced — PROMPT 4 and PROMPT 10
- Tests exist for core flows — each prompt requires tests

If you'd like, I can:
- Produce actual concrete code generation LLM prompts for each of the above code blocks formatted for direct use with a code-generation LLM, or
- Start executing the first prompt by generating the repository skeleton (PROMPT 0) now.

Which would you like to do next?