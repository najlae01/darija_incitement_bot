# Moderation API wrapper. Uses OpenAI Moderation as Tier A.
from typing import Dict
import os, requests

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
        categories = dict(getattr(out, "categories", {}) or {})
        scores = dict(getattr(out, "category_scores", {}) or {})

        violence = float(scores.get("violence", 0.0) or 0.0)
        harass_threat = float(scores.get("harassment/threatening", 0.0) or 0.0)
        illicit_violent = float(scores.get("illicit/violent", 0.0) or 0.0)  # omni-only

        # combine with a conservative max (or weighted)
        violence_score = max(violence, harass_threat, illicit_violent)
        return {"violence_score": violence_score, "categories": categories}

    except Exception:
        return {"violence_score": 0.0, "categories": {"violence": False}}

TIERB_URL   = os.getenv("TIERB_URL", "").strip()
TIERB_TOKEN = os.getenv("TIERB_TOKEN", "").strip()

def tierb_inference(text: str, context: str = ""):
    """
    Call your custom classifier (e.g., HF endpoint).
    Expected JSON: { "incitement_score": 0..1 } or { "score": 0..1 }
    Returns dict or None on failure.
    """
    if not TIERB_URL:
        return None
    try:
        headers = {"Authorization": f"Bearer {TIERB_TOKEN}"} if TIERB_TOKEN else {}
        payload = {"inputs": {"text": text, "context": context}}
        r = requests.post(TIERB_URL, json=payload, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json() if r.content else {}
        score = float(data.get("incitement_score", data.get("score", 0.0)) or 0.0)
        return {"incitement_score": max(0.0, min(1.0, score))}
    except Exception:
        return None