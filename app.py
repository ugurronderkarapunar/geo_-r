import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import stripe

from database import (
    init_db,
    get_recent_articles_with_analyses,
    get_article_by_id,
    get_db_stats,
)
from logger_config import logger
from pdf_report import generate_pdf_report

st.set_page_config(page_title="Geopolitical Pulse", layout="wide")

# Stripe test key (secrets veya env)
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "sk_test_placeholder")

# Basit oturum yönetimi (demo)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None

def login():
    with st.sidebar:
        st.subheader("🔐 Giriş / Abonelik")
        email = st.text_input("E-posta adresiniz")
        if st.button("Demo Giriş (Ücretsiz)"):
            st.session_state.authenticated = True
            st.session_state.username = email or "demo@example.com"
            st.rerun()
        if st.button("Premium Abone Ol (Stripe Test)"):
            try:
                checkout_session = stripe.checkout.Session.create(
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
                st.markdown(f"[Ödeme Sayfasına Git]({checkout_session.url})")
            except Exception as e:
                st.error("Stripe test modunda – ödeme simülasyonu")
                logger.error(f"Stripe: {e}")

if not st.session_state.authenticated:
    login()
    st.stop()

# Kullanıcı premium mu? Basit demo: email 'premium' içeriyorsa
is_premium = "premium" in st.session_state.username.lower()

# Veritabanını başlat
if not init_db():
    st.error("Veritabanı başlatılamadı. Logları kontrol edin.")
    st.stop()

st.title("🌍 Geopolitical Pulse")
st.caption("Uluslararası İlişkiler Teorileriyle Haber Analizi")

# İstatistikleri göster
stats = get_db_stats()
st.sidebar.metric("Toplam Makale", stats["articles"])
st.sidebar.metric("Analiz Edilen", stats["analyses"])

# Son 24 saat haberlerini getir
articles = get_recent_articles_with_analyses(hours=24)

if not articles:
    st.info("Son 24 saatte analiz edilmiş haber yok. Lütfen daha sonra kontrol edin.")
else:
    # Kartları 2 sütun halinde göster
    cols = st.columns(2)
    for idx, art in enumerate(articles):
        # En yüksek puanlı 2 teori
        scores = {
            "Realizm": art.get("realism_score", 0),
            "Liberalizm": art.get("liberalism_score", 0),
            "İnşacılık": art.get("constructivism_score", 0),
            "Eleştirel Teori": art.get("critical_theory_score", 0),
            "İngiliz Okulu": art.get("english_school_score", 0),
        }
        top_theories = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        theory_tags = " | ".join([f"{t}: {s:.0f}" for t, s in top_theories])

        with cols[idx % 2]:
            with st.expander(f"📰 {art['title']}"):
                st.markdown(f"**Kaynak:** {art['source']}")
                st.markdown(f"**Yayın:** {art.get('published_at', 'Bilinmiyor')}")
                st.markdown(f"**🔖 Teori etiketleri:** {theory_tags}")
                if st.button("🔍 Detaylı Analiz", key=f"btn_{art['id']}"):
                    st.session_state.selected_article_id = art["id"]
                    st.rerun()

# Detay sayfası
if "selected_article_id" in st.session_state:
    art_id = st.session_state.selected_article_id
    article = get_article_by_id(art_id)
    if article:
        st.subheader(f"🔍 {article['title']}")
        st.write(f"**Kaynak:** {article['url']}")
        st.write(f"**Yayın tarihi:** {article.get('published_at', 'Bilinmiyor')}")

        # Puanları DataFrame ve grafik
        df_scores = pd.DataFrame({
            "Teori": ["Realizm", "Liberalizm", "İnşacılık", "Eleştirel Teori", "İngiliz Okulu"],
            "Puan": [
                article.get("realism_score", 0),
                article.get("liberalism_score", 0),
                article.get("constructivism_score", 0),
                article.get("critical_theory_score", 0),
                article.get("english_school_score", 0),
            ]
        })
        fig = px.bar(df_scores, x="Teori", y="Puan", title="Teorik Ağırlıklar", color="Teori")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📝 Analiz Notu")
        st.write(article.get("analysis_note", "Analiz notu bulunamadı."))

        if is_premium:
            if st.button("📄 PDF Rapor Oluştur"):
                pdf_data = generate_pdf_report(article)
                st.download_button(
                    label="PDF İndir",
                    data=pdf_data,
                    file_name=f"rapor_{article['id']}.pdf",
                    mime="application/pdf"
                )
        else:
            st.info("Premium aboneler PDF rapor görebilir. Sol menüden abone olun.")

        if st.button("← Gündeme Dön"):
            del st.session_state.selected_article_id
            st.rerun()
    else:
        st.error("Makale bulunamadı.")
        del st.session_state.selected_article_id
        st.rerun()

# Footer
st.markdown("---")
st.caption("Geopolitical Pulse - Uluslararası İlişkiler Teorileriyle Haber Analizi")
