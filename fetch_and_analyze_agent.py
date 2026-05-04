#!/usr/bin/env python3
import feedparser, sqlite3, os, openai, time
from datetime import datetime

DB_PATH = os.environ.get("GP_DB_PATH", "geopolitical_pulse.db")
openai.api_key = os.environ.get("OPENAI_API_KEY")

RSS_SOURCES = [
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Foreign Policy", "url": "https://foreignpolicy.com/feed/"},
]

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT, source TEXT, published_at TEXT, summary TEXT, fetched_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS analyses (id INTEGER PRIMARY KEY, article_id INTEGER UNIQUE, realism_score INTEGER, liberalism_score INTEGER, constructivism_score INTEGER, critical_theory_score INTEGER, english_school_score INTEGER, analysis_note TEXT, created_at TEXT)")

def insert_article(url, title, source, published_at, summary, fetched_at):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO articles (url, title, source, published_at, summary, fetched_at) VALUES (?,?,?,?,?,?)",
              (url, title, source, published_at, summary, fetched_at))
    if c.rowcount:
        article_id = c.lastrowid
    else:
        c.execute("SELECT id FROM articles WHERE url=?", (url,))
        article_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return article_id

def insert_analysis(article_id, scores, note, created_at):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO analyses (article_id, realism_score, liberalism_score, constructivism_score, critical_theory_score, english_school_score, analysis_note, created_at) VALUES (?,?,?,?,?,?,?,?)",
                  (article_id, scores["realism"], scores["liberalism"], scores["constructivism"],
                   scores["critical_theory"], scores["english_school"], note, created_at))

def get_unanalyzed():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT a.id, a.title, a.summary FROM articles a LEFT JOIN analyses an ON a.id=an.article_id WHERE an.id IS NULL LIMIT 20")
        return [{"id":r[0], "title":r[1], "summary":r[2] or ""} for r in c.fetchall()]

def analyze(title, summary):
    prompt = f"""Şu haberi Uluslararası İlişkiler teorilerine göre puanla (0-100) ve Türkçe analiz notu yaz (150 kelime).
Başlık: {title}
Özet: {summary[:1500]}
Çıktı formatı:
Realizm: XX
Liberalizm: XX
İnşacılık: XX
Eleştirel Teori: XX
İngiliz Okulu: XX
Analiz: ..."""
    resp = openai.ChatCompletion.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], temperature=0.3)
    raw = resp.choices[0].message.content
    scores = {"realism":50,"liberalism":50,"constructivism":50,"critical_theory":50,"english_school":50}
    note = ""
    for line in raw.split("\n"):
        if "Realizm:" in line:
            scores["realism"] = int(''.join(filter(str.isdigit,line)) or 50)
        elif "Liberalizm:" in line:
            scores["liberalism"] = int(''.join(filter(str.isdigit,line)) or 50)
        elif "İnşacılık:" in line:
            scores["constructivism"] = int(''.join(filter(str.isdigit,line)) or 50)
        elif "Eleştirel Teori:" in line:
            scores["critical_theory"] = int(''.join(filter(str.isdigit,line)) or 50)
        elif "İngiliz Okulu:" in line:
            scores["english_school"] = int(''.join(filter(str.isdigit,line)) or 50)
        elif "Analiz:" in line:
            note = line.replace("Analiz:","").strip()
    return scores, note

def main():
    if not openai.api_key:
        print("OpenAI API anahtarı bulunamadı. Lütfen ortam değişkenini ayarlayın.")
        return
    init_db()
    print("RSS çekiliyor...")
    for src in RSS_SOURCES:
        feed = feedparser.parse(src["url"])
        for entry in feed.entries[:3]:
            insert_article(entry.link, entry.title, src["name"],
                           entry.get("published",""), entry.get("summary","")[:500],
                           datetime.utcnow().isoformat())
            print(f"   {src['name']}: {entry.title[:50]}")
    art_list = get_unanalyzed()
    print(f"Analiz edilecek {len(art_list)} makale bulundu.")
    for art in art_list:
        scores, note = analyze(art["title"], art["summary"])
        insert_analysis(art["id"], scores, note, datetime.utcnow().isoformat())
        print(f"   Analiz tamam: {art['title'][:50]} -> Realizm: {scores['realism']}")
        time.sleep(0.5)
    print("İşlem tamamlandı.")

if __name__ == "__main__":
    main()
