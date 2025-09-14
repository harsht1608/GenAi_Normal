import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import backend.main as main
from backend.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_ask_gemini(monkeypatch):
    def fake_call_gemini(prompt, model_name=None):
        return "Mock response"
    monkeypatch.setattr("backend.main.call_gemini", fake_call_gemini)

    res = client.post("/ask-gemini", json={"prompt": "Hello Gemini"})
    assert res.status_code == 200
    data = res.json()
    assert data["response"] == "Mock response"
    assert "model" in data

def test_devops_endpoints(monkeypatch):
    monkeypatch.setattr("backend.main.call_gemini", lambda prompt, model_name=None: "AI Suggestion")

    endpoints = ["analyze-logs", "optimize-docker", "fix-ci"]
    for ep in endpoints:
        res = client.post(f"/{ep}", json={"content": "dummy"})
        assert res.status_code == 200
        data = res.json()
        assert "AI Suggestion" in data["suggestions"]
