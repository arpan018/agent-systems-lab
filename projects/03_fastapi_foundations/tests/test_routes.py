# Stage 3 tests. TestClient talks to the app in-process; there is no live server.
# Health, a valid echo, and invalid bodies are the three cases this stage claims.

from fastapi.testclient import TestClient

from app.main import app
from app.service import echo_text

client = TestClient(app)


# Health is a fixed status object.
def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Valid text is trimmed and counted by the service, then returned by the route.
def test_echo_valid() -> None:
    response = client.post("/echo", json={"text": "  hello   world  "})
    assert response.status_code == 200
    assert response.json() == {"text": "hello world", "character_count": 11}
    assert echo_text("  hello   world  ").character_count == 11


# Missing, blank, and oversized text are 422 from request validation.
def test_echo_invalid() -> None:
    missing = client.post("/echo", json={})
    assert missing.status_code == 422
    blank = client.post("/echo", json={"text": "   "})
    assert blank.status_code == 422
    too_long = client.post("/echo", json={"text": "x" * 501})
    assert too_long.status_code == 422
