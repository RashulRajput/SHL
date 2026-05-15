from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_contract() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_schema_for_vague_query() -> None:
    response = client.post("/chat", json={"messages": [{"role": "user", "content": "I need an assessment"}]})
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"reply", "recommendations", "end_of_conversation"}
    assert isinstance(payload["reply"], str)
    assert payload["recommendations"] == []
    assert payload["end_of_conversation"] is False


def test_validation_rejects_extra_fields() -> None:
    response = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Hiring Java developer"}], "session_id": "nope"},
    )
    assert response.status_code == 422

