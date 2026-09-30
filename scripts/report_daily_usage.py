# Print token totals from data/usage/requests.jsonl for one UTC date.
# Shows the day total, then the same rows grouped by model and by profile.
# This is the project ledger only. It does not measure Cursor usage.

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "projects" / "01_llm_cli_assistant"))

from usage import (  # noqa: E402
    AssistantError,
    default_ledger_path,
    format_report,
    load_rows,
    parse_utc_date,
    summarize,
)


# --date is required. --ledger overrides the default JSONL path.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report local OpenAI token usage for one UTC date."
    )
    parser.add_argument("--date", required=True, help="UTC calendar date, YYYY-MM-DD.")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=None,
        help="JSONL ledger path. Defaults to data/usage/requests.jsonl.",
    )
    return parser


# Load the ledger, keep that UTC day, and print the totals.
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        day = parse_utc_date(args.date)
        ledger = args.ledger if args.ledger is not None else default_ledger_path()
        records, skipped = load_rows(ledger)
        print(format_report(summarize(records, day, skipped_lines=skipped)))
    except AssistantError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
