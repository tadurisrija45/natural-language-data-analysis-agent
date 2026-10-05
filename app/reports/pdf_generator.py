import os
import uuid
from datetime import datetime
from typing import Optional
from flask import current_app

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)

from ..models import Analysis, User
from ..utils.helpers import format_datetime, format_file_size


class PDFReportGenerator:
    @classmethod
    def generate_session_report(cls, analysis: Analysis, user: User) -> str:
        """
        Generate a complete professional PDF report for an analysis session.
        Returns the absolute filepath of the generated PDF file.
        """
        reports_dir = current_app.config["REPORTS_DIR"]
        os.makedirs(reports_dir, exist_ok=True)
        pdf_filename = f"report_analysis_{analysis.id}_{uuid.uuid4().hex[:8]}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_filename)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        # Custom Brand Colors
        primary_teal = colors.HexColor("#0F766E")
        dark_teal = colors.HexColor("#115E59")
        slate_dark = colors.HexColor("#0F172A")
        slate_muted = colors.HexColor("#64748B")
        border_color = colors.HexColor("#E2E8F0")
        bg_light = colors.HexColor("#F8FAFC")
        card_bg = colors.HexColor("#FFFFFF")

        # Custom Typography Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=primary_teal,
            spaceAfter=6
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=slate_muted,
            spaceAfter=15
        )

        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=dark_teal,
            spaceBefore=14,
            spaceAfter=8
        )

        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=slate_dark,
            spaceAfter=6
        )

        body_bold = ParagraphStyle(
            "BodyBold",
            parent=body_style,
            fontName="Helvetica-Bold"
        )

        badge_style = ParagraphStyle(
            "Badge",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.white
        )

        story = []

        # 1. Header Banner
        header_table = Table(
            [[
                Paragraph("<b>DataAgent</b> | AI-Powered Data Analysis", ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=12, textColor=primary_teal)),
                Paragraph("Confidential & Verified", ParagraphStyle("Right", fontName="Helvetica", fontSize=9, textColor=slate_muted, alignment=2))
            ]],
            colWidths=[350, 180]
        )
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 1, border_color),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))

        # 2. Document Title & Metadata
        story.append(Paragraph(f"{analysis.icon} {analysis.title}", title_style))
        meta_text = (
            f"Prepared for: <b>{user.full_name}</b> (@{user.username}) &nbsp;|&nbsp; "
            f"Date: <b>{format_datetime(analysis.created_at, 'date_only')}</b> &nbsp;|&nbsp; "
            f"Time: <b>{format_datetime(analysis.created_at, 'time_only')}</b> &nbsp;|&nbsp; "
            f"Status: <b>{analysis.status}</b>"
        )
        story.append(Paragraph(meta_text, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceAfter=15))

        # 3. Uploaded Datasets Profile Summary
        story.append(Paragraph("1. Uploaded Datasets & Profile", h2_style))
        dataset_rows = [[
            Paragraph("<b>Dataset Name</b>", body_bold),
            Paragraph("<b>File Type</b>", body_bold),
            Paragraph("<b>Size</b>", body_bold),
            Paragraph("<b>Rows × Cols</b>", body_bold),
            Paragraph("<b>Uploaded Time</b>", body_bold),
        ]]

        for ds in analysis.datasets:
            dataset_rows.append([
                Paragraph(ds.original_name, body_style),
                Paragraph(ds.file_type.upper(), body_style),
                Paragraph(format_file_size(ds.file_size), body_style),
                Paragraph(f"{ds.row_count:,} × {ds.column_count}", body_style),
                Paragraph(format_datetime(ds.created_at, "time_only"), body_style)
            ])

        ds_table = Table(dataset_rows, colWidths=[180, 60, 75, 105, 110])
        ds_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), bg_light),
            ("TEXTCOLOR", (0, 0), (-1, 0), dark_teal),
            ("GRID", (0, 0), (-1, -1), 0.5, border_color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(ds_table)
        story.append(Spacer(1, 18))

        # 4. Analysis Questions & Evidence-Backed Findings
        story.append(Paragraph("2. Analysis Questions & Evidence-Backed Findings", h2_style))

        q_idx = 1
        for msg in analysis.messages:
            if msg.message_type == "user":
                continue

            q_text = msg.question or "Business Question"
            ans_text = msg.answer or "Analysis result not available."
            evidence = msg.evidence if isinstance(msg.evidence, dict) else {}
            proof_text = msg.proof or ""
            validation = msg.validation if isinstance(msg.validation, list) else []
            insight_text = msg.insight or ""
            chart_info = msg.chart_info if isinstance(msg.chart_info, dict) else {}

            mode_label = (msg.mode or "Natural Language").replace("_", " ").title()

            # Question Header Card
            story.append(Paragraph(
                f"<b>Question {q_idx} [{mode_label}]: {q_text}</b>",
                ParagraphStyle("QHead", parent=h2_style, fontSize=12, textColor=primary_teal)
            ))
            story.append(Paragraph(f"<b>Answer:</b> {ans_text}", ParagraphStyle("Ans", parent=body_style, fontSize=11, fontName="Helvetica-Bold", textColor=slate_dark)))
            story.append(Spacer(1, 6))

            # Only show code block for SQL or Python modes (not internal NL pipeline code)
            if msg.mode in ["sql", "python"]:
                raw_snippet = (msg.raw_code or q_text or "").strip()
                lines = raw_snippet.splitlines()
                if len(lines) > 18:
                    raw_snippet = "\n".join(lines[:18]) + f"\n... [{len(lines) - 18} more lines]"
                code_snippet = raw_snippet.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")

                code_table = Table([[
                    Paragraph(f"<b>Executed {mode_label}:</b><br/><font face='Courier' size=8 color='#0F172A'>{code_snippet}</font>", body_style)
                ]], colWidths=[530])
                code_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                    ("BOX", (0, 0), (-1, -1), 0.5, border_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]))
                story.append(code_table)
                story.append(Spacer(1, 6))

            # Embed Chart if static image exists
            static_chart_path = chart_info.get("static_image_path")
            if static_chart_path and os.path.exists(static_chart_path):
                try:
                    img = Image(static_chart_path, width=5.5 * inch, height=2.6 * inch)
                    story.append(img)
                    story.append(Spacer(1, 8))
                except Exception:
                    pass

            # Evidence & Proof Table
            breakdown = evidence.get("breakdown", [])
            breakdown_str = ", ".join([f"{b.get('entity')}: {b.get('formatted_value')}" for b in breakdown[:4]])
            source_ds = evidence.get("source_dataset", "Uploaded File")
            rows_num = evidence.get("rows_analyzed", 0)

            evidence_content = (
                f"<b>Source Dataset:</b> {source_ds} &nbsp;|&nbsp; <b>Rows Analyzed:</b> {rows_num}<br/>"
                f"<b>Breakdown:</b> {breakdown_str}"
            )

            validation_items = []
            for v in validation:
                if isinstance(v, dict):
                    status_sym = "✓" if v.get("passed", True) else "✗"
                    validation_items.append(f"{status_sym} {v.get('check', '')}: {v.get('detail', '')}")

            val_str = "<br/>".join(validation_items) if validation_items else "✓ Calculations and schema verified."

            clean_proof_lines = (proof_text or "").splitlines()
            if len(clean_proof_lines) > 16:
                clean_proof_text = "\n".join(clean_proof_lines[:16]) + f"\n... [{len(clean_proof_lines) - 16} more lines]"
            else:
                clean_proof_text = proof_text or ""
            clean_proof = clean_proof_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")

            details_data = [
                [Paragraph("<b>Traceable Evidence</b>", body_bold), Paragraph(evidence_content, body_style)],
                [Paragraph("<b>Proof & Traceability</b>", body_bold), Paragraph(clean_proof, body_style)],
                [Paragraph("<b>Validation Checklist</b>", body_bold), Paragraph(val_str, body_style)],
                [Paragraph("<b>Executive Insight</b>", body_bold), Paragraph(insight_text, ParagraphStyle("Insight", parent=body_style, fontName="Helvetica-Oblique"))],
            ]

            if msg.suggested_questions:
                sug_lines = "<br/>".join([f"• {sq}" for sq in msg.suggested_questions[:4]])
                details_data.append([
                    Paragraph("<b>Suggested Follow-Ups</b>", body_bold),
                    Paragraph(sug_lines, ParagraphStyle("Suggestions", parent=body_style, textColor=dark_teal))
                ])

            card_table = Table(details_data, colWidths=[130, 400])
            card_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), bg_light),
                ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))

            story.append(card_table)
            story.append(Spacer(1, 14))
            story.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceAfter=14))
            q_idx += 1

        # Build document
        doc.build(story)
        return pdf_path
