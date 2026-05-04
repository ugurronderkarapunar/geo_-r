from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime

def generate_pdf_report(article: dict) -> bytes:
    """
    article: get_article_by_id veya get_recent_articles_with_analyses'den dönen dict.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50
    c.drawString(100, y, "Geopolitical Pulse - Analiz Raporu")
    y -= 30
    c.drawString(100, y, f"Başlık: {article.get('title', 'Belirsiz')}")
    y -= 20
    c.drawString(100, y, f"Kaynak URL: {article.get('url', 'Belirsiz')}")
    y -= 20
    c.drawString(100, y, f"Yayın Tarihi: {article.get('published_at', 'Bilinmiyor')}")
    y -= 20
    c.drawString(100, y, f"Analiz Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 30

    c.drawString(100, y, "Teori Puanları (0-100):")
    y -= 20
    c.drawString(120, y, f"Realizm: {article.get('realism_score', 0)}")
    y -= 18
    c.drawString(120, y, f"Liberalizm: {article.get('liberalism_score', 0)}")
    y -= 18
    c.drawString(120, y, f"İnşacılık: {article.get('constructivism_score', 0)}")
    y -= 18
    c.drawString(120, y, f"Eleştirel Teori: {article.get('critical_theory_score', 0)}")
    y -= 18
    c.drawString(120, y, f"İngiliz Okulu: {article.get('english_school_score', 0)}")
    y -= 30

    c.drawString(100, y, "Analiz Notu:")
    y -= 20
    note = article.get('analysis_note', 'Analiz notu yok.')[:600]
    for line in note.split('\n'):
        if y < 50:
            c.showPage()
            y = height - 50
        c.drawString(100, y, line[:80])
        y -= 20

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
