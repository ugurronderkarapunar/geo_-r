"""
src/fetch_feeds.py
Fetches articles from 5 geopolitical RSS feeds and stores them in SQLite.
Can be imported as a module (Streamlit) or run directly (CLI / GitHub Actions).
"""

import re
import sys
import os
import logging
from datetime import datetime

import feedparser

# ── Path fix for direct CLI invocation ───────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import insert_article, init_db

logger = logging.getLogger(__name__)

# ── Feed definitions ──────────────────────────────────────────────────────────
RSS_FEEDS = [
    {
        "name": "BBC World News",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
    },
    {
        "name": "Reuters World",
        "url": "https://feeds.reuters.com/reuters/worldnews",
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
    },
    {
        "name": "Foreign Policy",
        "url": "https://foreignpolicy.com/feed/",
    },
    {
        "name": "The Guardian World",
        "url": "https://www.theguardian.com/world/rss",
    },
]

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE  = re.compile(r"\s+")


def _clean(text: str, max_len: int = 1000) -> str:
    """Strip HTML tags and normalise whitespace."""
    text = _TAG_RE.sub(" ", text or "")
    text = _WS_RE.sub(" ", text).strip()
    return text[:max_len]


def _parse_date(entry) -> str | None:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6]).isoformat()
            except Exception:
                pass
    return None


def fetch_and_store_feeds(entries_per_feed: int = 15) -> int:
    """
    Fetch all RSS feeds and insert new articles into the DB.
    Returns the count of **newly inserted** articles.
    """
    init_db()
    total_new = 0

    for feed_cfg in RSS_FEEDS:
        name = feed_cfg["name"]
        url  = feed_cfg["url"]
        try:
            feed = feedparser.parse(url)

            if feed.get("bozo") and feed.get("bozo_exception"):
                # Log but continue — partial feeds are still useful
                logger.warning(
                    f"Bozo feed from '{name}': {feed['bozo_exception']}"
                )

            for entry in feed.entries[:entries_per_feed]:
                try:
                    link = entry.get("link", "").strip()
                    if not link:
                        continue

                    title   = _clean(entry.get("title", "Başlık yok"), max_len=300)
                    summary = _clean(
                        entry.get("summary", entry.get("description", "")),
                        max_len=1000,
                    )
                    published_at = _parse_date(entry)
                    fetched_at   = datetime.utcnow().isoformat()

                    _, is_new = insert_article(
                        url=link,
                        title=title,
                        source=name,
                        published_at=published_at,
                        summary=summary,
                        fetched_at=fetched_at,
                    )
                    if is_new:
                        total_new += 1

                except Exception as e:
                    logger.error(f"Entry processing error ({name}): {e}")

        except Exception as e:
            logger.error(f"Feed fetch error ({name} — {url}): {e}")

    return total_new


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    print("📡  RSS beslemeleri alınıyor…")
    count = fetch_and_store_feeds()
    print(f"✅  {count} yeni makale veritabanına eklendi.")
