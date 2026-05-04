# 🌍 Geopolitical Pulse

> AI destekli jeopolitik haber analizi — 5 Uluslararası İlişkiler teorisi merceğinden.

---

## 📁 Proje Yapısı

```
geopolitical-pulse/
├── app.py                        # Ana Streamlit uygulaması
├── config.yaml                   # Kullanıcı kimlik bilgileri (hashlenmiş)
├── requirements.txt
├── generate_passwords.py         # Şifre hash üretici
├── scripts/
│   └── update.py                 # CLI: RSS çek + analiz et
├── src/
│   ├── database.py               # SQLite katmanı
│   ├── fetch_feeds.py            # RSS beslemelerini çeker
│   ├── analyzer.py               # OpenAI ile teori analizi
│   └── pdf_report.py             # ReportLab PDF çıktısı
├── .streamlit/
│   ├── secrets.toml              # API anahtarları (git'e koymayın!)
│   └── config.toml               # Tema ve sunucu ayarları
└── .github/
    └── workflows/
        └── update_feeds.yml      # Otomatik güncelleme (6 saatte bir)
```

---

## 🚀 Kurulum

### 1. Depoyu klonla

```bash
git clone https://github.com/KULLANICI_ADINIZ/geopolitical-pulse.git
cd geopolitical-pulse
```

### 2. Sanal ortam oluştur ve bağımlılıkları yükle

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🔑 OpenAI API Anahtarı Nasıl Eklenir?

### Adım 1 — API anahtarını al

1. [platform.openai.com](https://platform.openai.com) adresine git
2. Sağ üstteki profil → **API keys** → **Create new secret key**
3. `sk-proj-...` ile başlayan anahtarı kopyala

### Adım 2 — secrets.toml dosyasını düzenle

`.streamlit/secrets.toml` dosyasını aç ve anahtarını yapıştır:

```toml
OPENAI_API_KEY = "sk-proj-BURAYA_GERCEK_ANAHTARINIZI_YAPISTIRIN"
```

> ⚠️ Bu dosyayı asla git'e push etme! `.gitignore`'a eklidir.

### Adım 3 — API kullanımını test et

```bash
python -c "
import os; os.environ['OPENAI_API_KEY']='sk-proj-...'
from src.analyzer import get_openai_client
c = get_openai_client()
print('✅ Bağlantı başarılı!')
"
```

---

## 👤 Kullanıcıları Yapılandır

### 1. Şifreleri hashle

```bash
python generate_passwords.py
```

Çıktı şöyle görünür:
```
  Kullanıcı : admin
  Şifre     : Admin@2024!
  Hash      : $2b$12$abc123...

  Kullanıcı : premium1
  ...
```

### 2. config.yaml'a yapıştır

`config.yaml` dosyasını aç, `password:` alanlarına hash değerlerini yapıştır:

```yaml
credentials:
  usernames:
    admin:
      email:    admin@example.com
      name:     Admin User
      password: "$2b$12$abc123..."   # ← hashlenmiş şifre
      role:     premium              # premium | free
    kullanici1:
      ...
      role:     free
```

> `role: premium` → PDF export aktif  
> `role: free` → yalnızca okuma

---

## ▶️ Uygulamayı Çalıştır

```bash
streamlit run app.py
```

Tarayıcıda `http://localhost:8501` adresine git.

---

## 🤖 Manuel Güncelleme (CLI)

```bash
# RSS çek + analiz et (varsayılan)
python scripts/update.py

# Sadece RSS çek
python scripts/update.py --fetch-only

# Sadece analiz et (max 10 makale)
python scripts/update.py --analyze-only --limit 10
```

---

## ⚙️ GitHub Actions Otomasyonu

Her 6 saatte bir otomatik RSS güncellemesi için:

1. GitHub deposuna git → **Settings → Secrets and variables → Actions**
2. **New repository secret** ekle:
   - Name: `OPENAI_API_KEY`
   - Value: `sk-proj-...`
3. `.github/workflows/update_feeds.yml` zaten repo'da, otomatik çalışır.

Manuel tetiklemek için: **Actions → 🌍 Geopolitical Pulse — Auto Update → Run workflow**

---

## 💳 Stripe Entegrasyonu (Test Modu)

1. [dashboard.stripe.com/test/apikeys](https://dashboard.stripe.com/test/apikeys) adresine git
2. **Test anahtarlarını** kopyala (`sk_test_...` ve `pk_test_...`)
3. `.streamlit/secrets.toml`'a ekle:

```toml
STRIPE_SECRET_KEY      = "sk_test_..."
STRIPE_PUBLISHABLE_KEY = "pk_test_..."
```

> `src/app.py` içindeki `_handle_stripe_checkout()` fonksiyonunda `checkout.Session.create()` çağrısının yorumunu kaldır ve Stripe price ID'ni ekle.

---

## 🧪 RSS Kaynakları

| Kaynak | URL |
|--------|-----|
| BBC World News | `feeds.bbci.co.uk/news/world/rss.xml` |
| Reuters World | `feeds.reuters.com/reuters/worldnews` |
| Al Jazeera | `aljazeera.com/xml/rss/all.xml` |
| Foreign Policy | `foreignpolicy.com/feed/` |
| The Guardian World | `theguardian.com/world/rss` |

---

## 📊 Analiz Teorileri

| Teori | Odak |
|-------|------|
| 🔴 **Realizm** | Güç, ulusal çıkar, güvenlik ikilemi |
| 🔵 **Liberalizm** | Kurumlar, işbirliği, demokratik barış |
| 🟢 **İnşacılık** | Kimlik, normlar, söylem |
| 🟣 **Eleştirel Teori** | Hegemonya, eşitsizlik, kurtuluş |
| 🟡 **İngiliz Okulu** | Uluslararası toplum, normlar, düzen |

---

## 📄 Lisans

MIT — Özgürce kullan, fork'la, geliştir.
