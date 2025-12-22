# LifeLog

LifeLog is a self-hosted, personal life-logging application designed for quick capture of events, notes, and moments. It provides a reliable and fast way to chronicle your life with flexible metadata and attachments, all fully searchable and hosted locally.

## Getting Started

- Generate a random password for the admin user:
  - `$ openssl rand -base64 32`

- Generate a random API token for the admin user:
  - `$ python -c 'import uuid; print(uuid.uuid4())'`


## Features

- **FastAPI Backend**: Robust and fast API-first design.
- **Web Interface**: Simple, server-rendered UI for browsing timelines and capturing events.
- **CLI Tool**: Efficient command-line interface for quick entry and bulk operations.
- **Search**: Full-text search capabilities using PostgreSQL `tsvector`.
- **Storage**: S3-compatible object storage (MinIO) for handling attachments.
- **Self-Hosted**: Runs entirely in a local Docker Compose stack for privacy and control.

## Documentation

Comprehensive documentation and planning files used to generate and guide this project are located in the `docs/` directory:

- [`docs/ONE_PAGER.md`](docs/ONE_PAGER.md): High-level overview of the project's goals, features, and MVP requirements.
- [`docs/DEV_SPEC.md`](docs/DEV_SPEC.md): Technical specifications including API endpoints, database schema, and architecture decisions.
- [`docs/AGENTS.md`](docs/AGENTS.md): Directives and context for AI agents working on the codebase.
- [`docs/PROMPT_PLAN.md`](docs/PROMPT_PLAN.md): Strategic planning for AI-assisted development and prompting strategies.

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
