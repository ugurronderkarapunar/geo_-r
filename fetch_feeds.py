import feedparser
import sqlite3
from datetime import datetime
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("GP_DB_PATH", "geopolitical_pulse.db")

RSS_SOURCES = [
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Foreign Policy", "url": "https://foreignpolicy.com/feed/"},
]

def insert_article(conn, url, title, source, published, summary):
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO articles
        (url, title, source, published_at, summary, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (url, title, source, published, summary, datetime.utcnow().isoformat()))
    return c.lastrowid

def fetch_all():
    conn = sqlite3.connect(DB_PATH)
    for src in RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:5]:
                pub_date = entry.get("published", "")
                summary = entry.get("summary", "")[:500]
                article_id = insert_article(conn, entry.link, entry.title, src["name"], pub_date, summary)
                if article_id:
                    logger.info(f"Eklendi: {entry.title}")
            conn.commit()
        except Exception as e:
            logger.error(f"Hata {src['name']}: {e}")
    conn.close()

if __name__ == "__main__":
    fetch_all()
