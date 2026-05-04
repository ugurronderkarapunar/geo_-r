"""
src/pdf_report.py
Generates a professional PDF analysis report using ReportLab.
Premium feature — called only when the user has a premium role.
"""

import logging
from datetime import datetime
from io import BytesIO

logger = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, HRFlowable, KeepTogether,
    )
    _RL_OK = True
except ImportError:
    _RL_OK = False
    logger.error("ReportLab not installed — PDF export unavailable.")


# ── Colour palette ────────────────────────────────────────────────────────────
C_DARK   = HexColor("#1A1A2E") if _RL_OK else None
C_ACCENT = HexColor("#3D5AFE") if _RL_OK else None
C_LIGHT  = HexColor("#F8F9FA") if _RL_OK else None
C_MID    = HexColor("#DEE2E6") if _RL_OK else None
C_GREY   = HexColor("#6C757D") if _RL_OK else None

THEORY_COLORS = {
    "Realism":        "#E74C3C",
    "Liberalism":     "#3498DB",
    "Constructivism": "#2ECC71",
    "Critical Theory":"#9B59B6",
    "English School": "#F39C12",
}

SCORE_META = [
    ("realism_score",        "Realism"),
    ("liberalism_score",     "Liberalism"),
    ("constructivism_score", "Constructivism"),
    ("critical_theory_score","Critical Theory"),
    ("english_school_score", "English School"),
]


def generate_pdf_report(articles: list[dict], username: str = "User") -> BytesIO | None:
    """
    Build a PDF report for the given list of article dicts.
    Returns a BytesIO buffer ready for st.download_button, or None on failure.
    """
    if not _RL_OK:
        logger.error("ReportLab unavailable — cannot generate PDF.")
        return None

    try:
        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2.2 * cm,
            rightMargin=2.2 * cm,
            title="Geopolitical Pulse — Analysis Report",
            author=f"Generated for {username}",
        )

        styles = getSampleStyleSheet()

        # ── Custom paragraph styles ──
        s_title = ParagraphStyle(
            "GPTitle",
            parent=styles["Title"],
            fontSize=26,
            textColor=C_DARK,
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )
        s_sub = ParagraphStyle(
            "GPSub",
            parent=styles["Normal"],
            fontSize=10,
            textColor=C_GREY,
            spaceAfter=16,
            alignment=TA_CENTER,
        )
        s_section = ParagraphStyle(
            "GPSection",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=C_DARK,
            spaceBefore=18,
            spaceAfter=6,
            fontName="Helvetica-Bold",
            borderPad=4,
        )
        s_body = ParagraphStyle(
            "GPBody",
            parent=styles["Normal"],
            fontSize=10,
            textColor=HexColor("#333333"),
            spaceAfter=6,
            leading=15,
            alignment=TA_JUSTIFY,
        )
        s_meta = ParagraphStyle(
            "GPMeta",
            parent=styles["Normal"],
            fontSize=8.5,
            textColor=C_GREY,
            spaceAfter=4,
            leading=12,
        )
        s_caption = ParagraphStyle(
            "GPCaption",
            parent=styles["Normal"],
            fontSize=8,
            textColor=C_GREY,
            alignment=TA_CENTER,
            spaceAfter=6,
        )

        story = []

        # ── Cover header ──
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("🌍 Geopolitical Pulse", s_title))
        story.append(
            Paragraph(
                f"Analysis Report &nbsp;·&nbsp; "
                f"{datetime.utcnow().strftime('%B %d, %Y  %H:%M UTC')}",
                s_sub,
            )
        )
        story.append(Paragraph(f"Prepared for: <b>{username}</b>", s_sub))
        story.append(
            HRFlowable(width="100%", thickness=2, color=C_DARK, spaceAfter=10)
        )

        # ── Summary row ──
        summary_data = [
            [
                Paragraph(f"<b>{len(articles)}</b><br/>Articles", s_sub),
                Paragraph(
                    f"<b>{sum(1 for a in articles if a.get('analysis_note'))}</b><br/>Analysed",
                    s_sub,
                ),
                Paragraph(
                    f"<b>{datetime.utcnow().strftime('%d %b %Y')}</b><br/>Report Date",
                    s_sub,
                ),
            ]
        ]
        summary_tbl = Table(summary_data, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
        summary_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT),
                    ("BOX", (0, 0), (-1, -1), 0.5, C_MID),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, C_MID),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(summary_tbl)
        story.append(Spacer(1, 0.5 * cm))

        # ── Articles ──
        for idx, art in enumerate(articles, 1):
            title   = art.get("title", "Untitled")
            source  = art.get("source", "—")
            pub     = (art.get("published_at") or "")[:10]
            url     = art.get("url", "")
            note    = art.get("analysis_note", "")

            # Compute sorted scores
            scored = sorted(
                [(label, art.get(key, 0)) for key, label in SCORE_META],
                key=lambda x: x[1],
                reverse=True,
            )

            block = []

            # Article heading
            block.append(
                Paragraph(f"{idx}. {title}", s_section)
            )
            block.append(
                Paragraph(
                    f"Source: <b>{source}</b>  &nbsp;|&nbsp;  Published: <b>{pub or '—'}</b>",
                    s_meta,
                )
            )
            if url:
                block.append(Paragraph(f'<link href="{url}">{url[:80]}</link>', s_meta))

            # Score table
            tbl_data = [
                [
                    Paragraph("<b>Theory</b>", s_meta),
                    Paragraph("<b>Score</b>", s_meta),
                    Paragraph("<b>Visual</b>", s_meta),
                ]
            ]
            for theory_name, score in scored:
                bar_filled  = "█" * (score // 10)
                bar_empty   = "░" * (10 - score // 10)
                bar_str     = bar_filled + bar_empty
                color       = THEORY_COLORS.get(theory_name, "#999")
                tbl_data.append(
                    [
                        Paragraph(f'<font color="{color}"><b>{theory_name}</b></font>', s_meta),
                        Paragraph(f"<b>{score}</b>/100", s_meta),
                        Paragraph(
                            f'<font color="{color}">{bar_str}</font>', s_meta
                        ),
                    ]
                )
            score_table = Table(
                tbl_data,
                colWidths=[4.5 * cm, 2 * cm, 5.5 * cm],
            )
            score_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), C_DARK),
                        ("TEXTCOLOR", (0, 0), (-1, 0), white),
                        ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE",  (0, 0), (-1, -1), 8.5),
                        ("ALIGN",     (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_LIGHT, white]),
                        ("GRID",      (0, 0), (-1, -1), 0.4, C_MID),
                        ("PADDING",   (0, 0), (-1, -1), 7),
                    ]
                )
            )
            block.append(Spacer(1, 0.25 * cm))
            block.append(score_table)
            block.append(Spacer(1, 0.2 * cm))

            # Analysis note
            if note:
                block.append(Paragraph("<b>Theoretical Analysis</b>", s_body))
                block.append(
                    Paragraph(note, s_body)
                )

            block.append(
                HRFlowable(width="100%", thickness=0.5, color=C_MID, spaceAfter=6)
            )

            story.append(KeepTogether(block[:4]))  # title + meta always together
            story.extend(block[4:])

        # ── Footer ──
        story.append(Spacer(1, 0.6 * cm))
        story.append(
            Paragraph(
                "<i>This report was generated automatically by Geopolitical Pulse. "
                "Scores reflect the theoretical relevance of each IR framework "
                "to the news item, as assessed by GPT-4o-mini.</i>",
                s_caption,
            )
        )

        doc.build(story)
        buf.seek(0)
        return buf

    except Exception as e:
        logger.error(f"generate_pdf_report error: {e}")
        return None
