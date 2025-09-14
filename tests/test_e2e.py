import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_backend_and_frontend_together():
    # 1. Call backend
    res = requests.post(f"{BASE_URL}/ask-gemini", json={"prompt": "Hello E2E"})
    assert res.status_code == 200
    data = res.json()
    assert "response" in data

    # 2. Save response locally (simulating frontend use)
    response_text = data["response"]
    assert isinstance(response_text, str)
