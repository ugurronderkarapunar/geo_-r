"""
Geopolitical Pulse — AI-powered IR theory news analysis
Main Streamlit application entry point.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

# Bu import'lar src olmadan, doğrudan dosya adlarıyla
from database import init_db, SessionLocal, Feed, Analysis, User
from logger_config import logger
from pdf_report import generate_pdf_report
from analyzer import get_openai_client, analyze_news  # gerekirse
from fetch_feeds import fetch_and_store_feeds

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="error.log",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Geopolitical Pulse",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ─── Typography ─── */
    .gp-title   { font-size:2.1rem; font-weight:800; color:#1A1A2E; margin:0; }
    .gp-sub     { font-size:.9rem;  color:#6C757D; margin-top:2px; }

    /* ─── Cards ─── */
    .theory-tag {
        display:inline-block; padding:3px 10px; border-radius:20px;
        font-size:.72rem; font-weight:700; margin:3px 4px 0 0;
    }
    .tag-realism        { background:#FDECEA; color:#C0392B; }
    .tag-liberalism     { background:#EAF3FB; color:#2471A3; }
    .tag-constructivism { background:#E9F7EF; color:#1E8449; }
    .tag-critical       { background:#F5EEF8; color:#7D3C98; }
    .tag-english        { background:#FEF9E7; color:#D68910; }

    /* ─── Badges ─── */
    .badge-premium {
        background:linear-gradient(135deg,#FFD700,#FFA500);
        color:#fff; padding:3px 10px; border-radius:20px;
        font-size:.72rem; font-weight:800;
    }
    .badge-free {
        background:#E9ECEF; color:#495057;
        padding:3px 10px; border-radius:20px; font-size:.72rem; font-weight:700;
    }

    /* ─── Analysis block ─── */
    .analysis-box {
        background:#F8F9FA; padding:20px; border-radius:10px;
        border-left:4px solid #1A1A2E; line-height:1.85; font-size:.95rem;
    }

    /* ─── Streamlit tweaks ─── */
    .stButton > button { border-radius:8px; }
    div[data-testid="metric-container"] { background:#F8F9FA; border-radius:8px; padding:10px; }
</style>
""", unsafe_allow_html=True)

# ── DB init ───────────────────────────────────────────────────────────────────
init_db()

# ── Auth config ───────────────────────────────────────────────────────────────
def load_config():
    try:
        with open("config.yaml") as f:
            return yaml.load(f, Loader=SafeLoader)
    except FileNotFoundError:
        logger.error("config.yaml not found")
        st.error("⚠️  **config.yaml** bulunamadı. Lütfen şablondan oluşturun.")
        st.code("cp config.yaml.example config.yaml\npython generate_passwords.py")
        st.stop()
    except Exception as e:
        logger.error(f"Config load error: {e}")
        st.error(f"Yapılandırma hatası: {e}")
        st.stop()


config = load_config()

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# ── Constants ─────────────────────────────────────────────────────────────────
THEORY_INFO = {
    "realism":        {"label": "Realism",        "css": "tag-realism",        "color": "#E74C3C"},
    "liberalism":     {"label": "Liberalism",     "css": "tag-liberalism",     "color": "#3498DB"},
    "constructivism": {"label": "Constructivism", "css": "tag-constructivism", "color": "#2ECC71"},
    "critical_theory":{"label": "Critical Theory","css": "tag-critical",       "color": "#9B59B6"},
    "english_school": {"label": "English School", "css": "tag-english",        "color": "#F39C12"},
}

SCORE_KEYS = [
    ("realism_score",        "Realism",        "#E74C3C", "Güç siyaseti, ulusal çıkar, güvenlik ikilemi"),
    ("liberalism_score",     "Liberalism",     "#3498DB", "Uluslararası kurumlar, işbirliği, demokratik barış"),
    ("constructivism_score", "Constructivism", "#2ECC71", "Kimlik, normlar, gerçekliğin sosyal inşası"),
    ("critical_theory_score","Critical Theory","#9B59B6", "Güç yapıları, kurtuluş, eşitsizlik"),
    ("english_school_score", "English School", "#F39C12", "Uluslararası toplum, normlar, düzen"),
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_top_theories(article, n=2):
    scores = {k: article.get(f"{k}_score", 0) for k in THEORY_INFO}
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]


def is_premium(username: str) -> bool:
    try:
        return (config["credentials"]["usernames"]
                .get(username, {})
                .get("role", "free") == "premium")
    except Exception:
        return False


def fmt_date(s):
    if not s:
        return "—"
    try:
        return datetime.fromisoformat(s[:19]).strftime("%d %b %Y  %H:%M")
    except Exception:
        return str(s)[:16]


# ── Page: Dashboard ───────────────────────────────────────────────────────────
def page_dashboard():
    st.markdown('<p class="gp-title">🌍 Geopolitical Pulse</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="gp-sub">AI-destekli jeopolitik haber analizi — 5 UR teorisi merceğinden</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Control row ──
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        hours = st.selectbox(
            "Zaman aralığı",
            [24, 48, 72, 168],
            format_func=lambda x: f"Son {x} saat" if x < 168 else "Son 7 gün",
            label_visibility="collapsed",
        )
    with c2:
        if st.button("🔄 Haberleri Çek", use_container_width=True):
            with st.spinner("RSS beslemeleri alınıyor…"):
                try:
                    n = fetch_and_store_feeds()
                    st.success(f"✅ {n} yeni makale")
                except Exception as e:
                    logger.error(f"Fetch error: {e}")
                    st.error(str(e))
    with c3:
        if st.button("🤖 Analiz Et", use_container_width=True):
            with st.spinner("AI analiz yapıyor…"):
                try:
                    n = run_analysis(limit=15)
                    st.success(f"✅ {n} makale analiz edildi")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Analysis error: {e}")
                    st.error(str(e))
    with c4:
        username = st.session_state.get("username", "")
        badge = "badge-premium" if is_premium(username) else "badge-free"
        label = "⭐ Premium" if is_premium(username) else "🆓 Free"
        st.markdown(f'<span class="{badge}">{label}</span>', unsafe_allow_html=True)

    st.divider()

    # ── Article list ──
    articles = get_recent_articles_with_analyses(hours=hours)

    if not articles:
        st.info(
            "📭 Henüz analiz edilmiş haber yok. "
            "**Haberleri Çek** → **Analiz Et** adımlarını izleyin."
        )
        with st.expander("ℹ️ Başlarken"):
            st.markdown("""
1. **Haberleri Çek** — 5 RSS kaynağından haber çeker
2. **Analiz Et** — OpenAI ile UR teorisi puanları üretir
3. Haberler kartlar halinde burada görünür

> **Gereksinim:** `.streamlit/secrets.toml` içinde `OPENAI_API_KEY`
            """)
        return

    # Theory filter
    theory_filter = st.multiselect(
        "Teori filtresi",
        [v["label"] for v in THEORY_INFO.values()],
        placeholder="UR teorisine göre filtrele…",
        label_visibility="collapsed",
    )

    st.caption(f"**{len(articles)}** makale — son {hours} saat")

    cols = st.columns(2)
    rendered = 0

    for i, art in enumerate(articles):
        top = get_top_theories(art, 2)

        if theory_filter:
            labels = [THEORY_INFO[k]["label"] for k, _ in top]
            if not any(tf in labels for tf in theory_filter):
                continue

        with cols[rendered % 2]:
            with st.container(border=True):
                mc1, mc2 = st.columns(2)
                with mc1:
                    st.caption(f"📰 {art.get('source', '?')}")
                with mc2:
                    st.caption(f"🕐 {fmt_date(art.get('published_at') or art.get('fetched_at'))}")

                st.markdown(f"**{art.get('title', 'Başlık yok')}**")

                summ = art.get("summary", "")
                if summ:
                    st.markdown(
                        f"<small style='color:#555'>{summ[:160]}{'…' if len(summ)>160 else ''}</small>",
                        unsafe_allow_html=True,
                    )

                tags = "".join(
                    f'<span class="theory-tag {THEORY_INFO[k]["css"]}">'
                    f'{THEORY_INFO[k]["label"]} {s}</span>'
                    for k, s in top
                )
                st.markdown(tags, unsafe_allow_html=True)
                st.markdown("")

                if st.button("Analizi Gör →", key=f"card_{art['id']}", use_container_width=True):
                    st.session_state["page"] = "detail"
                    st.session_state["article_id"] = art["id"]
                    st.rerun()

        rendered += 1


# ── Page: Detail ──────────────────────────────────────────────────────────────
def page_detail():
    if st.button("← Dashboard"):
        st.session_state["page"] = "dashboard"
        st.rerun()

    art_id = st.session_state.get("article_id")
    if not art_id:
        st.session_state["page"] = "dashboard"
        st.rerun()
        return

    try:
        art = get_article_by_id(art_id)
    except Exception as e:
        logger.error(f"Article fetch error: {e}")
        st.error(f"Makale yüklenemedi: {e}")
        return

    if not art:
        st.error("Makale bulunamadı.")
        return

    st.divider()
    st.markdown(f"## {art.get('title', 'Başlıksız')}")

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Kaynak", art.get("source", "—"))
    mc2.metric("Yayın", fmt_date(art.get("published_at") or ""))
    mc3.metric("Analiz", fmt_date(art.get("fetched_at") or ""))

    if art.get("url"):
        st.markdown(f"[🔗 Orijinal Makale]({art['url']})")

    if art.get("summary"):
        with st.expander("📄 Özet", expanded=False):
            st.write(art["summary"])

    st.divider()
    st.markdown("### 📊 UR Teorisi Puanları")

    col_bar, col_rank = st.columns([3, 2])

    with col_bar:
        for sk, name, color, desc in SCORE_KEYS:
            score = art.get(sk, 0)
            st.markdown(f"**{name}** &nbsp;— {score}/100")
            st.progress(score / 100, text=f"_{desc}_")
            st.markdown("")

    with col_rank:
        st.markdown("**Sıralama**")
        ranked = sorted(
            [(name, art.get(sk, 0)) for sk, name, _, _ in SCORE_KEYS],
            key=lambda x: x[1], reverse=True
        )
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, (name, score) in enumerate(ranked):
            st.markdown(f"{medals[i]} **{name}**: {score}")

    st.divider()
    st.markdown("### 📝 Teorik Analiz Notu")

    note = art.get("analysis_note", "")
    if note:
        st.markdown(
            f'<div class="analysis-box">{note}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Bu makale için analiz notu henüz oluşturulmadı.")

    st.divider()

    # ── PDF Export (premium) ──
    username = st.session_state.get("username", "")
    st.markdown("### 📄 Rapor İndir")

    if is_premium(username):
        if st.button("⬇️ PDF Raporu Oluştur", type="primary"):
            with st.spinner("PDF oluşturuluyor…"):
                try:
                    buf = generate_pdf_report([art], username=username)
                    if buf:
                        st.download_button(
                            "📥 PDF İndir",
                            data=buf,
                            file_name=(
                                f"geopolitical_pulse_{art_id}_"
                                f"{datetime.now().strftime('%Y%m%d')}.pdf"
                            ),
                            mime="application/pdf",
                        )
                    else:
                        st.error("PDF oluşturulamadı. error.log dosyasını kontrol edin.")
                except Exception as e:
                    logger.error(f"PDF export error: {e}")
                    st.error(str(e))
    else:
        st.warning("⭐ **Premium özellik** — PDF raporu indirmek için premium'a geçin.")
        if st.button("🚀 Premium'a Geç"):
            st.session_state["page"] = "upgrade"
            st.rerun()


# ── Page: Upgrade ─────────────────────────────────────────────────────────────
def page_upgrade():
    if st.button("← Geri"):
        st.session_state["page"] = "dashboard"
        st.rerun()

    st.markdown("## ⭐ Premium'a Geç")

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("### 🆓 Ücretsiz Plan\n**$0 / ay**")
            st.divider()
            for line in ["✅ 24 saatlik haber akışı", "✅ 5-teori analizi",
                         "✅ Teori etiketleri", "❌ PDF indirme",
                         "❌ 7+ gün geçmiş", "❌ Gelişmiş filtre"]:
                st.markdown(line)

    with c2:
        with st.container(border=True):
            st.markdown("### ⭐ Premium Plan\n**$9.99 / ay**")
            st.divider()
            for line in ["✅ Ücretsiz plandaki her şey", "✅ **PDF rapor indirme**",
                         "✅ 30 günlük geçmiş", "✅ Gelişmiş filtreler",
                         "✅ Öncelikli destek"]:
                st.markdown(line)
            st.markdown("")
            if st.button("💳 Şimdi Abone Ol", type="primary", use_container_width=True):
                _handle_stripe_checkout()


def _handle_stripe_checkout():
    try:
        import stripe
        stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "sk_test_PLACEHOLDER")
        if "PLACEHOLDER" in stripe.api_key:
            st.info(
                "🚧 **Test modu** — Gerçek anahtar için "
                "`.streamlit/secrets.toml` dosyasına `STRIPE_SECRET_KEY` ekleyin."
            )
        else:
            # Production: create checkout session
            # session = stripe.checkout.Session.create(
            #     payment_method_types=["card"],
            #     line_items=[{"price": "price_XXXX", "quantity": 1}],
            #     mode="subscription",
            #     success_url="https://yourdomain.com/?success=true",
            #     cancel_url="https://yourdomain.com/?cancelled=true",
            # )
            # st.markdown(f"[Ödeme sayfasına git →]({session.url})")
            st.info("Stripe checkout session oluşturulacak.")
    except ImportError:
        st.warning("`stripe` kütüphanesi bulunamadı. `requirements.txt` kontrol edin.")
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        st.error(str(e))


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    username = st.session_state.get("username", "")
    name = st.session_state.get("name", "Kullanıcı")

    with st.sidebar:
        st.markdown(f"### 👤 {name}")
        badge = "badge-premium" if is_premium(username) else "badge-free"
        label = "⭐ Premium" if is_premium(username) else "🆓 Free"
        st.markdown(f'<span class="{badge}">{label}</span>', unsafe_allow_html=True)
        st.divider()

        st.markdown("**Navigasyon**")
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.rerun()
        if not is_premium(username):
            if st.button("⭐ Premium'a Geç", use_container_width=True):
                st.session_state["page"] = "upgrade"
                st.rerun()

        st.divider()

        # DB Stats
        try:
            stats = get_db_stats()
            st.markdown("**İstatistikler**")
            st.metric("Toplam Makale", stats.get("articles", 0))
            st.metric("Analiz Edilmiş", stats.get("analyses", 0))
        except Exception as e:
            logger.error(f"Sidebar stats error: {e}")

        st.divider()

        with st.expander("ℹ️ Hakkında"):
            st.markdown("""
**Geopolitical Pulse** haberleri 5 UR teorisi merceğinden analiz eder:
- 🔴 **Realizm**
- 🔵 **Liberalizm**
- 🟢 **İnşacılık**
- 🟣 **Eleştirel Teori**
- 🟡 **İngiliz Okulu**

*OpenAI GPT ile desteklenmektedir.*
            """)

        st.divider()
        authenticator.logout("🚪 Çıkış Yap", "sidebar")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Session state defaults
    st.session_state.setdefault("page", "dashboard")
    st.session_state.setdefault("article_id", None)

    # Auth
    try:
        authenticator.login()
    except Exception as e:
        logger.error(f"Auth error: {e}")
        st.error(f"Kimlik doğrulama hatası: {e}")
        return

    status = st.session_state.get("authentication_status")

    if status is False:
        st.error("❌ Kullanıcı adı veya şifre hatalı.")
        return

    if status is None:
        # Landing page
        st.markdown('<p class="gp-title">🌍 Geopolitical Pulse</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="gp-sub">Jeopolitik haberleri AI ile 5 UR teorisi merceğinden analiz edin</p>',
            unsafe_allow_html=True,
        )
        st.info("Devam etmek için yukarıdaki forma giriş yapın.")
        c1, c2, c3 = st.columns(3)
        c1.markdown("**📰 Canlı Haber Akışı**\n5 prestijli jeopolitik kaynaktan otomatik güncelleme")
        c2.markdown("**🤖 AI Analiz**\nHer haber 5 UR teorisi çerçevesinde puanlanır")
        c3.markdown("**📊 İnteraktif Gösterge Paneli**\nTeori etiketleri ve detaylı puan kartları")
        return

    if status:
        render_sidebar()
        page = st.session_state.get("page", "dashboard")
        try:
            if page == "dashboard":
                page_dashboard()
            elif page == "detail":
                page_detail()
            elif page == "upgrade":
                page_upgrade()
            else:
                page_dashboard()
        except Exception as e:
            logger.error(f"Page render error ({page}): {e}")
            st.error(f"Sayfa yüklenirken hata oluştu: {e}")


if __name__ == "__main__":
    main()
