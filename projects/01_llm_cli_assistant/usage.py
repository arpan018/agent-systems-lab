# Token ledger for Stage 1. One JSON object per successful API call.
# Rows store time, model, profile, token counts, and response id.
# The question and the API key are not fields, so they cannot be written.
# The report groups one UTC date by model and by profile.
# A missing ledger file is an empty day.

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any


# Shared by the CLI and the report so both can fail with one readable line.
class AssistantError(Exception):
    pass


# One ledger row. There is no field for the question.
@dataclass(frozen=True)
class UsageRecord:
    timestamp_utc: str
    model: str
    profile: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    response_id: str


# Sum of requests and tokens for a day, a model, or a profile.
@dataclass(frozen=True)
class TokenTotals:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # New totals that include this row. The previous totals stay unchanged.
    def add(self, record: UsageRecord) -> "TokenTotals":
        return TokenTotals(
            requests=self.requests + 1,
            input_tokens=self.input_tokens + record.input_tokens,
            output_tokens=self.output_tokens + record.output_tokens,
            total_tokens=self.total_tokens + record.total_tokens,
        )


# One UTC day: overall totals, plus the same rows split by model and profile.
@dataclass(frozen=True)
class DailySummary:
    day: date
    overall: TokenTotals
    by_model: dict[str, TokenTotals]
    by_profile: dict[str, TokenTotals]
    skipped_lines: int


# Repo-root ledger shared by the CLI and the report script.
def default_ledger_path() -> Path:
    from assistant import repo_root

    return repo_root() / "data" / "usage" / "requests.jsonl"


# Copy token counts off a response. The question is not an argument.
def record_from_response(
    response: object,
    *,
    model: str,
    profile: str,
    now: datetime | None = None,
) -> UsageRecord:
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        raise AssistantError("Usage timestamps must be timezone-aware UTC.")
    usage = getattr(response, "usage", None)
    return UsageRecord(
        timestamp_utc=moment.astimezone(UTC).isoformat(),
        model=model,
        profile=profile,
        input_tokens=_token_count(usage, "input_tokens"),
        output_tokens=_token_count(usage, "output_tokens"),
        total_tokens=_token_count(usage, "total_tokens"),
        response_id=str(getattr(response, "id", "") or ""),
    )


# Append one JSON line, creating data/usage when it is missing.
def append_usage(path: Path, record: UsageRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(record), ensure_ascii=True) + "\n")


# Parsed rows and how many lines were skipped. A missing file returns nothing.
def load_rows(path: Path) -> tuple[list[UsageRecord], int]:
    if not path.is_file():
        return [], 0
    records: list[UsageRecord] = []
    skipped = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(_record_from_json(line))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            skipped += 1
    return records, skipped


# Keep rows from this UTC day and total them by model and profile.
def summarize(records: list[UsageRecord], day: date, *, skipped_lines: int = 0) -> DailySummary:
    selected = [record for record in records if _record_day(record) == day]
    by_model: dict[str, TokenTotals] = defaultdict(TokenTotals)
    by_profile: dict[str, TokenTotals] = defaultdict(TokenTotals)
    overall = TokenTotals()
    for record in selected:
        overall = overall.add(record)
        by_model[record.model] = by_model[record.model].add(record)
        by_profile[record.profile] = by_profile[record.profile].add(record)
    return DailySummary(
        day=day,
        overall=overall,
        by_model=dict(by_model),
        by_profile=dict(by_profile),
        skipped_lines=skipped_lines,
    )


# Plain-text report. Mentions skipped lines only when a row could not be read.
def format_report(summary: DailySummary) -> str:
    lines = [
        f"Date (UTC): {summary.day.isoformat()}",
        f"Requests: {summary.overall.requests}",
        f"Input tokens: {summary.overall.input_tokens}",
        f"Output tokens: {summary.overall.output_tokens}",
        f"Total tokens: {summary.overall.total_tokens}",
        "",
        "By model:",
        *_format_groups(summary.by_model),
        "",
        "By profile:",
        *_format_groups(summary.by_profile),
    ]
    if summary.skipped_lines:
        lines.extend(["", f"Skipped malformed lines: {summary.skipped_lines}"])
    return "\n".join(lines)


# YYYY-MM-DD only. Anything else is a local error.
def parse_utc_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise AssistantError(f"Date {value!r} must be YYYY-MM-DD.") from exc


# One token field. Missing usage counts as zero.
def _token_count(usage: object, name: str) -> int:
    if usage is None:
        return 0
    value = getattr(usage, name, 0)
    return 0 if value is None else int(value)


# One JSONL object. The caller skips the line when this raises.
def _record_from_json(line: str) -> UsageRecord:
    payload: dict[str, Any] = json.loads(line)
    return UsageRecord(
        timestamp_utc=str(payload["timestamp_utc"]),
        model=str(payload["model"]),
        profile=str(payload["profile"]),
        input_tokens=int(payload["input_tokens"]),
        output_tokens=int(payload["output_tokens"]),
        total_tokens=int(payload["total_tokens"]),
        response_id=str(payload.get("response_id", "")),
    )


# UTC calendar date of a stored timestamp.
def _record_day(record: UsageRecord) -> date:
    parsed = datetime.fromisoformat(record.timestamp_utc.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).date()


# Sorted lines for one grouping. Empty means this day had no calls.
def _format_groups(groups: dict[str, TokenTotals]) -> list[str]:
    if not groups:
        return ["  (none)"]
    lines: list[str] = []
    for name in sorted(groups):
        totals = groups[name]
        lines.append(
            f"  {name}: requests={totals.requests} input={totals.input_tokens} "
            f"output={totals.output_tokens} total={totals.total_tokens}"
        )
    return lines
