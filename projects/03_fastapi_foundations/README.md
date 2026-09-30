# Stage 3 — FastAPI Foundations

Tiny local JSON API. No OpenAI. Learn routes, Pydantic bodies, and TestClient.

## Setup

```bash
uv sync
```

## Run

From the repo root:

```bash
uv run uvicorn app.main:app --app-dir projects/03_fastapi_foundations --reload
```

Open http://127.0.0.1:8000/docs

## Success

```bash
curl http://127.0.0.1:8000/health
```

```text
{"status":"ok"}
```

```bash
curl -X POST http://127.0.0.1:8000/echo -H "Content-Type: application/json" -d "{\"text\": \"  hello   world  \"}"
```

```text
{"text":"hello world","character_count":11}
```

## Failure

POST `/echo` with `{}` or `{"text": "   "}` returns HTTP 422. The generated docs show the same validation error.

## Tests

```bash
uv run pytest projects/03_fastapi_foundations
uv run ruff check projects/03_fastapi_foundations
```

Tests use FastAPI's TestClient. They do not start uvicorn and they do not call OpenAI.

## Utility ledger

```text
Utility: projects/03_fastapi_foundations/app/service.py
Added or changed: Stage 3
Why it exists: Keeps string normalization out of the route so tests can call it directly.
What it does not do: It does not call OpenAI, read .env, or talk to a database.
Tests: Echo route plus echo_text on the same input.
Shared yet: No.
```

## Intended for

A local JSON API with `GET /health` and `POST /echo`. This project does not call OpenAI.
