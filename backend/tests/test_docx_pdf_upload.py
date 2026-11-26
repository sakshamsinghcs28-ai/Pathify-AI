"""Comprehensive Verification Test for DOCX and PDF Resume Uploads & Analysis.

Tests:
1. Genuine binary DOCX generation, upload, and 4-pillar analysis.
2. Genuine binary PDF generation, upload, and 4-pillar analysis.
3. Analysis History retrieval for the user.
4. Official ReportLab PDF Report compilation and download.
5. Verification that file_type with 70+ chars (e.g. DOCX MIME type) persists without error.
"""

import io
import uuid
import docx
import httpx
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

LIVE_SERVER_URL = "http://127.0.0.1:5000"


def generate_sample_docx() -> bytes:
    doc = docx.Document()
    doc.add_heading("Saksham Singh", level=1)
    doc.add_paragraph("isaksham14@gmail.com | 7050738361 | linkedin.com/in/saksham-singh")
    doc.add_heading("Professional Summary", level=2)
    doc.add_paragraph("Computer Science undergraduate with expertise in Python, SQL, and Data Analytics.")
    doc.add_heading("Skills", level=2)
    doc.add_paragraph("Python, SQL, Prompt Engineering, Excel, Problem-Solving")
    doc.add_heading("Projects", level=2)
    doc.add_paragraph("Sales Analytics Dashboard: Created dynamic charts to compare revenue by city, boosting reporting efficiency by 30%.")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def generate_sample_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 750, "Jordan Taylor")
    c.drawString(72, 735, "jordan.taylor@example.com | (555) 234-5678 | linkedin.com/in/jordantaylor")
    c.drawString(72, 700, "PROFESSIONAL SUMMARY")
    c.drawString(72, 685, "Experienced Full-Stack Developer with 4 years building web apps using React, Node.js, and PostgreSQL.")
    c.drawString(72, 650, "SKILLS")
    c.drawString(72, 635, "JavaScript, TypeScript, Python, React, Node.js, PostgreSQL, Docker, Git")
    c.drawString(72, 600, "EXPERIENCE")
    c.drawString(72, 585, "Senior Software Engineer | Tech Systems | 2020 - Present")
    c.drawString(72, 570, "- Architected 15 React modules increasing rendering performance by 35%.")
    c.drawString(72, 555, "- Optimized PostgreSQL database queries reducing API latency by 40%.")
    c.showPage()
    c.save()
    return buf.getvalue()


def main():
    print("=" * 80)
    print("TESTING DOCX AND PDF RESUME UPLOADS AND 4-PILLAR ANALYSIS")
    print("=" * 80)

    docx_bytes = generate_sample_docx()
    pdf_bytes = generate_sample_pdf()

    with httpx.Client(base_url=LIVE_SERVER_URL, timeout=20.0) as client:
        # Register test user
        uid = uuid.uuid4().hex[:6]
        user_email = f"doc_pdf_tester_{uid}@pathify.test"
        reg = client.post("/api/auth/register", json={
            "full_name": f"Docx/PDF Tester {uid}",
            "email": user_email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        })
        assert reg.status_code == 201, f"Registration failed: {reg.text}"
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  ✓ User authenticated: {user_email}")

        # -------------------------------------------------------------
        # 1. DOCX Test
        # -------------------------------------------------------------
        print("\n[Test 1] Testing DOCX Resume Upload & Analysis...")
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        files_docx = {"file": ("Saksham_Singh_Resume.docx", docx_bytes, docx_mime)}
        up_docx = client.post("/api/resume/upload", headers=headers, files=files_docx)
        assert up_docx.status_code == 200, f"DOCX Upload failed: {up_docx.text}"
        docx_data = up_docx.json()
        assert docx_data["file_type"] == docx_mime
        print(f"  ✓ DOCX Upload successful: file_type length = {len(docx_data['file_type'])} chars")

        an_docx_payload = {
            "filename": "Saksham_Singh_Resume.docx",
            "raw_text": docx_data["raw_text"],
            "file_size_bytes": docx_data["file_size_bytes"],
            "file_type": docx_data["file_type"],
            "role_id": "role-2",  # Data Analyst
            "job_description": "Seeking a Data Analyst skilled in Python, SQL, and Excel reporting.",
        }
        an_docx = client.post("/api/resume/analyze", headers=headers, json=an_docx_payload)
        assert an_docx.status_code == 200, f"DOCX Analysis failed: {an_docx.text}"
        an_docx_data = an_docx.json()
        assert an_docx_data["overall_score"] > 0
        docx_id = an_docx_data["id"]
        print(f"  ✓ DOCX Analysis successful: Overall Score = {an_docx_data['overall_score']}/100 (ID: {docx_id})")

        # -------------------------------------------------------------
        # 2. PDF Test
        # -------------------------------------------------------------
        print("\n[Test 2] Testing PDF Resume Upload & Analysis...")
        files_pdf = {"file": ("Jordan_Taylor_Resume.pdf", pdf_bytes, "application/pdf")}
        up_pdf = client.post("/api/resume/upload", headers=headers, files=files_pdf)
        assert up_pdf.status_code == 200, f"PDF Upload failed: {up_pdf.text}"
        pdf_data = up_pdf.json()
        assert pdf_data["file_type"] == "application/pdf"
        print("  ✓ PDF Upload successful.")

        an_pdf_payload = {
            "filename": "Jordan_Taylor_Resume.pdf",
            "raw_text": pdf_data["raw_text"],
            "file_size_bytes": pdf_data["file_size_bytes"],
            "file_type": pdf_data["file_type"],
            "role_id": "role-1",  # Full-Stack Developer
            "job_description": "Looking for a Senior Full-Stack Engineer with React, Node.js, and PostgreSQL experience.",
        }
        an_pdf = client.post("/api/resume/analyze", headers=headers, json=an_pdf_payload)
        assert an_pdf.status_code == 200, f"PDF Analysis failed: {an_pdf.text}"
        an_pdf_data = an_pdf.json()
        assert an_pdf_data["overall_score"] > 0
        pdf_id = an_pdf_data["id"]
        print(f"  ✓ PDF Analysis successful: Overall Score = {an_pdf_data['overall_score']}/100 (ID: {pdf_id})")

        # -------------------------------------------------------------
        # 3. History Test
        # -------------------------------------------------------------
        print("\n[Test 3] Verifying Scan History Persistence...")
        hist_res = client.get("/api/resume/history", headers=headers)
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert hist_data["total"] >= 2
        print(f"  ✓ Found {hist_data['total']} saved analyses in PostgreSQL history.")

        # -------------------------------------------------------------
        # 4. Downloadable PDF Report
        # -------------------------------------------------------------
        print("\n[Test 4] Verifying PDF Report Download...")
        rep_res = client.get(f"/api/resume/report/{pdf_id}/download", headers=headers)
        assert rep_res.status_code == 200
        assert rep_res.headers["content-type"] == "application/pdf"
        assert rep_res.content.startswith(b"%PDF-")
        print(f"  ✓ Official ReportLab PDF Report compiled and streamed ({len(rep_res.content)} bytes).")

    print("\n" + "=" * 80)
    print(">>> ALL DOCX AND PDF UPLOAD AND ANALYSIS TESTS PASSED! <<<")
    print("=" * 80)


if __name__ == "__main__":
    main()
