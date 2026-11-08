import pytest

from apps.qa import services

pytestmark = pytest.mark.django_db

QUESTION = "How many days per week can I work from home once probation is over?"


def test_answer_comes_with_cited_sources(indexed, client_for):
    response = client_for(indexed).post("/api/ask/", {"question": QUESTION}, format="json")

    assert response.status_code == 200
    body = response.data
    assert body["mode"] == "extractive"
    assert "three days per week" in body["answer"]
    top = body["sources"][0]
    assert (top["document_title"], top["page"]) == ("nordlicht_handbook", 1)
    assert set(top) == {"document_id", "document_title", "page", "score", "text"}
    assert len(body["sources"]) <= 5


def test_top_k_is_respected(indexed, client_for):
    response = client_for(indexed).post(
        "/api/ask/", {"question": QUESTION, "top_k": 2}, format="json"
    )
    assert len(response.data["sources"]) == 2


def test_no_documents_means_no_answer(user, client_for):
    response = client_for(user).post("/api/ask/", {"question": QUESTION}, format="json")
    assert response.status_code == 200
    assert response.data["answer"] is None
    assert response.data["mode"] == "no_results"
    assert response.data["sources"] == []


def test_questions_only_search_your_own_documents(indexed, other_user, client_for):
    response = client_for(other_user).post("/api/ask/", {"question": QUESTION}, format="json")
    assert response.data["sources"] == []


@pytest.mark.parametrize(
    "payload",
    [{}, {"question": ""}, {"question": "x" * 1001}, {"question": "ok", "top_k": 0}, {"question": "ok", "top_k": 11}],
)
def test_invalid_requests_are_rejected(user, client_for, payload):
    assert client_for(user).post("/api/ask/", payload, format="json").status_code == 400


def test_llm_mode_is_used_when_enabled(indexed, client_for, settings, monkeypatch):
    settings.ANSWER_BACKEND = "anthropic"
    seen = {}

    def fake_llm(question, hits):
        seen["question"], seen["hits"] = question, hits
        return "Three days per week [1]."

    monkeypatch.setattr(services, "_generate_with_llm", fake_llm)
    response = client_for(indexed).post("/api/ask/", {"question": QUESTION}, format="json")

    assert response.data["mode"] == "llm"
    assert response.data["answer"] == "Three days per week [1]."
    assert seen["question"] == QUESTION and seen["hits"]


def test_llm_failure_falls_back_to_extractive(indexed, client_for, settings, monkeypatch):
    settings.ANSWER_BACKEND = "anthropic"

    def broken(question, hits):
        raise TimeoutError("API unreachable")

    monkeypatch.setattr(services, "_generate_with_llm", broken)
    response = client_for(indexed).post("/api/ask/", {"question": QUESTION}, format="json")

    assert response.status_code == 200
    assert response.data["mode"] == "extractive"
    assert "three days per week" in response.data["answer"]


def test_ask_is_rate_limited(indexed, client_for, monkeypatch):
    from rest_framework.throttling import ScopedRateThrottle

    # DRF reads the rates once at import time, so patch the dict it holds.
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "ask", "2/min")

    client = client_for(indexed)
    codes = [
        client.post("/api/ask/", {"question": QUESTION}, format="json").status_code
        for _ in range(3)
    ]
    assert codes == [200, 200, 429]
