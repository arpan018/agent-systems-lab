# Stage 2 extractor: one profile, one schema, one Responses parse call.
# The profile names the schema; the request builder sends text_format, not a prompt JSON blob.
# Parsed output is validated again locally so bad objects fail before they are printed.
# Usage rows add the schema name. Notes and the API key are not logged.

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI
from pydantic import ValidationError

from schemas import MeetingTasks

logger = logging.getLogger("structured_data_extractor")

DEFAULT_PROFILE_NAME = "structured_extraction_v1"


class ExtractorError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str


@dataclass(frozen=True)
class ExtractionProfile:
    name: str
    model: str
    instructions: str
    output_schema: type[MeetingTasks]
    reasoning_effort: str | None = None


EXTRACTION_INSTRUCTIONS_V1: Final[str] = (
    "Extract action items from the meeting notes. "
    "Fill only fields supported by the schema. "
    "If a person, date, or task is not in the notes, leave that field null or omit the task. "
    "If there are no action items, return an empty tasks list. "
    "Use priority high only when the notes mark urgency."
)

STRUCTURED_EXTRACTION_V1: Final[ExtractionProfile] = ExtractionProfile(
    name="structured_extraction_v1",
    model="gpt-5.4-mini",
    instructions=EXTRACTION_INSTRUCTIONS_V1,
    output_schema=MeetingTasks,
    reasoning_effort="low",
)

PROFILES: Final[dict[str, ExtractionProfile]] = {
    STRUCTURED_EXTRACTION_V1.name: STRUCTURED_EXTRACTION_V1,
}


# Walk up to pyproject.toml so .env and the ledger resolve from any working directory.
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise ExtractorError("Could not find the repo root (pyproject.toml).")


# Read the key only. This CLI always defaults to structured_extraction_v1.
def load_settings(environ: Mapping[str, str]) -> Settings:
    api_key = environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ExtractorError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and set the key."
        )
    return Settings(api_key=api_key)


# Load the repo-root .env, then read the process environment.
def load_runtime_settings() -> Settings:
    load_dotenv(repo_root() / ".env")
    return load_settings(os.environ)


# Look up the extraction profile. Unknown names list this stage's one profile.
def get_profile(name: str) -> ExtractionProfile:
    try:
        return PROFILES[name]
    except KeyError:
        known = ", ".join(sorted(PROFILES))
        raise ExtractorError(f"Unknown profile {name!r}. Known profiles: {known}.") from None


# Split examples/sample_inputs.txt on ### headings into (id, notes) pairs.
def load_samples(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        raise ExtractorError(f"Sample file not found: {path}")
    samples: list[tuple[str, str]] = []
    current_id: str | None = None
    chunks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            if current_id is not None:
                samples.append((current_id, "\n".join(chunks).strip()))
            current_id = line[4:].strip()
            chunks = []
        else:
            chunks.append(line)
    if current_id is not None:
        samples.append((current_id, "\n".join(chunks).strip()))
    if not samples:
        raise ExtractorError(f"No samples found in {path}. Use ### headings.")
    return samples


# Copy fields the parse call needs. The schema type is text_format, not a dumped JSON schema.
def build_request(profile: ExtractionProfile, notes: str) -> dict[str, Any]:
    text = notes.strip()
    if not text:
        raise ExtractorError("Notes are empty. Pass meeting notes or use --batch.")
    request: dict[str, Any] = {
        "model": profile.model,
        "instructions": profile.instructions,
        "input": text,
        "text_format": profile.output_schema,
    }
    if profile.reasoning_effort is not None:
        request["reasoning"] = {"effort": profile.reasoning_effort}
    return request


# Re-parse a dict or model so invalid local data fails here, not in the caller.
def validate_extraction(payload: object) -> MeetingTasks:
    try:
        if isinstance(payload, MeetingTasks):
            return MeetingTasks.model_validate(payload.model_dump())
        return MeetingTasks.model_validate(payload)
    except ValidationError as exc:
        count = exc.error_count()
        raise ExtractorError(f"Extraction failed local validation: {count} error(s).") from exc


# Create the SDK client. The key is an argument here and is never logged.
def create_client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=settings.api_key)


# Parse notes into MeetingTasks, validate locally, then append usage with the schema name.
def extract_tasks(
    client: OpenAI,
    profile: ExtractionProfile,
    notes: str,
    *,
    usage_path: Path,
) -> MeetingTasks:
    request = build_request(profile, notes)
    logger.info(
        "request profile=%s model=%s schema=%s reasoning_effort=%s",
        profile.name,
        profile.model,
        profile.output_schema.__name__,
        profile.reasoning_effort,
    )
    try:
        response = client.responses.parse(**request)
    except AuthenticationError:
        raise ExtractorError("OpenAI rejected the API key. Check OPENAI_API_KEY in .env.") from None
    except APIStatusError as exc:
        raise ExtractorError(f"OpenAI request failed (HTTP {exc.status_code}).") from None
    except APIConnectionError:
        raise ExtractorError(
            "Could not reach the OpenAI API. Check your network and try again."
        ) from None

    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise ExtractorError("The model returned no structured output.")
    result = validate_extraction(parsed)
    _append_usage(usage_path, response, profile)
    return result


# Repo-root ledger shared with Stage 1. Extra schema field is ignored by that report.
def default_ledger_path() -> Path:
    return repo_root() / "data" / "usage" / "requests.jsonl"


# One JSONL row: Stage 1 fields plus schema so the extraction profile is visible later.
def _append_usage(path: Path, response: object, profile: ExtractionProfile) -> None:
    usage = getattr(response, "usage", None)
    row = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "model": profile.model,
        "profile": profile.name,
        "schema": profile.output_schema.__name__,
        "input_tokens": _token_count(usage, "input_tokens"),
        "output_tokens": _token_count(usage, "output_tokens"),
        "total_tokens": _token_count(usage, "total_tokens"),
        "response_id": str(getattr(response, "id", "") or ""),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=True) + "\n")


# One token field. Missing usage counts as zero.
def _token_count(usage: object, name: str) -> int:
    if usage is None:
        return 0
    value = getattr(usage, name, 0)
    return 0 if value is None else int(value)
