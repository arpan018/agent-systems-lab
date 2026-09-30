# Stage 2 tests. No network calls.
# Schema validation and profile selection are the checks this stage claims.

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from extractor import (
    STRUCTURED_EXTRACTION_V1,
    ExtractorError,
    build_request,
    extract_tasks,
    get_profile,
    load_samples,
    load_settings,
    validate_extraction,
)
from schemas import MeetingTasks, Priority


# A complete payload becomes MeetingTasks with the enum preserved.
def test_valid_payload_validates() -> None:
    data = validate_extraction(
        {
            "meeting_title": "Standup",
            "tasks": [
                {
                    "title": "Send the Stage 2 patch",
                    "owner": "Arpan",
                    "due": "today",
                    "priority": "high",
                }
            ],
        }
    )
    assert data.meeting_title == "Standup"
    assert data.tasks[0].owner == "Arpan"
    assert data.tasks[0].priority is Priority.high


# Optional fields may be omitted. An empty task list is valid.
def test_optional_fields_and_empty_tasks() -> None:
    data = validate_extraction({"tasks": []})
    assert data.meeting_title is None
    assert data.tasks == []
    data = validate_extraction({"tasks": [{"title": "Ping legal"}]})
    assert data.tasks[0].owner is None
    assert data.tasks[0].due is None
    assert data.tasks[0].priority is Priority.medium


# Bad enums, missing titles, and non-lists fail locally.
def test_invalid_payload_fails() -> None:
    with pytest.raises(ExtractorError, match="local validation"):
        validate_extraction({"tasks": [{"title": "x", "priority": "urgent"}]})
    with pytest.raises(ExtractorError, match="local validation"):
        validate_extraction({"tasks": [{}]})
    with pytest.raises(ValidationError):
        MeetingTasks.model_validate({"tasks": "not-a-list"})


# This stage has one named profile, bound to MeetingTasks.
def test_profile_selection() -> None:
    profile = get_profile("structured_extraction_v1")
    assert profile is STRUCTURED_EXTRACTION_V1
    assert profile.output_schema is MeetingTasks
    with pytest.raises(ExtractorError, match="structured_extraction_v1"):
        get_profile("fast_chat")
    with pytest.raises(ExtractorError, match="Known profiles"):
        get_profile("missing")


# The parse request sends the schema type and omits unset controls.
def test_request_uses_schema_not_freeform_json() -> None:
    request = build_request(STRUCTURED_EXTRACTION_V1, "  Arpan will send the patch.  ")
    assert request["model"] == "gpt-5.4-mini"
    assert request["input"] == "Arpan will send the patch."
    assert request["text_format"] is MeetingTasks
    assert request["reasoning"] == {"effort": "low"}
    assert "temperature" not in request
    with pytest.raises(ExtractorError, match="empty"):
        build_request(STRUCTURED_EXTRACTION_V1, "   ")


# Missing key fails before a client exists. Stage 2 does not read AI_PROFILE.
def test_missing_api_key() -> None:
    with pytest.raises(ExtractorError, match="OPENAI_API_KEY is missing"):
        load_settings({})
    settings = load_settings({"OPENAI_API_KEY": "sk-test", "AI_PROFILE": "fast_chat"})
    assert settings.api_key == "sk-test"


# The sample file has eight meeting-note blocks.
def test_sample_file_has_eight_inputs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "sample_inputs.txt"
    samples = load_samples(path)
    assert len(samples) == 8
    ids = [sample_id for sample_id, _ in samples]
    assert "empty-actions" in ids
    assert all(notes for _, notes in samples)


# A fake parse result is validated and the ledger stores the schema name, not the notes.
def test_extract_validates_and_records_schema(tmp_path: Path) -> None:
    parsed = MeetingTasks.model_validate(
        {"meeting_title": "Standup", "tasks": [{"title": "Send the patch", "owner": "Arpan"}]}
    )
    seen: dict[str, object] = {}

    # Record parse kwargs and return a structured object with token counts.
    def parse(**kwargs: object) -> object:
        seen.update(kwargs)
        return SimpleNamespace(
            id="resp_extract",
            output_parsed=parsed,
            usage=SimpleNamespace(input_tokens=40, output_tokens=20, total_tokens=60),
        )

    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    ledger = tmp_path / "requests.jsonl"
    notes = "Arpan will send the Stage 2 patch today."
    result = extract_tasks(client, STRUCTURED_EXTRACTION_V1, notes, usage_path=ledger)
    assert result.tasks[0].title == "Send the patch"
    assert seen["text_format"] is MeetingTasks
    row = ledger.read_text(encoding="utf-8")
    assert "MeetingTasks" in row
    assert "structured_extraction_v1" in row
    assert notes not in row
