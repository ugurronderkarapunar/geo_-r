import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import stripe
import feedparser
import openai
import time

from database import (
    init_db,
    get_recent_articles_with_analyses,
    get_article_by_id,
    get_db_stats,
    insert_article,
    insert_analysis,
    get_unanalyzed_articles,
)
from logger_config import logger
from pdf_report import generate_pdf_report

st.set_page_config(page_title="Geopolitical Pulse", layout="wide")

# Stripe ve OpenAI anahtarları
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "sk_test_placeholder")
openai_api_key = st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))

# Yeni OpenAI istemcisi (openai>=1.0.0 için)
openai_client = openai.OpenAI(api_key=openai_api_key)

# Oturum
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None

def login():
    with st.sidebar:
        st.subheader("🔐 Giriş")
        email = st.text_input("E-posta")
        if st.button("Demo Giriş (Ücretsiz)"):
            st.session_state.authenticated = True
            st.session_state.username = email or "demo@example.com"
            st.rerun()
        if st.button("Premium Abone Ol (Stripe Test)"):
            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {'name': 'Geopolitical Pulse Premium'},
                            'unit_amount': 999,
                        },
                        'quantity': 1,
                    }],
                    mode='subscription',
                    success_url='https://yourdomain.com/success',
                    cancel_url='https://yourdomain.com/cancel',
                )
                st.markdown(f"[Ödeme Sayfası]({session.url})")
            except Exception as e:
                st.error("Stripe test modunda")
                logger.error(f"Stripe: {e}")

if not st.session_state.authenticated:
    login()
    st.stop()

is_premium = "premium" in st.session_state.username.lower()
init_db()
stats = get_db_stats()
st.sidebar.metric("Toplam Makale", stats["articles"])
st.sidebar.metric("Analiz Edilen", stats["analyses"])

st.title("🌍 Geopolitical Pulse")
st.caption("Uluslararası İlişkiler Teorileriyle Haber Analizi")

# ─── Buton: Haberleri Çek ve Analiz Et ────────────────────────────────────────
if st.sidebar.button("📡 Şimdi Haberleri Çek ve Analiz Et", type="primary"):
    with st.spinner("RSS kaynakları taranıyor ve OpenAI analizi yapılıyor..."):
        rss_sources = [
            {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
            {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
            {"name": "Foreign Policy", "url": "https://foreignpolicy.com/feed/"},
        ]
        new_count = 0
        for src in rss_sources:
            try:
                feed = feedparser.parse(src["url"])
                for entry in feed.entries[:3]:
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
            except Exception as e:
                st.warning(f"{src['name']} hatası: {e}")
        st.success(f"{new_count} yeni haber eklendi. Şimdi analiz ediliyor...")
        
        unanalyzed = get_unanalyzed_articles(limit=10)
        analyzed = 0
        for art in unanalyzed:
            try:
                response = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": f"""Şu haberi Uluslararası İlişkiler teorilerine göre puanla (0-100) ve kısa analiz notu yaz.
Başlık: {art['title']}
Özet: {art.get('summary', '')[:1500]}

Çıktı formatı (sadece şu şekilde, başka metin olmasın):
Realizm: XX
Liberalizm: XX
İnşacılık: XX
Eleştirel Teori: XX
İngiliz Okulu: XX
Analiz: ..."""
                    }],
                    temperature=0.3
                )
                raw = response.choices[0].message.content
                scores = {"realism": 50, "liberalism": 50, "constructivism": 50, "critical_theory": 50, "english_school": 50}
                note = "Analiz oluşturulamadı."
                for line in raw.split("\n"):
                    if "Realizm:" in line:
                        scores["realism"] = int(''.join(filter(str.isdigit, line)))
                    elif "Liberalizm:" in line:
                        scores["liberalism"] = int(''.join(filter(str.isdigit, line)))
                    elif "İnşacılık:" in line:
                        scores["constructivism"] = int(''.join(filter(str.isdigit, line)))
                    elif "Eleştirel Teori:" in line:
                        scores["critical_theory"] = int(''.join(filter(str.isdigit, line)))
                    elif "İngiliz Okulu:" in line:
                        scores["english_school"] = int(''.join(filter(str.isdigit, line)))
                    elif "Analiz:" in line:
                        note = line.replace("Analiz:", "").strip()
                insert_analysis(art["id"], scores, note)
                analyzed += 1
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"OpenAI hatası {art['id']}: {e}")
        st.success(f"{analyzed} haber analiz edildi. Sayfayı yenileyin!")
        st.rerun()

# Normal akış: Son 7 gün haberlerini göster
articles = get_recent_articles_with_analyses(hours=168)

if not articles:
    st.info("📭 Henüz hiç haber yok. Sol menüden **'Şimdi Haberleri Çek ve Analiz Et'** butonuna tıklayarak ilk haberleri getirebilirsiniz.")
else:
    cols = st.columns(2)
    for idx, art in enumerate(articles):
        scores = {
    "Realizm": art.get("realism_score") or 0,
    "Liberalizm": art.get("liberalism_score") or 0,
    "İnşacılık": art.get("constructivism_score") or 0,
    "Eleştirel Teori": art.get("critical_theory_score") or 0,
    "İngiliz Okulu": art.get("english_school_score") or 0,
}
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        tags = " | ".join([f"{t}: {s:.0f}" for t, s in top])
        with cols[idx % 2]:
            with st.expander(f"📰 {art['title']}"):
                st.markdown(f"**Kaynak:** {art['source']}")
                st.markdown(f"**Yayın:** {art.get('published_at', 'Bilinmiyor')}")
                st.markdown(f"**🔖 {tags}**")
                if st.button("Detay", key=f"btn_{art['id']}"):
                    st.session_state.selected_article_id = art["id"]
                    st.rerun()

# Detay sayfası
if "selected_article_id" in st.session_state:
    art_id = st.session_state.selected_article_id
    article = get_article_by_id(art_id)
    if article:
        st.subheader(f"🔍 {article['title']}")
        st.write(f"**Kaynak:** {article['url']}")
        df = pd.DataFrame({
            "Teori": ["Realizm","Liberalizm","İnşacılık","Eleştirel Teori","İngiliz Okulu"],
            "Puan": [article.get("realism_score",0), article.get("liberalism_score",0),
                     article.get("constructivism_score",0), article.get("critical_theory_score",0),
                     article.get("english_school_score",0)]
        })
        st.plotly_chart(px.bar(df, x="Teori", y="Puan", title="Teorik Puanlar"))
        st.markdown("### Analiz Notu")
        st.write(article.get("analysis_note", "Analiz yok."))
        if is_premium:
            if st.button("PDF Rapor"):
                pdf = generate_pdf_report(article)
                st.download_button("İndir", pdf, "rapor.pdf")
        else:
            st.info("Premium aboneler PDF alabilir.")
        if st.button("← Geri"):
            del st.session_state.selected_article_id
            st.rerun()
    else:
        st.error("Makale bulunamadı.")
        del st.session_state.selected_article_id
        st.rerun()
