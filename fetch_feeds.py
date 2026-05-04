import feedparser
import os
from database import insert_article
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

RSS_FEEDS = {
    "CNN": "http://rss.cnn.com/rss/edition.rss",
    "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "BBC": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Foreign Policy": "https://foreignpolicy.com/feed/",
    "The Economist": "https://www.economist.com/feeds/print-sections/77/world-news.xml"
}

def fetch_and_store_feeds():
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:  # Her kaynaktan son 10 haber
                url_entry = entry.link
                title = entry.title
                published = entry.get("published", "")
                summary = entry.get("summary", "")[:1000]  # kısalt
                fetched_at = datetime.utcnow().isoformat()
                insert_article(url_entry, title, source, published, summary, fetched_at)
            logger.info(f"{source} başarıyla çekildi.")
        except Exception as e:
            logger.error(f"{source} hatası: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_and_store_feeds()
