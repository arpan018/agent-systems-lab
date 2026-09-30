# Stage 1 tests. No network calls.
# The request dict, the missing key, and the daily totals are the checks that matter.
# A fake client covers the success path and one HTTP failure.

from datetime import UTC, date, datetime
from types import SimpleNamespace

import httpx2
import pytest
from openai import APIStatusError

import main
from assistant import FAST_CHAT, LLMProfile, build_request, get_profile, load_settings, send_prompt
from usage import (
    AssistantError,
    append_usage,
    format_report,
    load_rows,
    parse_utc_date,
    record_from_response,
    summarize,
)


# fast_chat sends model, instructions, input, low reasoning, and low verbosity.
def test_fast_chat_request_shape() -> None:
    request = build_request(FAST_CHAT, "  What is a token?  ")
    assert request == {
        "model": "gpt-5.4-mini",
        "instructions": FAST_CHAT.instructions,
        "input": "What is a token?",
        "reasoning": {"effort": "low"},
        "text": {"verbosity": "low"},
    }


# A profile with no optional controls sends only the three required fields.
def test_unset_controls_are_omitted() -> None:
    profile = LLMProfile(name="plain", model="gpt-5.4-mini", instructions="Be brief.")
    request = build_request(profile, "hello")
    assert set(request) == {"model", "instructions", "input"}


# Blank text fails before a client exists.
def test_empty_question_fails_locally() -> None:
    with pytest.raises(AssistantError, match="empty"):
        build_request(FAST_CHAT, "   ")


# No key in the mapping is a local error.
def test_missing_api_key() -> None:
    with pytest.raises(AssistantError, match="OPENAI_API_KEY is missing"):
        load_settings({})


# The default profile name is fast_chat when AI_PROFILE is unset.
def test_settings_default_profile() -> None:
    settings = load_settings({"OPENAI_API_KEY": "sk-test"})
    assert settings.api_key == "sk-test"
    assert settings.profile_name == "fast_chat"
    assert get_profile("fast_chat") is FAST_CHAT


# An unknown profile names the one profile this stage has.
def test_unknown_profile() -> None:
    with pytest.raises(AssistantError, match="fast_chat"):
        get_profile("missing")


# The ledger row has token counts and no question text.
def test_usage_row_has_no_question() -> None:
    response = SimpleNamespace(
        id="resp_123",
        usage=SimpleNamespace(input_tokens=3, output_tokens=4, total_tokens=7),
    )
    record = record_from_response(
        response,
        model="gpt-5.4-mini",
        profile="fast_chat",
        now=datetime(2026, 9, 30, 11, 43, tzinfo=UTC),
    )
    assert record.total_tokens == 7
    assert record.response_id == "resp_123"
    assert "input" not in record.__dict__


# Rows from another UTC day are left out. A bad line is counted.
def test_daily_report_groups_one_utc_day(tmp_path) -> None:
    ledger = tmp_path / "requests.jsonl"
    same_day = record_from_response(
        SimpleNamespace(
            id="a",
            usage=SimpleNamespace(input_tokens=30, output_tokens=34, total_tokens=64),
        ),
        model="gpt-5.4-mini",
        profile="fast_chat",
        now=datetime(2026, 9, 30, 11, 43, tzinfo=UTC),
    )
    other_day = record_from_response(
        SimpleNamespace(
            id="b",
            usage=SimpleNamespace(input_tokens=1, output_tokens=1, total_tokens=2),
        ),
        model="gpt-5.4-mini",
        profile="fast_chat",
        now=datetime(2026, 9, 29, 1, 0, tzinfo=UTC),
    )
    append_usage(ledger, same_day)
    append_usage(ledger, other_day)
    ledger.write_text(ledger.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")

    records, skipped = load_rows(ledger)
    summary = summarize(records, date(2026, 9, 30), skipped_lines=skipped)
    report = format_report(summary)
    assert summary.overall.requests == 1
    assert summary.overall.total_tokens == 64
    assert "fast_chat: requests=1" in report
    assert "Skipped malformed lines: 1" in report
    assert parse_utc_date("2026-09-30") == date(2026, 9, 30)


# A fake client writes the ledger and does not store the question.
def test_send_prompt_writes_usage_without_the_question(tmp_path) -> None:
    seen: dict[str, object] = {}

    # Record the request kwargs and return a fixed answer with token counts.
    def create(**kwargs: object) -> object:
        seen.update(kwargs)
        return SimpleNamespace(
            id="resp_ok",
            output_text="A token is a piece of text.",
            usage=SimpleNamespace(input_tokens=30, output_tokens=34, total_tokens=64),
        )

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    ledger = tmp_path / "requests.jsonl"
    reply = send_prompt(client, FAST_CHAT, "What is a token?", usage_path=ledger)
    assert reply.text == "A token is a piece of text."
    assert seen["model"] == "gpt-5.4-mini"
    assert "temperature" not in seen
    assert "What is a token?" not in ledger.read_text(encoding="utf-8")


# HTTP failures stay one sentence and do not append a usage row.
def test_api_error_is_a_short_message(tmp_path) -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(500, request=request)

    # Raise the same status error the SDK raises for HTTP 500.
    def create(**kwargs: object) -> object:
        raise APIStatusError("upstream failed", response=response, body=None)

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    with pytest.raises(AssistantError, match="HTTP 500"):
        send_prompt(client, FAST_CHAT, "hello", usage_path=tmp_path / "requests.jsonl")
    assert not (tmp_path / "requests.jsonl").exists()


# The CLI prints the missing-key error and does not print an answer.
def test_main_missing_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Stand-in for load_runtime_settings when the key is absent.
    def missing() -> None:
        raise AssistantError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and set the key."
        )

    monkeypatch.setattr(main, "load_runtime_settings", missing)
    assert main.main(["hello"]) == 1
    captured = capsys.readouterr()
    assert "OPENAI_API_KEY is missing" in captured.err
    assert captured.out == ""
