# LifeLog — One-Pager (MVP)

Summary
- Problem: Need a self-hosted, low-maintenance personal life-log to quickly record events (moments, receipts, notes, media) with flexible metadata and attachments.
- Primary goal: Fast, reliable capture + searchable chronicle that is easy to run locally in a single docker-compose stack and extensible later.
- Target user: Single tech-savvy self-hosting owner (Python developer) who primarily interacts via API/CLI and occasionally via a simple web UI on the local network.

Core decisions (final)
- Platform: Browser-accessible web app + CLI. API-first.
- Backend: FastAPI with server-rendered Jinja2 templates and HTMX for small interactive flows.
- DB: PostgreSQL with tsvector full-text search and GIN index.
- File storage: RustFS (S3-compatible) included in docker-compose.
- Auth: Single admin password (provided by environment variable) for web UI; single API token for CLI/API.
- Attachments: Multiple per event (configurable limit), default 10 MB per file, whitelist MIME types (images/docs/media).
- Compose services: app, postgres, rustfs, pgadmin (pgAdmin bound to localhost only).
- Backups: Manual export endpoint + CLI export (no automated backups in MVP).
- Migration tool: Alembic; ORM: SQLAlchemy.

MVP scope (must-have)
- API (FastAPI):
  - CRUD for events
  - Attachments upload/download via RustFS
  - Search endpoint (Postgres full-text tsvector + tag/date filters)
  - Export endpoint (JSON of events + attachment keys)
  - Token-based API auth
- Web UI (Jinja2 + HTMX):
  - Timeline (newest-first) with compact cards
  - Quick-add bar for instant capture (title + tags)
  - Full event form (timestamp, title, description, tags, attachments, metadata JSON)
  - Event detail with preview/download, edit, delete
  - Settings page (rotate API token, file-size limit)
- CLI:
  - create-event (title, description, tags, timestamp)
  - attach-file (upload file and link to event)
  - export (download all events JSON)
  - CLI authenticates with API token
- Storage & infra:
  - Postgres (with tsvector + GIN index)
  - RustFS in compose with a default bucket
  - pgAdmin available on host (127.0.0.1 only)
  - Single docker-compose for full stack
- Security & limits:
  - Admin password via ENV for web UI
  - API token generated on first-run (or provided via ENV)
  - File-size limit default 10 MB (env-configurable)
  - Allowed MIME types whitelist (block executables)

Event model (MVP schema)
- Table: events
  - id: BIGSERIAL PRIMARY KEY
  - created_at: TIMESTAMPTZ NOT NULL DEFAULT now()
  - timestamp: TIMESTAMPTZ NOT NULL (user editable; defaults to now())
  - title: TEXT NOT NULL
  - description: TEXT
  - tags: TEXT[] (or text column with normalized comma-separated tags)
  - metadata: JSONB (optional structured data)
  - attachments: stored in attachments table (see below)
  - search_vector: tsvector (generated/maintained for title + description + tags)
- Table: attachments
  - id: BIGSERIAL PRIMARY KEY
  - event_id: FK -> events.id
  - key: TEXT (S3/RustFS object key)
  - filename: TEXT
  - content_type: TEXT
  - size_bytes: BIGINT
  - uploaded_at: TIMESTAMPTZ
- Indexes:
  - GIN index on events.search_vector
  - Index on events.timestamp (for sorting)
  - Index on tags if using array type

Search design
- Use Postgres tsvector stored in search_vector and a GIN index:
  - Populate/maintain via trigger or generated column updated on insert/update.
  - Ranking and basic phrase matching supported.
  - API supports:
    - q=<text> (full-text)
    - tags=tag1,tag2 (AND/OR semantics configurable)
    - start=<date>&end=<date>
    - sort: newest-first default
- Reason: chosen for accurate relevance and scalability while staying within single Postgres service.

API surface (high-level)
- Auth
  - Authentication: Bearer token (Authorization: Bearer <API_TOKEN>) for API; web UI uses session after admin password login.
- Key endpoints (more details in tech spec):
  - POST /api/events — create event (title, description, timestamp, tags, metadata)
  - GET /api/events — list events (pagination, sort, filters)
  - GET /api/events/{id} — read event detail
  - PATCH /api/events/{id} — update event
  - DELETE /api/events/{id} — delete event
  - POST /api/events/{id}/attachments — upload attachment (multipart/form-data => stream to RustFS)
  - GET /api/attachments/{key} — proxy/download attachment (signed URL or server-stream with creds)
  - GET /api/search — search endpoint (q, tags, date range, pagination)
  - GET /api/export — export all events JSON (optionally return presigned URLs)
  - POST /api/auth/token/rotate — rotate API token (admin only)
- Notes:
  - API returns S3 object keys and optionally presigned URLs (short-lived) for downloads.
  - Uploads should be streamed and validated (size & MIME).

Web UI flow (UX)
- Landing / Timeline:
  - Shows newest-first compact cards: timestamp, title, tags, short snippet, attachment icons.
- Quick-add bar:
  - Single-line title input + tags input + Add button: creates event with timestamp = now().
- Full event form:
  - Editable timestamp, title, multi-line description, tags, metadata JSON (advanced), attachments upload.
- Event detail:
  - Full display, list attachments with preview/download, edit/delete actions.
- Search/filters:
  - Text search, date range picker, multi-tag filter.
- Settings:
  - Rotate API token, configure file-size limit, view RustFS bucket name, change admin password (optionally).

CLI
- Lightweight Python CLI that uses same API with token.
- Commands:
  - create-event --title "..." [--desc "..."] [--tags "a,b"] [--timestamp "..."]
  - attach-file --event-id 123 --file ./photo.jpg
  - export --out events.json
- Authentication via env var LIFLOG_API_TOKEN or config file.
- Suitable for bulk imports, scripts, and backups.

Docker Compose (high-level)
- Services:
  - app (FastAPI)
    - image: built from repo
    - ports: 0.0.0.0:8000:8000
    - env:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/lifelog
      - RUSTFS_ENDPOINT=rustfs:9000
      - ADMIN_PASSWORD (provided via env at runtime)
      - API_TOKEN (optional; generated if missing)
      - FILE_MAX_BYTES (default 10_485_760)
      - ALLOWED_MIME_TYPES (comma separated)
    - depends_on: db, rustfs
    - volumes: ./data/uploads (optional) for local caching
    - entrypoint: run migrations (Alembic) then start Uvicorn
  - db (Postgres)
    - image: postgres:15
    - environment: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
    - volumes: pgdata:/var/lib/postgresql/data
  - rustfs
    - image: rustfs/rustfs
    - command: server /data --console-address ":9001"
    - environment: RUSTFS_ACCESS_KEY, RUSTFS_SECRET_KEY
    - ports: 9000:9000, 9001:9001
    - volumes: rustfs-data:/data
    - healthcheck: appropriate http check
  - pgadmin
    - image: dpage/pgadmin4
    - environment: PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD
    - ports: 127.0.0.1:8080:80   # bound to localhost only (per spec)
    - volumes: pgadmin-data:/var/lib/pgadmin
- Volumes:
  - pgdata, rustfs-data, pgadmin-data
- Notes:
  - App must create RustFS bucket on startup if missing (via rustfs client or SDK).
  - Alembic migrations run on app startup (entrypoint handles migrations).

Environment variables (recommended defaults / names)
- ADMIN_PASSWORD (required on first deploy; hashed in DB)
- API_TOKEN (if omitted, app generates one and outputs to logs on first run)
- DATABASE_URL (postgres connection)
- POSTGRES_* for db container
- RUSTFS_ACCESS_KEY, RUSTFS_SECRET_KEY
- RUSTFS_BUCKET (default: lifelog-attachments)
- FILE_MAX_BYTES (default: 10_485_760 -> 10 MB)
- ATTACHMENT_MAX_PER_EVENT (default: 10)
- ALLOWED_MIME_TYPES (default: image/jpeg,image/png,image/webp,application/pdf,text/plain,text/markdown,text/csv,video/mp4)
- PGADMIN_EMAIL, PGADMIN_PASSWORD (pgAdmin)
- LOG_LEVEL

Attachment policy & security
- Multiple attachments allowed per event (default up to 10).
- Default max 10 MB per file (env-configurable).
- Allowed MIME types whitelisted (images, pdf, plain text, csv, mp4). Block common executable types (.exe, .sh).
- Validate content type and size server-side, and enforce limits before streaming full upload.
- Store attachments in RustFS with non-guessable keys (UUID + original filename metadata).
- Prefer serving downloads via short-lived presigned URLs; if the app proxies downloads, ensure proper auth checks.
- If exposing the app publicly, put a reverse proxy (Caddy/Traefik) in front with HTTPS and optional Basic auth.

Operational notes
- Migrations: Alembic + SQLAlchemy models. Entrypoint should run alembic upgrade head automatically.
- Tests: unit tests for API handlers, storage interface (RustFS), search behavior, and CLI.
- CI: build image, run migrations, run test suite, lint (black/ruff).
- Logging/observability: structured logs, file rotation for uploads if needed.
- Backups: MVP relies on manual export (GET /api/export) and CLI export. Recommend a later cron job that dumps Postgres and uploads to RustFS (small container) when ready.

Acceptance criteria (MVP)
- Deployable via single docker-compose up.
- Admin can log in via web UI using ADMIN_PASSWORD set via env on first run.
- API token available (generated or set) and usable to authenticate CLI commands.
- Able to create events via web UI quick-add and full form.
- Attachments can be uploaded and associated with events; stored in RustFS.
- Search works via full-text query, tag filtering, date range.
- Events can be exported as JSON via UI and CLI.
- pgAdmin is accessible at http://127.0.0.1:8080 and can connect to the Postgres container.
- File size and MIME limits enforced and configurable.

Implementation recommendations for engineering
- Stack / libraries:
  - FastAPI (web + API)
  - Jinja2 + HTMX for UI interactivity
  - SQLAlchemy (1.x) + asyncpg / async SQLAlchemy usage
  - Alembic for migrations
  - python-multipart for uploads
  - minio-py or boto3 for RustFS interactions
  - passlib for password hashing
  - python-dotenv support for env file in development
- DB tsvector:
  - Create a GENERATED column or trigger to update search_vector from title, description, and tags.
  - Create GIN index: CREATE INDEX ON events USING GIN(search_vector);
- Uploads:
  - Use streaming multipart handling to avoid loading large files into memory.
  - Validate content type & size early.
  - Generate object keys with UUIDs.
- Authentication:
  - Web login -> session cookie (secure, HttpOnly).
  - API -> Authorization: Bearer <token>.
- CLI:
  - Simple click-based or argparse Python CLI that calls API; distribute in repo.

Security checklist (MVP)
- Admin password set by environment variable; change default in production.
- API token = long random secret; store securely.
- pgAdmin bound to 127.0.0.1 only.
- Enforce file type & size server-side.
- If exposing publicly, require TLS and a reverse proxy with additional auth as needed.

Roadmap / Next steps (post-MVP)
- Optional: automated daily backups (pg_dump + upload to RustFS).
- Optional: thumbnail/preview generation for images & videos.
- Optional: full user accounts / multi-tenant support.
- Optional: richer analytics, timeline visualizations.
- Optional: add webhooks / integrations for automated event ingestion (IFTTT, Zapier).
- Optional: more robust search ranking & fuzzy matching; incremental tsvector updates.

Deliverables for technical-spec stage (what product & engineering leadership need next)
- Detailed API spec (OpenAPI) with request/response examples and error codes.
- DB schema SQL & Alembic migration initial script.
- Docker-compose YAML with service definitions (app, db, rustfs, pgadmin) and default env sample file (.env.example).
- Minimal UI wireframes for timeline, quick-add, full event form, event detail, settings.
- Security & deployment checklist (reverse proxy config examples for Caddy/Traefik).
- Implementation plan with rough sprint estimate (see suggested breakdown below).

Estimated implementation breakdown (indicative)
- Week 0 — setup & scaffolding:
  - Repo, CI, docker-compose, base FastAPI app, DB connection, Alembic.
- Week 1 — models & API:
  - Implement events/attachments models, migrations, basic CRUD endpoints.
- Week 2 — storage & uploads:
  - Integrate RustFS, implement upload endpoints, object key management, validations.
- Week 3 — search & indexes:
  - tsvector generation, GIN index, search endpoint.
- Week 4 — web UI + HTMX:
  - Timeline, quick-add, full forms, attachments UI, settings page.
- Week 5 — CLI + polish:
  - CLI commands, export endpoint, token rotation, tests, docs.
- Week 6 — deployment & hardening:
  - finalize docker-compose, pgAdmin binding, logging, docs, handoff.

Contact / owner
- Product owner: (you)
- Suggested engineering lead: backend with FastAPI experience + ops/devops for docker-compose and RustFS.

Appendix: key defaults to include in .env.example
- ADMIN_PASSWORD=CHANGE_ME
- API_TOKEN= # optional; auto-generated if blank
- DATABASE_URL=postgresql+asyncpg://lifelog:lifelogpass@db:5432/lifelog
- RUSTFS_ACCESS_KEY=rustfsadmin
- RUSTFS_SECRET_KEY=rustfsadmin
- RUSTFS_BUCKET=lifelog-attachments
- FILE_MAX_BYTES=10485760
- ATTACHMENT_MAX_PER_EVENT=10
- ALLOWED_MIME_TYPES=image/jpeg,image/png,image/webp,application/pdf,text/plain,text/markdown,text/csv,video/mp4
- PGADMIN_EMAIL=admin@example.com
- PGADMIN_PASSWORD=pgadminpass

If you approve, I can:
- Generate a starter tech-spec (OpenAPI + DB migration + docker-compose snippet).
- Or produce the initial repo layout and single-file prototype plan for engineering to start implementing. Which next artifact do you want first?