"""
scripts/update.py
─────────────────
GitHub Actions ve manuel CLI kullanımı için birleşik güncelleme scripti.

Kullanım:
    python scripts/update.py                    # fetch + analyze (default)
    python scripts/update.py --fetch-only       # sadece RSS çek
    python scripts/update.py --analyze-only     # sadece analiz et
    python scripts/update.py --limit 10         # max 10 makale analiz et
"""

import argparse
import logging
import sys
import os

# ── Repo kökünü Python yoluna ekle ───────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("error.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Geopolitical Pulse — Updater")
    parser.add_argument("--fetch-only",   action="store_true", help="Sadece RSS çek")
    parser.add_argument("--analyze-only", action="store_true", help="Sadece analiz et")
    parser.add_argument("--limit", type=int, default=20, help="Analiz edilecek maks. makale")
    args = parser.parse_args()

    do_fetch   = not args.analyze_only
    do_analyze = not args.fetch_only

    print("=" * 55)
    print("  🌍  Geopolitical Pulse — Auto Update")
    print("=" * 55)

    if do_fetch:
        print("\n📡  RSS beslemeleri alınıyor…")
        try:
            from src.fetch_feeds import fetch_and_store_feeds
            n = fetch_and_store_feeds()
            print(f"  ✅  {n} yeni makale eklendi.")
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            print(f"  ❌  Hata: {e}")
            if args.fetch_only:
                sys.exit(1)

    if do_analyze:
        print(f"\n🤖  AI analizi çalıştırılıyor (limit={args.limit})…")
        try:
            from src.analyzer import run_analysis
            n = run_analysis(limit=args.limit)
            print(f"  ✅  {n} makale analiz edildi.")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            print(f"  ❌  Hata: {e}")
            sys.exit(1)

    print("\n✅  Güncelleme tamamlandı.")
    print("=" * 55)


if __name__ == "__main__":
    main()
