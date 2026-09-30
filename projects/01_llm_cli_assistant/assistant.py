# Stage 1 assistant: key, one profile, and one Responses API call.
# The API key comes from the environment. The profile holds model behavior only.
# build_request copies the fields this call needs and leaves unset controls out.
# API failures become AssistantError so the CLI prints one line.
# There is no conversation memory in this stage.

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI

from usage import AssistantError, UsageRecord, append_usage, record_from_response

logger = logging.getLogger("llm_cli_assistant")

DEFAULT_PROFILE_NAME = "fast_chat"


# Key and default profile name. Model behavior lives on LLMProfile, not here.
@dataclass(frozen=True)
class Settings:
    api_key: str
    profile_name: str


# Model, instructions, and the optional controls fast_chat actually sets.
@dataclass(frozen=True)
class LLMProfile:
    name: str
    model: str
    instructions: str
    reasoning_effort: str | None = None
    verbosity: str | None = None


# Answer text plus the usage row written for this call.
@dataclass(frozen=True)
class AssistantReply:
    text: str
    usage: UsageRecord


FAST_CHAT_INSTRUCTIONS: Final[str] = "Be helpful and concise. Answer the user's question directly."

FAST_CHAT: Final[LLMProfile] = LLMProfile(
    name="fast_chat",
    model="gpt-5.4-mini",
    instructions=FAST_CHAT_INSTRUCTIONS,
    reasoning_effort="low",
    verbosity="low",
)

# The only profile in this stage. Callers pass the object; nothing global is switched.
PROFILES: Final[dict[str, LLMProfile]] = {FAST_CHAT.name: FAST_CHAT}


# Walk up to pyproject.toml so .env and the ledger resolve from any working directory.
def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
    raise AssistantError("Could not find the repo root (pyproject.toml).")


# Read the key and optional AI_PROFILE. A missing key fails before any network call.
def load_settings(environ: Mapping[str, str]) -> Settings:
    api_key = environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise AssistantError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and set the key."
        )
    profile_name = environ.get("AI_PROFILE", DEFAULT_PROFILE_NAME).strip() or DEFAULT_PROFILE_NAME
    return Settings(api_key=api_key, profile_name=profile_name)


# Load the repo-root .env, then read the process environment.
def load_runtime_settings() -> Settings:
    load_dotenv(repo_root() / ".env")
    return load_settings(os.environ)


# Look up a profile by name. Unknown names list what this stage actually has.
def get_profile(name: str) -> LLMProfile:
    try:
        return PROFILES[name]
    except KeyError:
        known = ", ".join(sorted(PROFILES))
        raise AssistantError(f"Unknown profile {name!r}. Known profiles: {known}.") from None


# Build Responses API kwargs. Unset reasoning or verbosity is omitted, not sent as null.
def build_request(profile: LLMProfile, user_input: str) -> dict[str, Any]:
    question = user_input.strip()
    if not question:
        raise AssistantError(
            "Question is empty. Pass a question argument or type one at the prompt."
        )
    request: dict[str, Any] = {
        "model": profile.model,
        "instructions": profile.instructions,
        "input": question,
    }
    if profile.reasoning_effort is not None:
        request["reasoning"] = {"effort": profile.reasoning_effort}
    if profile.verbosity is not None:
        request["text"] = {"verbosity": profile.verbosity}
    return request


# Create the SDK client. The key is an argument here and is never logged.
def create_client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=settings.api_key)


# Send one question, require text back, then append token counts.
def send_prompt(
    client: OpenAI,
    profile: LLMProfile,
    user_input: str,
    *,
    usage_path: Path,
) -> AssistantReply:
    request = build_request(profile, user_input)
    logger.info(
        "request profile=%s model=%s reasoning_effort=%s verbosity=%s",
        profile.name,
        profile.model,
        profile.reasoning_effort,
        profile.verbosity,
    )
    try:
        response = client.responses.create(**request)
    except AuthenticationError:
        raise AssistantError("OpenAI rejected the API key. Check OPENAI_API_KEY in .env.") from None
    except APIStatusError as exc:
        raise AssistantError(f"OpenAI request failed (HTTP {exc.status_code}).") from None
    except APIConnectionError:
        raise AssistantError(
            "Could not reach the OpenAI API. Check your network and try again."
        ) from None

    text = getattr(response, "output_text", None)
    if not isinstance(text, str) or not text.strip():
        raise AssistantError("The model returned no text output.")

    usage = record_from_response(response, model=profile.model, profile=profile.name)
    append_usage(usage_path, usage)
    return AssistantReply(text=text, usage=usage)
