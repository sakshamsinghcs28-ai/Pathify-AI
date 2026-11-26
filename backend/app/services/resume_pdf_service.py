"""Downloadable PDF Intelligence Report Generator.

Uses ReportLab to generate a publication-quality ATS Resume Analysis Report
in memory without requiring external headless browser binaries.
"""

import io
from datetime import datetime, timezone
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.models import ResumeAnalysis


def generate_resume_pdf_report(analysis: ResumeAnalysis) -> bytes:
    """Generate a styled PDF report for a given resume analysis record."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom Brand Styles
    title_style = ParagraphStyle(
        "BrandTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#4f46e5"),  # Indigo brand
    )
    subtitle_style = ParagraphStyle(
        "BrandSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )
    bold_body = ParagraphStyle(
        "BoldReportBody",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("Pathify.AI — Resume Intelligence & ATS Audit Report", title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')} | Target Role: {analysis.role.title if analysis.role else 'General Technical Pathway'}",
        subtitle_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4f46e5"), spaceAfter=12))

    # 2. Executive Scorecard Table
    score = analysis.overall_score
    score_color = "#10b981" if score >= 80 else ("#f59e0b" if score >= 60 else "#ef4444")
    score_rating = "Excellent ATS Match" if score >= 80 else ("Moderate Alignment" if score >= 60 else "Action Required")

    score_html = f"<font size='28' color='{score_color}'><b>{score:.1f}</b></font><br/><font size='9' color='#64748b'>/ 100 Overall Score ({score_rating})</font>"
    meta_html = (
        f"<b>Candidate:</b> {analysis.parsed_data.get('contact', {}).get('name') or 'Identified Candidate'}<br/>"
        f"<b>Document:</b> {analysis.filename} ({analysis.file_type})<br/>"
        f"<b>Email:</b> {analysis.parsed_data.get('contact', {}).get('email') or 'Not Detected'}<br/>"
        f"<b>Job Match:</b> {f'{analysis.jd_match_percentage:.1f}%' if analysis.jd_match_percentage is not None else 'N/A'}"
    )

    score_card_data = [
        [Paragraph(score_html, body_style), Paragraph(meta_html, body_style)],
    ]
    score_table = Table(score_card_data, colWidths=[2.2 * inch, 5.0 * inch])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 12))

    # 3. Four-Pillar Breakdown
    elements.append(Paragraph("Four-Pillar Performance Diagnostics", section_heading))

    pillars_data = [
        [
            Paragraph("<b>Diagnostic Pillar</b>", bold_body),
            Paragraph("<b>Score</b>", bold_body),
            Paragraph("<b>Evaluation & Key Findings</b>", bold_body),
        ],
        [
            Paragraph("1. ATS Compatibility & Formatting", bold_body),
            Paragraph(f"<b>{analysis.pillar_formatting_score:.1f}%</b>", body_style),
            Paragraph(f"Standard section detection, parseable structure, and contact completeness.", body_style),
        ],
        [
            Paragraph("2. Content & Impact", bold_body),
            Paragraph(f"<b>{analysis.pillar_content_score:.1f}%</b>", body_style),
            Paragraph(f"Action verbs, quantifiable results, and absence of passive clichés.", body_style),
        ],
        [
            Paragraph("3. Skills Alignment", bold_body),
            Paragraph(f"<b>{analysis.pillar_skills_score:.1f}%</b>", body_style),
            Paragraph(f"Matched {len(analysis.matched_skills)} skills against role requirements; {len(analysis.missing_skills)} gaps.", body_style),
        ],
        [
            Paragraph("4. Career Trajectory & Relevance", bold_body),
            Paragraph(f"<b>{analysis.pillar_experience_score:.1f}%</b>", body_style),
            Paragraph(f"Work history depth, timeline clarity, and domain relevance.", body_style),
        ],
    ]
    pillar_table = Table(pillars_data, colWidths=[2.2 * inch, 0.9 * inch, 4.1 * inch])
    pillar_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(pillar_table)
    elements.append(Spacer(1, 14))

    # 4. Matched Skills vs Missing Skills
    elements.append(Paragraph("Skills Coverage & Deficit Analysis", section_heading))
    matched_names = [s.get("name") for s in analysis.matched_skills if s.get("name")]
    missing_names = [f"{s.get('name')} ({s.get('priority', 'High')})" for s in analysis.missing_skills if s.get("name")]

    skills_data = [
        [
            Paragraph("<b>Identified Skills in Resume</b>", bold_body),
            Paragraph("<b>Missing / In-Demand Requirements</b>", bold_body),
        ],
        [
            Paragraph(", ".join(matched_names) if matched_names else "No core skills extracted.", body_style),
            Paragraph(", ".join(missing_names) if missing_names else "All requirements matched!", body_style),
        ],
    ]
    skills_table = Table(skills_data, colWidths=[3.6 * inch, 3.6 * inch])
    skills_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(skills_table)
    elements.append(Spacer(1, 14))

    # 5. Improvement Recommendations
    elements.append(Paragraph("Actionable Recommendations for Maximum ATS Impact", section_heading))
    recs = analysis.improvement_recommendations or []
    if recs:
        for idx, r in enumerate(recs, 1):
            pillar_name = r.get("pillar", "General")
            priority = r.get("priority", "Medium")
            rec_text = r.get("text", "")
            rec_p = Paragraph(f"<b>[{priority} Priority • {pillar_name}]</b> {rec_text}", body_style)
            elements.append(rec_p)
            elements.append(Spacer(1, 4))
    else:
        elements.append(Paragraph("Your resume exhibits strong ATS characteristics with no critical flags detected.", body_style))

    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=8))
    elements.append(Paragraph(
        "Pathify-AI Career Intelligence • Automated Evaluation • Sync with Personalized Roadmaps at localhost:5000",
        subtitle_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
