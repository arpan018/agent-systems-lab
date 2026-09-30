# Stage 1 — LLM CLI Assistant

One command sends a question to the OpenAI Responses API and prints the reply plus token counts.

## Setup

From the repo root:

```bash
uv sync
copy .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. `AI_PROFILE` defaults to `fast_chat` (`gpt-5.4-mini`).

## Run

```bash
uv run python projects/01_llm_cli_assistant/main.py "In one sentence, what is a token?"
```

Omit the question to be prompted once:

```bash
uv run python projects/01_llm_cli_assistant/main.py
```

Choose the profile explicitly (only `fast_chat` exists in this stage):

```bash
uv run python projects/01_llm_cli_assistant/main.py --profile fast_chat "Say hello in five words."
```

Each successful call appends a usage row to `data/usage/requests.jsonl` (gitignored). Summarize one UTC day:

```bash
uv run python scripts/report_daily_usage.py --date 2026-09-30
```

## Success

A live call prints the answer, then:

```text
profile: fast_chat
model: gpt-5.4-mini
response_id: resp_...
input_tokens: ...
output_tokens: ...
total_tokens: ...
```

The log line names the profile, model, and generation controls. It does not print the API key or the question.

## Failure

Missing key (no network call):

```bash
uv run python projects/01_llm_cli_assistant/main.py "hello"
```

```text
error: OPENAI_API_KEY is missing. Copy .env.example to .env and set the key.
```

Unknown profile:

```bash
uv run python projects/01_llm_cli_assistant/main.py --profile missing "hello"
```

```text
error: Unknown profile 'missing'. Known profiles: fast_chat.
```

A rejected key or HTTP error prints one line such as `error: OpenAI request failed (HTTP 401).` and does not dump a stack trace.

## Tests

```bash
uv run pytest
uv run ruff check projects/01_llm_cli_assistant scripts
```

Tests cover the request dict, the missing key, the ledger, and a fake client. They do not call OpenAI.

## Utility ledger

```text
Utility: projects/01_llm_cli_assistant/assistant.py
Added or changed: Stage 1
Why it exists: Holds the key check, the one profile, the request dict, and the API call together.
What it does not do: It does not store chat history, choose among many models, or write the ledger format.
Tests: Builds the fast_chat request, omits unset controls, rejects an empty question and a missing key.
Shared yet: No.
```

```text
Utility: projects/01_llm_cli_assistant/usage.py
Added or changed: Stage 1
Why it exists: Records per-response token counts for this project's API key.
What it does not do: It does not store prompts, estimate cost, or warn against a daily allowance.
Tests: Appends JSONL and totals one UTC day by model and profile.
Shared yet: No.
```

## Intended for

One command-line question, one model reply, and token counts. This project is a one-shot text CLI.
