# Command line for one extraction or a batch of sample notes.
# Prints schema JSON on stdout. Profile, model, and tokens go to stderr.
# ExtractorError is one stderr line and exit code 1.

import argparse
import json
import logging
import sys
from pathlib import Path

from extractor import (
    DEFAULT_PROFILE_NAME,
    ExtractorError,
    create_client,
    default_ledger_path,
    extract_tasks,
    get_profile,
    load_runtime_settings,
    load_samples,
)
from schemas import MeetingTasks

logger = logging.getLogger("structured_data_extractor")

SAMPLES_PATH = Path(__file__).resolve().parent / "examples" / "sample_inputs.txt"


# Notes text, optional --batch over the sample file, and an optional profile name.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract meeting tasks as JSON that matches the MeetingTasks schema.",
    )
    parser.add_argument(
        "notes",
        nargs="?",
        help="Meeting notes. If omitted without --batch, the CLI reads stdin.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Extract every sample in examples/sample_inputs.txt.",
    )
    parser.add_argument(
        "--samples",
        type=Path,
        default=SAMPLES_PATH,
        help="Sample file for --batch. Defaults to this project's examples/sample_inputs.txt.",
    )
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE_NAME,
        help="Profile name. Defaults to structured_extraction_v1.",
    )
    return parser


# Show the request line on stderr. Do this once so tests do not stack handlers.
def configure_logging() -> None:
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.propagate = False


# Use the argument, or read stdin, unless --batch was selected.
def resolve_notes(notes: str | None, *, batch: bool) -> str | None:
    if batch:
        return None
    if notes is not None:
        return notes
    try:
        return sys.stdin.read()
    except OSError:
        raise ExtractorError(
            "No notes were provided. Pass text, pipe stdin, or use --batch."
        ) from None


# Print one MeetingTasks object as indented JSON.
def print_extraction(data: MeetingTasks) -> None:
    print(data.model_dump_json(indent=2))


# Print batch results as a JSON list of {id, data} objects.
def print_batch(results: list[tuple[str, MeetingTasks]]) -> None:
    payload = [
        {"id": sample_id, "data": data.model_dump(mode="json")}
        for sample_id, data in results
    ]
    print(json.dumps(payload, indent=2, ensure_ascii=True))


# Run one extract or the sample batch. Exit 0 after JSON, or 1 after ExtractorError.
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_runtime_settings()
        configure_logging()
        profile = get_profile(args.profile)
        client = create_client(settings)
        usage_path = default_ledger_path()
        if args.batch:
            results: list[tuple[str, MeetingTasks]] = []
            for sample_id, notes in load_samples(args.samples):
                extracted = extract_tasks(client, profile, notes, usage_path=usage_path)
                results.append((sample_id, extracted))
            print_batch(results)
        else:
            notes = resolve_notes(args.notes, batch=False)
            if notes is None:
                raise ExtractorError(
                    "No notes were provided. Pass text, pipe stdin, or use --batch."
                )
            print_extraction(extract_tasks(client, profile, notes, usage_path=usage_path))
    except ExtractorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
