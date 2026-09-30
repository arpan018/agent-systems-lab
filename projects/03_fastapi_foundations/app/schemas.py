# Stage 3 HTTP models. Request and response shapes stay out of the route bodies.
# EchoRequest rejects blank and oversized text before service.py runs.

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str


class EchoRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)

    # FastAPI already checks length. This blocks whitespace-only strings.
    @field_validator("text")
    @classmethod
    def text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain non-whitespace characters")
        return value


class EchoResponse(BaseModel):
    text: str
    character_count: int
