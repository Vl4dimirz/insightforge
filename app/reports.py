"""
Report generation — turn a data profile (and optional AI analysis) into a
downloadable Excel workbook or a polished PDF. File generation is a classic,
sellable Python skill.
"""

import io
import re
from html import escape

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def _columns_frame(profile: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "column": c["name"],
                "type": c["dtype"],
                "nulls": c["nulls"],
                "null %": c["null_pct"],
                "unique": c["unique"],
                "mean": (c["numeric"] or {}).get("mean"),
            }
            for c in profile["column_profiles"]
        ]
    )


def build_excel(source: str, profile: dict) -> bytes:
    """A two-sheet workbook: a summary and the full column profile."""
    buf = io.BytesIO()
    summary = pd.DataFrame(
        {
            "metric": ["source", "rows", "columns", "duplicate_rows"],
            "value": [source, profile["rows"], profile["columns"], profile["duplicate_rows"]],
        }
    )
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        summary.to_excel(xl, sheet_name="Summary", index=False)
        _columns_frame(profile).to_excel(xl, sheet_name="Columns", index=False)
    return buf.getvalue()


def _md_to_rl(line: str) -> str:
    """Tiny markdown→reportlab conversion: **bold** and *bullets* into safe markup."""
    line = escape(line)
    line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
    line = re.sub(r"^\s*[\*\-]\s+", "• ", line)
    line = re.sub(r"^\s*#+\s*", "", line)
    return line


def build_pdf(source: str, profile: dict, insights: str | None = None) -> bytes:
    """A clean, monochrome PDF: header, key metrics, column table, optional AI analysis."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=16 * mm, rightMargin=16 * mm, title="InsightForge Report")
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=colors.black, fontSize=22, spaceAfter=4)
    meta = ParagraphStyle("meta", parent=styles["Normal"], textColor=colors.grey, fontSize=9, spaceAfter=12)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=colors.black, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=15)

    story = [
        Paragraph("InsightForge — Data Report", h1),
        Paragraph(f"Source: {escape(source)}", meta),
        Paragraph(
            f"<b>{profile['rows']:,}</b> rows &nbsp;·&nbsp; <b>{profile['columns']}</b> columns "
            f"&nbsp;·&nbsp; <b>{profile['duplicate_rows']}</b> duplicate rows",
            body,
        ),
        Spacer(1, 10),
        Paragraph("Column profile", h2),
    ]

    df = _columns_frame(profile)
    table_data = [list(df.columns)] + [
        [("-" if pd.isna(v) else v) for v in row] for row in df.itertuples(index=False)
    ]
    table = Table(table_data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.96, 0.96, 0.96)]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(table)

    if insights:
        story.append(Paragraph("AI Analysis", h2))
        for line in insights.split("\n"):
            if line.strip():
                story.append(Paragraph(_md_to_rl(line), body))
                story.append(Spacer(1, 3))

    doc.build(story)
    return buf.getvalue()
