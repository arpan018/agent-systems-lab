# Stage 2 — Structured Data Extractor

Turn messy meeting notes into `MeetingTasks` JSON. The model must match that schema; local validation rejects anything else.

## Setup

From the repo root:

```bash
uv sync
copy .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. This CLI uses profile `structured_extraction_v1` (`gpt-5.4-mini` + `MeetingTasks`). It does not use `AI_PROFILE` from Stage 1.

## Run

One block of notes:

```bash
uv run python projects/02_structured_data_extractor/main.py "Standup. Arpan will send the Stage 2 patch today."
```

All eight samples:

```bash
uv run python projects/02_structured_data_extractor/main.py --batch
```

Stdout is JSON. Stderr is the log line: profile, model, schema, and reasoning. Token counts are appended to `data/usage/requests.jsonl` with the profile and schema name.

## Success

A valid extract prints JSON such as:

```json
{
  "meeting_title": "Standup",
  "tasks": [
    {
      "title": "Send the Stage 2 patch",
      "owner": "Arpan",
      "due": "today",
      "priority": "medium"
    }
  ]
}
```

`--batch` prints a JSON list of `{id, data}` objects, one per `###` heading in `examples/sample_inputs.txt`.

## Failure

Unknown profile (no network call):

```bash
uv run python projects/02_structured_data_extractor/main.py --profile fast_chat "hello"
```

```text
error: Unknown profile 'fast_chat'. Known profiles: structured_extraction_v1.
```

Empty notes fail locally with `error: Notes are empty...`. A missing key prints the same `.env` message as Stage 1. A model object that fails Pydantic becomes `error: Extraction failed local validation: ...`.

## Tests

```bash
uv run pytest projects/02_structured_data_extractor
uv run ruff check projects/02_structured_data_extractor
```

Tests cover schema validation and profile selection. They do not call OpenAI.

## Utility ledger

```text
Utility: projects/02_structured_data_extractor/extractor.py
Added or changed: Stage 2
Why it exists: Binds one named profile to MeetingTasks and builds a parse request.
What it does not do: It does not import Stage 1 modules, retry failed parses, or serve HTTP.
Tests: Profile lookup, request text_format, local ValidationError wrapping.
Shared yet: No. src/common/ was not created.
```

## Intended for

Turn messy meeting notes into validated `MeetingTasks` JSON. This project is a structured-extraction CLI, not a web server.
