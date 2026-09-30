# Command line for one question.
# Loads settings, sends the question, prints the answer and token counts.
# AssistantError is one stderr line and exit code 1.
# With no question argument, the program asks once on stdin.

import argparse
import logging
import sys

from assistant import (
    create_client,
    get_profile,
    load_runtime_settings,
    send_prompt,
)
from usage import AssistantError, default_ledger_path

logger = logging.getLogger("llm_cli_assistant")


# Optional question, and an optional profile name that overrides AI_PROFILE.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ask one question and print the model reply plus token usage.",
    )
    parser.add_argument(
        "question",
        nargs="?",
        help="Question text. If omitted, the CLI prompts once on stdin.",
    )
    parser.add_argument(
        "--profile",
        help="Profile name. Defaults to AI_PROFILE or fast_chat.",
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


# Use the argument, or read one line from the terminal.
def resolve_question(question: str | None) -> str:
    if question is not None:
        return question
    try:
        return input("Question: ")
    except EOFError:
        raise AssistantError(
            "No question was provided. Pass one as an argument or type one at the prompt."
        ) from None


# Run one call. Exit 0 after printing usage, or 1 after an AssistantError.
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_runtime_settings()
        configure_logging()
        profile_name = args.profile if args.profile is not None else settings.profile_name
        profile = get_profile(profile_name)
        reply = send_prompt(
            create_client(settings),
            profile,
            resolve_question(args.question),
            usage_path=default_ledger_path(),
        )
    except AssistantError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    usage = reply.usage
    print(reply.text)
    print()
    print(f"profile: {usage.profile}")
    print(f"model: {usage.model}")
    print(f"response_id: {usage.response_id}")
    print(f"input_tokens: {usage.input_tokens}")
    print(f"output_tokens: {usage.output_tokens}")
    print(f"total_tokens: {usage.total_tokens}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
