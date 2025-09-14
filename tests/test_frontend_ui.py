import pytest

def test_frontend_chatbot(page):
    page.goto("http://localhost:8501")
    assert "Gemini" in page.title()

    page.fill("textarea", "Hello from test")
    page.click("text=Ask Gemini")

    # Gemini response check
    assert page.is_visible("text=Response from Gemini:")


def test_frontend_devops(page):
    page.goto("http://localhost:8501")
    page.click("text=DevOps Helpers")

    page.select_option("select", label="Analyze Logs")
    page.fill("textarea", "error: test failure")
    page.click("text=Run Helper")

    # Suggestions check
    assert page.is_visible("text=Suggestions from Gemini")
