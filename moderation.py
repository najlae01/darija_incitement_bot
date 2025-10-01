# Moderation API wrapper. Uses OpenAI Moderation as Tier A.
from typing import Dict
import os

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

def openai_moderate(text: str) -> Dict:
    """
    Returns a dict with keys:
    - violence_score: float in [0, 1]
    - categories: dict of categories and booleans/scores
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or OpenAI is None:
        # Fallback: no API key → neutral
        return {"violence_score": 0.0, "categories": {"violence": False}}

    client = OpenAI(api_key=api_key)
    # Use the moderation endpoint; adjust model name if needed.
    try:
        resp = client.moderations.create(
            model="omni-moderation-latest",
            input=text[:20000]
        )
        # Map result to violence score; OpenAI returns category scores
        out = resp.results[0]
        categories = getattr(out, "categories", {}) or {}
        category_scores = getattr(out, "category_scores", {}) or {}
        violence_score = float(category_scores.get("violence", 0.0) or 0.0)
        return {"violence_score": violence_score, "categories": dict(categories)}
    except Exception:
        return {"violence_score": 0.0, "categories": {"violence": False}}
