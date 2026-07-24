import csv
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_csv(session: dict, activity: dict, students: list[dict], responses: list[dict]) -> str:
    students_by_id = {s["id"]: s for s in students}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Name", "Grade", "Section", "Submitted At", "Correct", "Answer"])
    for r in responses:
        student = students_by_id.get(r["student_id"], {})
        writer.writerow([
            student.get("name", "Unknown"),
            student.get("grade", ""),
            student.get("section", ""),
            r["submitted_at"],
            r.get("correct", ""),
            r.get("answer", ""),
        ])
    return output.getvalue()


def build_pdf(session: dict, activity: dict, students: list[dict], responses: list[dict]) -> bytes:
    students_by_id = {s["id"]: s for s in students}
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    elements = [
        Paragraph("LISM AI Classroom Report", styles["Title"]),
        Paragraph(f"Activity: {activity['title']}", styles["Heading2"]),
        Paragraph(f"Session Code: {session['code']}", styles["Normal"]),
        Paragraph(f"Students joined: {len(students)} | Responses: {len(responses)}", styles["Normal"]),
        Spacer(1, 16),
    ]

    data = [["Student", "Grade", "Section", "Correct", "Answer"]]
    for r in responses:
        student = students_by_id.get(r["student_id"], {})
        data.append([
            student.get("name", "Unknown"),
            str(student.get("grade", "")),
            student.get("section", ""),
            "Yes" if r.get("correct") else ("No" if r.get("correct") is False else "-"),
            str(r.get("answer", ""))[:60],
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
