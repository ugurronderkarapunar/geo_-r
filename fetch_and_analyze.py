#!/usr/bin/env python3
"""
Otomatik RSS çekme ve OpenAI analiz betiği.
GitHub Actions tarafından çalıştırılacak.
"""

import feedparser
import sqlite3
import os
import openai
import time
from datetime import datetime

DB_PATH = os.environ.get("GP_DB_PATH", "geopolitical_pulse.db")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

openai.api_key = OPENAI_API_KEY

RSS_SOURCES = [
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Foreign Policy", "url": "https://foreignpolicy.com/feed/"},
]

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            published_at TEXT,
            summary TEXT,
            fetched_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER UNIQUE NOT NULL,
            realism_score INTEGER DEFAULT 0,
            liberalism_score INTEGER DEFAULT 0,
            constructivism_score INTEGER DEFAULT 0,
            critical_theory_score INTEGER DEFAULT 0,
            english_school_score INTEGER DEFAULT 0,
            analysis_note TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
    """)
    conn.commit()
    conn.close()

def insert_article(url, title, source, published_at, summary, fetched_at):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO articles
        (url, title, source, published_at, summary, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (url, title, source, published_at, summary, fetched_at))
    is_new = c.rowcount > 0
    if is_new:
        article_id = c.lastrowid
    else:
        c.execute("SELECT id FROM articles WHERE url = ?", (url,))
        row = c.fetchone()
        article_id = row[0] if row else None
    conn.commit()
    conn.close()
    return article_id, is_new

def insert_analysis(article_id, scores, note, created_at):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO analyses
        (article_id, realism_score, liberalism_score, constructivism_score,
         critical_theory_score, english_school_score, analysis_note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (article_id,
          scores.get("realism", 0),
          scores.get("liberalism", 0),
          scores.get("constructivism", 0),
          scores.get("critical_theory", 0),
          scores.get("english_school", 0),
          note,
          created_at))
    conn.commit()
    conn.close()

def get_unanalyzed_articles(limit=20):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT a.id, a.title, a.summary
        FROM articles a
        LEFT JOIN analyses an ON a.id = an.article_id
        WHERE an.id IS NULL
        ORDER BY a.fetched_at DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "summary": r[2] or ""} for r in rows]

def analyze_with_openai(title, summary):
    prompt = f"""Şu haberi Uluslararası İlişkiler teorilerine göre puanla (0-100) ve kısa analiz notu yaz.
Başlık: {title}
Özet: {summary[:1500]}

Çıktı formatı (sadece şu şekilde, başka metin olmasın):
Realizm: XX
Liberalizm: XX
İnşacılık: XX
Eleştirel Teori: XX
İngiliz Okulu: XX
Analiz: ..."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        raw = response.choices[0].message.content
        scores = {"realism": 50, "liberalism": 50, "constructivism": 50,
                  "critical_theory": 50, "english_school": 50}
        note = "Analiz oluşturulamadı."
        for line in raw.split("\n"):
            if "Realizm:" in line:
                scores["realism"] = int(''.join(filter(str.isdigit, line)) or 50)
            elif "Liberalizm:" in line:
                scores["liberalism"] = int(''.join(filter(str.isdigit, line)) or 50)
            elif "İnşacılık:" in line:
                scores["constructivism"] = int(''.join(filter(str.isdigit, line)) or 50)
            elif "Eleştirel Teori:" in line:
                scores["critical_theory"] = int(''.join(filter(str.isdigit, line)) or 50)
            elif "İngiliz Okulu:" in line:
                scores["english_school"] = int(''.join(filter(str.isdigit, line)) or 50)
            elif "Analiz:" in line:
                note = line.replace("Analiz:", "").strip()
        return scores, note
    except Exception as e:
        print(f"OpenAI API hatası: {e}")
        return None, None

def main():
    init_db()
    print("📡 RSS çekiliyor...")
    new_count = 0
    for src in RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:5]:
                article_id, is_new = insert_article(
                    url=entry.link,
                    title=entry.title,
                    source=src["name"],
                    published_at=entry.get("published", ""),
                    summary=entry.get("summary", "")[:500],
                    fetched_at=datetime.utcnow().isoformat()
                )
                if is_new and article_id:
                    new_count += 1
            print(f"  {src['name']}: OK")
        except Exception as e:
            print(f"  {src['name']} hatası: {e}")

    print(f"✅ {new_count} yeni makale eklendi.")
    print("🧠 Analiz yapılmayan makaleler OpenAI ile analiz ediliyor...")
    unanalyzed = get_unanalyzed_articles(limit=20)
    analyzed_count = 0
    for art in unanalyzed:
        scores, note = analyze_with_openai(art["title"], art["summary"])
        if scores and note:
            insert_analysis(art["id"], scores, note, datetime.utcnow().isoformat())
            analyzed_count += 1
            print(f"  Analiz yapıldı: {art['title'][:50]}...")
            time.sleep(0.5)  # rate limit
        else:
            print(f"  Analiz başarısız: {art['title'][:50]}...")
    print(f"✅ {analyzed_count} makale analiz edildi.")
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM analyses")
    total_analyses = c.fetchone()[0]
    conn.close()
    print(f"📊 Veritabanında toplam {total_analyses} analiz bulunuyor.")

if __name__ == "__main__":
    main()
