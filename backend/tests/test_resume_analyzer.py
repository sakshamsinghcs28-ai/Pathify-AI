"""Comprehensive Test Suite for Pathify-AI Resume Analyzer & Intelligence Studio.

Tests:
1. Text extraction from plain text and structured documents
2. Contact info, section, and skills parsing
3. Four-Pillar ATS scoring calculation (Formatting, Content, Skills, Experience)
4. Job Description matching and keyword overlap calculation
5. AI Improvement Studio: XYZ formula rewrites and impact scoring
6. In-memory ReportLab PDF report generation
7. FastAPI router endpoints (/api/resume/upload, /analyze, /rewrite-bullet, /history, /download)
8. Multi-tenant data isolation and ownership enforcement
"""

import io
import sys
import uuid
from pathlib import Path
import httpx
from httpx import ASGITransport

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.services.resume_parser import (
    extract_bullet_points,
    extract_contact_info,
    extract_raw_text,
    extract_skills_from_text,
    parse_resume,
    split_into_sections,
)
from backend.app.services.resume_improver import (
    analyze_bullet_impact,
    generate_xyz_rewrites,
    generate_professional_summary,
)
from backend.app.services.resume_service import (
    analyze_resume_data,
    compute_jd_match,
    score_pillar_content,
    score_pillar_formatting,
)
from backend.app.services.resume_pdf_service import generate_resume_pdf_report
from database.models import CareerRole, ResumeAnalysis


SAMPLE_RESUME_TEXT = """
Alex Morgan
San Francisco, CA | alex.morgan@example.com | (555) 019-2834
https://linkedin.com/in/alexmorgan | https://github.com/alexmorgan

PROFESSIONAL SUMMARY
Results-driven Full-Stack Software Engineer with 4 years of experience architecting and deploying responsive web applications and scalable backend APIs using React, Node.js, and PostgreSQL.

TECHNICAL SKILLS
Languages & Frameworks: JavaScript, TypeScript, Python, HTML & CSS, React, Node.js, Express.js
Databases & Cloud: PostgreSQL, MongoDB, Redis, Docker, Git & GitHub, AWS (S3, EC2)

PROFESSIONAL EXPERIENCE
Senior Frontend Developer | TechCorp Solutions | 2022 - Present
• Architected dynamic single-page applications in React and TypeScript, boosting page rendering speed by 42%.
• Engineered reusable component library used across 8 engineering teams, reducing sprint cycle times by 20%.
• Integrated RESTful APIs with Redis caching, supporting over 25,000 daily active users with 99.9% uptime.
• Responsible for code reviews and mentored 4 junior developers on modern state management.

Software Engineer | Alpha Innovations | 2020 - 2022
• Developed modular microservices using Node.js and Express.js, decreasing query latency by 35%.
• Designed normalized PostgreSQL schemas with indexing, handling 1.5M transactions monthly.
• Worked on deployment pipelines utilizing Docker and GitHub Actions for continuous integration.

EDUCATION
Bachelor of Science in Computer Science | University of California, Berkeley | 2016 - 2020
"""


def test_resume_parser_extraction():
    """Verify section splitting, contact extraction, and skill identification."""
    parsed = parse_resume(SAMPLE_RESUME_TEXT)

    # 1. Contact Info
    contact = parsed["contact"]
    assert contact["email"] == "alex.morgan@example.com"
    assert "linkedin.com/in/alexmorgan" in contact["linkedin"]
    assert "github.com/alexmorgan" in contact["github"]
    assert contact["name"] == "Alex Morgan"

    # 2. Section Splitting
    sections = parsed["sections"]
    assert len(sections["experience"]) > 50
    assert len(sections["skills"]) > 30
    assert len(sections["education"]) > 20

    # 3. Bullets Extraction
    bullets = parsed["bullets"]
    assert len(bullets) >= 5
    assert any("42%" in b for b in bullets)

    # 4. Extracted Skills
    skills = parsed["extracted_skills"]
    assert "React" in skills
    assert "Node.js" in skills
    assert "PostgreSQL" in skills
    assert "JavaScript" in skills
    print("  ✓ Resume parser extraction test passed.")


def test_bullet_impact_and_xyz_rewriter():
    """Verify impact scoring and Google-style XYZ formula rewrites."""
    # Strong bullet with action verb and metric
    strong_bullet = "Architected dynamic single-page applications in React, boosting page rendering speed by 42%."
    analysis_strong = analyze_bullet_impact(strong_bullet)
    assert analysis_strong["starts_with_action_verb"] is True
    assert analysis_strong["has_metrics"] is True
    assert analysis_strong["score"] >= 80

    # Weak bullet with passive buzzwords
    weak_bullet = "Responsible for code reviews and worked on bugs."
    analysis_weak = analyze_bullet_impact(weak_bullet)
    assert len(analysis_weak["detected_buzzwords"]) >= 1
    assert analysis_weak["score"] < 70

    # XYZ Rewrites
    rewrites = generate_xyz_rewrites(weak_bullet, target_role="Full-Stack Developer")
    assert len(rewrites) >= 2
    assert any("Engineered" in r["text"] or "Architected" in r["text"] for r in rewrites)
    assert "formula_breakdown" in rewrites[0]
    print("  ✓ Bullet impact & XYZ rewriter test passed.")


def test_four_pillar_scoring():
    """Verify individual scoring of all four ATS pillars."""
    parsed = parse_resume(SAMPLE_RESUME_TEXT)

    # 1. Formatting pillar
    f_score, f_data = score_pillar_formatting(parsed)
    assert 70 <= f_score <= 100
    assert len(f_data["findings"]) >= 3

    # 2. Content pillar
    c_score, c_data = score_pillar_content(parsed)
    assert 50 <= c_score <= 100
    assert c_data["action_verb_percentage"] >= 40

    # 3. Overall 4-pillar analysis
    analysis = analyze_resume_data(
        raw_text=SAMPLE_RESUME_TEXT,
        filename="Alex_Morgan_Resume.pdf",
        file_size_bytes=len(SAMPLE_RESUME_TEXT),
        file_type="application/pdf",
    )
    assert 60 <= analysis["overall_score"] <= 100
    assert len(analysis["improvement_recommendations"]) >= 1
    print("  ✓ Four-pillar scoring test passed.")


def test_job_description_keyword_matching():
    """Verify keyword overlap calculation and missing requirements isolation."""
    sample_jd = """
    We are seeking a Senior Full-Stack Engineer with strong expertise in React, TypeScript,
    Node.js, PostgreSQL, Docker, and AWS Kubernetes. You will design distributed microservices,
    optimize database performance, and collaborate with product teams. Experience with GraphQL
    and CI/CD automation is highly desirable.
    """
    jd_match = compute_jd_match(SAMPLE_RESUME_TEXT, sample_jd)
    assert jd_match["match_percentage"] is not None
    assert jd_match["match_percentage"] > 40.0
    assert "react" in [k.lower() for k in jd_match["matched_keywords"]]
    print(f"  ✓ JD Keyword Match confirmed: {jd_match['match_percentage']}% overlap.")


def test_pdf_report_generation():
    """Verify ReportLab PDF generation compiles without errors."""
    mock_record = ResumeAnalysis(
        id=uuid.uuid4(),
        filename="Alex_Morgan_Resume.pdf",
        file_size_bytes=len(SAMPLE_RESUME_TEXT),
        file_type="application/pdf",
        raw_text=SAMPLE_RESUME_TEXT,
        parsed_data=parse_resume(SAMPLE_RESUME_TEXT),
        overall_score=84.5,
        pillar_formatting_score=90.0,
        pillar_content_score=82.0,
        pillar_skills_score=85.0,
        pillar_experience_score=80.0,
        matched_skills=[{"name": "React"}, {"name": "Node.js"}, {"name": "PostgreSQL"}],
        missing_skills=[{"name": "Docker", "priority": "High"}, {"name": "Kubernetes", "priority": "Medium"}],
        jd_match_percentage=78.5,
        improvement_recommendations=[
            {"pillar": "Content", "priority": "High", "text": "Quantify outcomes in your second role."},
        ],
    )
    pdf_bytes = generate_resume_pdf_report(mock_record)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
    print(f"  ✓ In-memory PDF report generated successfully ({len(pdf_bytes)} bytes).")


async def test_fastapi_resume_endpoints():
    """Verify end-to-end FastAPI endpoint integration via in-process ASGI client."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register test user
        test_uid = uuid.uuid4().hex[:6]
        user_email = f"resume_tester_{test_uid}@example.com"
        reg_res = await client.post("/api/auth/register", json={
            "full_name": f"Resume Tester {test_uid}",
            "email": user_email,
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
        })
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Upload text resume
        files = {
            "file": ("test_resume.txt", SAMPLE_RESUME_TEXT.encode("utf-8"), "text/plain"),
        }
        upload_res = await client.post("/api/resume/upload", headers=headers, files=files)
        assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
        upload_data = upload_res.json()
        assert upload_data["success"] is True
        assert upload_data["parsed"]["contact"]["email"] == "alex.morgan@example.com"

        # 3. Analyze resume
        analyze_payload = {
            "filename": "test_resume.txt",
            "raw_text": SAMPLE_RESUME_TEXT,
            "role_id": "role-1",  # Full-Stack Developer
            "job_description": "Looking for a Full-Stack React and Node.js developer.",
        }
        analyze_res = await client.post("/api/resume/analyze", headers=headers, json=analyze_payload)
        assert analyze_res.status_code == 200, f"Analyze failed: {analyze_res.text}"
        analyze_data = analyze_res.json()
        assert analyze_data["overall_score"] > 50
        analysis_id = analyze_data["id"]
        assert analysis_id is not None

        # 4. Bullet Rewrite Endpoint
        rewrite_res = await client.post("/api/resume/rewrite-bullet", headers=headers, json={
            "bullet_text": "Responsible for managing web servers and fixing bugs.",
            "target_role": "Full-Stack Developer",
        })
        assert rewrite_res.status_code == 200
        assert len(rewrite_res.json()["rewrites"]) >= 2

        # 5. History Endpoint
        history_res = await client.get("/api/resume/history", headers=headers)
        assert history_res.status_code == 200
        history_data = history_res.json()
        assert history_data["total"] >= 1
        assert history_data["history"][0]["id"] == analysis_id

        # 6. Single History Detail
        detail_res = await client.get(f"/api/resume/history/{analysis_id}", headers=headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == analysis_id

        # 7. Download PDF Report
        pdf_res = await client.get(f"/api/resume/report/{analysis_id}/download", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF-")

        # 8. Sync to Roadmap
        sync_res = await client.post(f"/api/resume/sync-to-roadmap/{analysis_id}", headers=headers)
        assert sync_res.status_code == 200
        assert sync_res.json()["success"] is True
        assert "roadmap_id" in sync_res.json()

        # 9. Cross-user isolation check: User B cannot access User A's resume
        user_b_res = await client.post("/api/auth/register", json={
            "full_name": "User B",
            "email": f"user_b_{test_uid}@example.com",
            "password": "PasswordB123!",
            "confirm_password": "PasswordB123!",
        })
        token_b = user_b_res.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        blocked_detail = await client.get(f"/api/resume/history/{analysis_id}", headers=headers_b)
        assert blocked_detail.status_code == 404, "User B should not access User A's resume"

        blocked_pdf = await client.get(f"/api/resume/report/{analysis_id}/download", headers=headers_b)
        assert blocked_pdf.status_code == 404, "User B should not download User A's PDF"

        # 10. Delete History
        del_res = await client.delete(f"/api/resume/history/{analysis_id}", headers=headers)
        assert del_res.status_code == 200

        # Verify deleted
        verify_del = await client.get(f"/api/resume/history/{analysis_id}", headers=headers)
        assert verify_del.status_code == 404

    print("  ✓ All 10 FastAPI router endpoints verified with full RBAC isolation.")


async def main():
    print("=" * 80)
    print("RUNNING PATHIFY-AI RESUME ANALYZER MODULE TEST SUITE")
    print("=" * 80)
    test_resume_parser_extraction()
    test_bullet_impact_and_xyz_rewriter()
    test_four_pillar_scoring()
    test_job_description_keyword_matching()
    test_pdf_report_generation()
    await test_fastapi_resume_endpoints()
    print("=" * 80)
    print(">>> ALL RESUME ANALYZER TESTS PASSED SUCCESSFULLY! <<<")
    print("=" * 80)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
