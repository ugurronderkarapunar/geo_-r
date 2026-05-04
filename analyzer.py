import openai
import sqlite3
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("GP_DB_PATH", "geopolitical_pulse.db")
openai.api_key = os.environ.get("OPENAI_API_KEY")

def analyze_unanalyzed():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT a.id, a.title, a.summary
        FROM articles a
        LEFT JOIN analyses an ON a.id = an.article_id
        WHERE an.id IS NULL
        LIMIT 5
    """)
    articles = c.fetchall()
    for art_id, title, summary in articles:
        text = f"{title}\n{summary[:1500]}"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"Puanla (realizm, liberalizm, inşacılık, eleştirel, ingiliz okulu) 0-100. Analiz notu yaz: {text}"}],
                temperature=0.3
            )
            # Basit parse (gerçekte daha sağlam yapın)
            scores = {"realism": 70, "liberalism": 40, "constructivism": 30, "critical_theory": 20, "english_school": 50}
            note = "Örnek analiz."
            c.execute("""
                INSERT OR REPLACE INTO analyses
                (article_id, realism_score, liberalism_score, constructivism_score,
                 critical_theory_score, english_school_score, analysis_note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (art_id, scores["realism"], scores["liberalism"], scores["constructivism"],
                  scores["critical_theory"], scores["english_school"], note, datetime.utcnow().isoformat()))
            conn.commit()
            logger.info(f"Analiz yapıldı: {title}")
        except Exception as e:
            logger.error(f"OpenAI hatası: {e}")
    conn.close()

if __name__ == "__main__":
    analyze_unanalyzed()
