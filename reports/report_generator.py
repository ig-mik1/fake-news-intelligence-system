from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from datetime import datetime
import os

from analytics.monitoring import load_recent_news, compute_monitoring_stats


REPORT_FOLDER = "reports/generated"


def generate_daily_report():

    os.makedirs(REPORT_FOLDER, exist_ok=True)

    df = load_recent_news()
    stats = compute_monitoring_stats(df)

    filename = f"{REPORT_FOLDER}/report_{datetime.now().date()}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph("AI News Intelligence Report", styles["Title"])
    )

    elements.append(Spacer(1, 20))

    elements.append(
        Paragraph(f"Date: {datetime.now()}", styles["Normal"])
    )

    elements.append(Spacer(1, 20))

    if stats:
        elements.append(
            Paragraph(f"Total Articles: {stats['total_articles']}", styles["Normal"])
        )

        elements.append(
            Paragraph(f"Average Article Length: {stats['avg_length']}", styles["Normal"])
        )

        elements.append(Spacer(1, 20))

        elements.append(
            Paragraph("Top News Sources:", styles["Heading2"])
        )

        for src, count in stats["top_sources"].items():
            elements.append(
                Paragraph(f"{src}: {count}", styles["Normal"])
            )

    doc.build(elements)

    return filename