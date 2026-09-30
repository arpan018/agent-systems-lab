# Deterministic echo logic. Routes call this; they do not normalize strings themselves.
# Collapse whitespace so "  hello   world " becomes a stable "hello world".

from app.schemas import EchoResponse


# Strip, squeeze internal spaces, and count characters of the result.
def echo_text(text: str) -> EchoResponse:
    normalized = " ".join(text.split())
    return EchoResponse(text=normalized, character_count=len(normalized))
