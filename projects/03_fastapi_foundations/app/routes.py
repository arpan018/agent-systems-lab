# HTTP routes only. They parse requests, call service.py, and return response models.
# Health is a constant. Echo is the one path that has application logic.

from fastapi import APIRouter

from app.schemas import EchoRequest, EchoResponse, HealthResponse
from app.service import echo_text

router = APIRouter()


# Confirm the process is up. No dependencies, no OpenAI.
@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


# Normalize posted text and return the cleaned string plus its length.
@router.post("/echo", response_model=EchoResponse)
def echo(payload: EchoRequest) -> EchoResponse:
    return echo_text(payload.text)
