"""
src/analyzer.py
Uses OpenAI GPT to score news articles across 5 IR theory frameworks
and generate a ~150-word theoretical analysis note.
Runs as a Streamlit helper OR as a standalone CLI script.
"""

import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import get_unanalyzed_articles, insert_analysis

logger = logging.getLogger(__name__)

# ── OpenAI client factory ─────────────────────────────────────────────────────
def _get_api_key() -> str:
    # 1. Environment variable (GitHub Actions / Docker)
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    # 2. Streamlit secrets (when running inside Streamlit)
    try:
        import streamlit as st
        key = st.secrets.get("OPENAI_API_KEY", "").strip()
        if key:
            return key
    except Exception:
        pass
    return ""


def get_openai_client():
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai paketi yüklü değil: pip install openai")

    api_key = _get_api_key()
    if not api_key:
        raise ValueError(
            "OpenAI API anahtarı bulunamadı.\n"
            "• .streamlit/secrets.toml → OPENAI_API_KEY = 'sk-…'\n"
            "• veya ortam değişkeni: export OPENAI_API_KEY='sk-…'"
        )
    return OpenAI(api_key=api_key)


# ── Prompt ────────────────────────────────────────────────────────────────────
_SYSTEM = (
    "You are a PhD-level expert in International Relations theory. "
    "Always respond with a single valid JSON object and nothing else — "
    "no markdown fences, no preamble, no trailing text."
)

_USER_TEMPLATE = """\
Analyze the following news item through 5 IR theoretical lenses.

Article Title : {title}
Source        : {source}
Summary       : {summary}

Return ONLY a JSON object with these exact keys:
{{
  "realism":         <integer 0-100>,
  "liberalism":      <integer 0-100>,
  "constructivism":  <integer 0-100>,
  "critical_theory": <integer 0-100>,
  "english_school":  <integer 0-100>,
  "analysis_note":   "<string, ~150 words, academic tone, covers which theory
                       best explains the event and why>"
}}

Scoring guide:
- Realism        : power politics, national interest, security dilemma, balance of power
- Liberalism     : international institutions, cooperation, democratic peace, trade
- Constructivism : identity, norms, social construction, discourse, ideas
- Critical Theory: structural power, hegemony, emancipation, hidden inequalities
- English School : international society, pluralism/solidarism, shared norms, order
"""


# ── Core analysis function ────────────────────────────────────────────────────
def analyze_article(client, article: dict) -> tuple[dict | None, str | None]:
    """
    Returns (scores_dict, analysis_note) or (None, None) on failure.
    scores_dict keys: realism, liberalism, constructivism, critical_theory, english_school
    """
    title   = (article.get("title") or "")[:300]
    summary = (article.get("summary") or "No summary available")[:600]
    source  = (article.get("source") or "Unknown")

    prompt = _USER_TEMPLATE.format(
        title=title, source=source, summary=summary
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.6,
            max_tokens=700,
            response_format={"type": "json_object"},
        )

        raw  = resp.choices[0].message.content.strip()
        data = json.loads(raw)

        scores = {
            "realism":         _clamp(data.get("realism", 0)),
            "liberalism":      _clamp(data.get("liberalism", 0)),
            "constructivism":  _clamp(data.get("constructivism", 0)),
            "critical_theory": _clamp(data.get("critical_theory", 0)),
            "english_school":  _clamp(data.get("english_school", 0)),
        }
        note = str(data.get("analysis_note", "")).strip()
        return scores, note

    except json.JSONDecodeError as e:
        logger.error(
            f"JSON parse error for article id={article.get('id')}: {e} | raw={raw[:200]}"
        )
        return None, None
    except Exception as e:
        logger.error(f"analyze_article error (id={article.get('id')}): {e}")
        return None, None


def _clamp(val) -> int:
    try:
        return max(0, min(100, int(val)))
    except (TypeError, ValueError):
        return 0


# ── Batch runner ──────────────────────────────────────────────────────────────
def run_analysis(limit: int = 20, delay: float = 0.5) -> int:
    """
    Analyze up to `limit` unanalyzed articles.
    `delay` (seconds) between API calls to stay within rate limits.
    Returns the count of successfully analyzed articles.
    """
    try:
        client = get_openai_client()
    except (ValueError, RuntimeError) as e:
        logger.error(f"OpenAI client init failed: {e}")
        raise  # Re-raise so the caller (Streamlit) can show the error

    articles      = get_unanalyzed_articles(limit=limit)
    analyzed_count = 0

    for art in articles:
        scores, note = analyze_article(client, art)
        if scores is not None and note:
            ok = insert_analysis(art["id"], scores, note)
            if ok:
                analyzed_count += 1
                logger.info(f"Analyzed article id={art['id']}: {art['title'][:60]}")
        if delay > 0 and len(articles) > 1:
            time.sleep(delay)

    return analyzed_count


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    print("🤖  AI analizi başlatılıyor…")
    try:
        n = run_analysis(limit=20)
        print(f"✅  {n} makale analiz edildi.")
    except Exception as exc:
        print(f"❌  Hata: {exc}")
        sys.exit(1)
