"""
The AI layer — a thin, reusable wrapper around Google Gemini.

Every part of InsightForge (text tools now; data insights, report writing later)
calls through this one module, so there's a single place that knows how to talk
to the model.
"""

import google.generativeai as genai

from app.config import settings


class AIError(RuntimeError):
    """Raised when the AI call can't be made or fails."""


def _model():
    if not settings.gemini_api_key:
        raise AIError("No GEMINI_API_KEY set. Copy .env.example to .env and add your key.")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(settings.gemini_model)


def generate(prompt: str) -> str:
    """Send one prompt, get the whole answer back as text."""
    try:
        resp = _model().generate_content(prompt)
        return (resp.text or "").strip()
    except AIError:
        raise
    except Exception as e:  # network, quota, bad key, etc.
        raise AIError(f"AI request failed: {e}") from e
