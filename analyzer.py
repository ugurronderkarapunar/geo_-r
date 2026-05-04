import openai
import os
from database import get_unanalyzed_articles, insert_analysis
import logging
import time

logger = logging.getLogger(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")

def analyze_article(title, summary):
    prompt = f"""Uluslararası İlişkiler teorilerine göre aşağıdaki haberi puanla (0-100).
Teoriler: Realizm, Liberalizm, İnşacılık, Eleştirel Teori, İngiliz Okulu.
Çıktı formatı:
Realizm: XX
Liberalizm: XX
İnşacılık: XX
Eleştirel Teori: XX
İngiliz Okulu: XX
Analiz Notu: (150 kelime)

Başlık: {title}
Özet: {summary}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=700
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return None

def parse_scores_and_note(raw):
    lines = raw.split("\n")
    scores = {}
    note = ""
    for line in lines:
        line_lower = line.lower()
        if "realizm" in line_lower and ":" in line:
            try:
                scores["realism"] = int(''.join(filter(str.isdigit, line.split(":")[-1])))
            except:
                scores["realism"] = 50
        elif "liberalizm" in line_lower and ":" in line:
            try:
                scores["liberalism"] = int(''.join(filter(str.isdigit, line.split(":")[-1])))
            except:
                scores["liberalism"] = 50
        elif "inşacılık" in line_lower and ":" in line:
            try:
                scores["constructivism"] = int(''.join(filter(str.isdigit, line.split(":")[-1])))
            except:
                scores["constructivism"] = 50
        elif "eleştirel teori" in line_lower and ":" in line:
            try:
                scores["critical_theory"] = int(''.join(filter(str.isdigit, line.split(":")[-1])))
            except:
                scores["critical_theory"] = 50
        elif "ingiliz okulu" in line_lower and ":" in line:
            try:
                scores["english_school"] = int(''.join(filter(str.isdigit, line.split(":")[-1])))
            except:
                scores["english_school"] = 50
        elif "analiz notu" in line_lower and ":" in line:
            note = line.split(":", 1)[-1].strip()
    # Varsayılan puanlar
    for k in ["realism", "liberalism", "constructivism", "critical_theory", "english_school"]:
        if k not in scores:
            scores[k] = 50
    return scores, note

def run_analysis():
    unanalyzed = get_unanalyzed_articles(limit=20)
    for art in unanalyzed:
        raw = analyze_article(art["title"], art["summary"])
        if raw:
            scores, note = parse_scores_and_note(raw)
            insert_analysis(art["id"], scores, note)
            logger.info(f"Analiz edildi: {art['title'][:50]}")
        time.sleep(1)  # rate limit

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_analysis()
