# LifeLog

LifeLog is a self-hosted, personal life-logging application designed for quick capture of events, notes, and moments. It provides a reliable and fast way to chronicle your life with flexible metadata and attachments, all fully searchable and hosted locally.

## Getting Started

### 1. Prerequisites
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)

### 2. Setup
1.  **Configure environment variables**:
    Copy the example environment file and update the passwords:
    ```bash
    cp .env.example .env
    ```
    Open `.env` and set secure values for `APP_AUTH_ADMIN_PASSWORD`, `POSTGRES_PASSWORD`, and `RUSTFS_SECRET_KEY`.

2.  **Start the application**:
    ```bash
    docker-compose up -d
    ```
    This will start the API, PostgreSQL database, RustFS (S3-compatible storage), and pgAdmin.

### 3. Verify it's working
To ensure everything is set up correctly, use `curl` to add your first life log event:

```bash
# Replace YOUR_ADMIN_PASSWORD with the one set in your .env
curl -X POST http://localhost:8000/api/events/ \
  -H "Authorization: Bearer YOUR_ADMIN_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Initial Setup Complete",
    "description": "LifeLog is up and running!",
    "tags": ["setup", "log"]
  }'
```

You should receive a `201 Created` response with the details of your new event.

## Tips

- Generate random passwords for necessary `.env` variables:
  - `$ openssl rand -base64 32`

## Features

- **FastAPI Backend**: Robust and fast API-first design.
- **Web Interface**: Simple, server-rendered UI for browsing timelines and capturing events.
- **CLI Tool**: Efficient command-line interface for quick entry and bulk operations.
- **Search**: Full-text search capabilities using PostgreSQL `tsvector`.
- **Storage**: S3-compatible object storage (RustFS) for handling attachments.
- **Self-Hosted**: Runs entirely in a local Docker Compose stack for privacy and control.

## Documentation

Comprehensive documentation and planning files used to generate and guide this project are located in the `docs/` directory:

- [`docs/ONE_PAGER.md`](docs/ONE_PAGER.md): High-level overview of the project's goals, features, and MVP requirements.
- [`docs/DEV_SPEC.md`](docs/DEV_SPEC.md): Technical specifications including API endpoints, database schema, and architecture decisions.
- [`docs/AGENTS.md`](docs/AGENTS.md): Directives and context for AI agents working on the codebase.
- [`docs/PROMPT_PLAN.md`](docs/PROMPT_PLAN.md): Strategic planning for AI-assisted development and prompting strategies.

- **Tooling**: Managed by `uv` for fast dependency resolution and environment management.

## TODO

- [ ] Convert to using `uv`.

  - ```dockerfile

    FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim
    WORKDIR /app
    COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
    COPY . .

    # Disable development dependencies.
    ENV UV_NO_DEV=1

    # Sync the project into a new environment, asserting the lockfile is up to date.
    RUN uv sync --locked

    # Run the application.
    CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

    ```

- [ ] Replace `setuptools` with something else (e.g. `hatchling`).
