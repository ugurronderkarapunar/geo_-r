"""
src/database.py
SQLite layer for Geopolitical Pulse.
All public functions return plain dicts (or lists thereof) so callers
never have to touch sqlite3.Row objects directly.
"""

import sqlite3
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("GP_DB_PATH", "geopolitical_pulse.db")


# ── Connection ────────────────────────────────────────────────────────────────
def get_connection() -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        raise


# ── Schema ────────────────────────────────────────────────────────────────────
def init_db() -> bool:
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                url         TEXT    UNIQUE NOT NULL,
                title       TEXT    NOT NULL,
                source      TEXT    NOT NULL,
                published_at TEXT,
                summary     TEXT,
                fetched_at  TEXT    NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id            INTEGER UNIQUE NOT NULL,
                realism_score         INTEGER DEFAULT 0,
                liberalism_score      INTEGER DEFAULT 0,
                constructivism_score  INTEGER DEFAULT 0,
                critical_theory_score INTEGER DEFAULT 0,
                english_school_score  INTEGER DEFAULT 0,
                analysis_note         TEXT,
                created_at            TEXT NOT NULL,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)

        # Index for fast time-range queries
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_fetched
            ON articles(fetched_at)
        """)

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"DB init error: {e}")
        return False


# ── Writes ────────────────────────────────────────────────────────────────────
def insert_article(
    url: str,
    title: str,
    source: str,
    published_at: str | None,
    summary: str,
    fetched_at: str,
) -> tuple[int | None, bool]:
    """
    Returns (article_id, is_new).
    is_new=False when the URL already existed.
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """
            INSERT OR IGNORE INTO articles
                (url, title, source, published_at, summary, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (url, title, source, published_at, summary, fetched_at),
        )
        is_new = c.rowcount > 0
        if is_new:
            article_id = c.lastrowid
        else:
            c.execute("SELECT id FROM articles WHERE url = ?", (url,))
            row = c.fetchone()
            article_id = row["id"] if row else None
        conn.commit()
        conn.close()
        return article_id, is_new
    except Exception as e:
        logger.error(f"insert_article error (url={url[:60]}): {e}")
        return None, False


def insert_analysis(article_id: int, scores: dict, analysis_note: str) -> bool:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO analyses
                (article_id, realism_score, liberalism_score,
                 constructivism_score, critical_theory_score,
                 english_school_score, analysis_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                int(scores.get("realism", 0)),
                int(scores.get("liberalism", 0)),
                int(scores.get("constructivism", 0)),
                int(scores.get("critical_theory", 0)),
                int(scores.get("english_school", 0)),
                analysis_note,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"insert_analysis error (article_id={article_id}): {e}")
        return False


# ── Reads ─────────────────────────────────────────────────────────────────────
def get_recent_articles_with_analyses(hours: int = 24) -> list[dict]:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT
                a.id, a.url, a.title, a.source,
                a.published_at, a.summary, a.fetched_at,
                an.realism_score, an.liberalism_score,
                an.constructivism_score, an.critical_theory_score,
                an.english_school_score, an.analysis_note
            FROM articles a
            LEFT JOIN analyses an ON a.id = an.article_id
            WHERE datetime(a.fetched_at) >= datetime('now', ?)
            ORDER BY a.fetched_at DESC
            """,
            (f"-{hours} hours",),
        )
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_recent_articles_with_analyses error: {e}")
        return []


def get_article_by_id(article_id: int) -> dict | None:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT
                a.id, a.url, a.title, a.source,
                a.published_at, a.summary, a.fetched_at,
                an.realism_score, an.liberalism_score,
                an.constructivism_score, an.critical_theory_score,
                an.english_school_score, an.analysis_note
            FROM articles a
            LEFT JOIN analyses an ON a.id = an.article_id
            WHERE a.id = ?
            """,
            (article_id,),
        )
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"get_article_by_id error (id={article_id}): {e}")
        return None


def get_unanalyzed_articles(limit: int = 20) -> list[dict]:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT a.id, a.url, a.title, a.source, a.summary
            FROM articles a
            LEFT JOIN analyses an ON a.id = an.article_id
            WHERE an.id IS NULL
            ORDER BY a.fetched_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"get_unanalyzed_articles error: {e}")
        return []


def get_db_stats() -> dict:
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) AS n FROM articles")
        articles = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) AS n FROM analyses")
        analyses = c.fetchone()["n"]
        conn.close()
        return {"articles": articles, "analyses": analyses}
    except Exception as e:
        logger.error(f"get_db_stats error: {e}")
        return {"articles": 0, "analyses": 0}
