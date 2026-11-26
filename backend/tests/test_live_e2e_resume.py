"""Live End-to-End Verification Test for Pathify-AI Resume Analyzer Module.

Executes live HTTP requests directly against http://127.0.0.1:5000:
1. Verifies Server Health (/api/health)
2. Verifies Frontend Static HTML (/ and /index.html) contains all Resume Analyzer navigation and UI components
3. Verifies Frontend JavaScript (/js/resume.js) is served correctly
4. Registers and authenticates a fresh test user
5. Tests Resume Upload endpoint (/api/resume/upload) with sample resume
6. Tests Four-Pillar ATS Analysis endpoint (/api/resume/analyze)
7. Tests AI Improvement Studio Bullet Point Rewriter (/api/resume/rewrite-bullet)
8. Tests Analysis History retrieval (/api/resume/history)
9. Tests Downloadable PDF Report compilation (/api/resume/report/{id}/download)
10. Tests Sync Missing Skills to Personalized Career Roadmap (/api/resume/sync-to-roadmap/{id})
"""

import sys
import uuid
import httpx

LIVE_SERVER_URL = "http://127.0.0.1:5000"

SAMPLE_RESUME = """
Jordan Taylor
Denver, CO | jordan.taylor@example.com | (555) 234-5678
https://linkedin.com/in/jordantaylor | https://github.com/jordantaylor

PROFESSIONAL SUMMARY
Dynamic Full-Stack Software Engineer with 3+ years of experience building resilient cloud applications with React, Node.js, and PostgreSQL.

SKILLS
Technical Skills: JavaScript, TypeScript, Python, React, Node.js, PostgreSQL, Docker, Git, REST APIs

PROFESSIONAL EXPERIENCE
Software Engineer | CloudScale Systems | 2021 - Present
• Designed and shipped 14 responsive React web components, boosting user engagement by 28%.
• Optimized backend microservices with Node.js and PostgreSQL, decreasing API response times by 32%.
• Built automated CI/CD deployment workflows using Docker and GitHub Actions with 99.9% build reliability.

EDUCATION
B.S. in Computer Science | University of Colorado | 2017 - 2021
"""

def main():
    print("=" * 80)
    print("STARTING LIVE END-TO-END RESUME ANALYZER VERIFICATION ON PORT 5000")
    print("=" * 80)

    with httpx.Client(base_url=LIVE_SERVER_URL, timeout=15.0) as client:
        # 1. Health Check
        print("\n[Step 1] Checking Live Server Health...")
        health_res = client.get("/api/health")
        assert health_res.status_code == 200, f"Health check failed: {health_res.status_code}"
        print("  ✓ Live backend health verified:", health_res.json()["message"])

        # 2. Frontend HTML Verification
        print("\n[Step 2] Verifying Frontend HTML Integration at /index.html...")
        html_res = client.get("/")
        assert html_res.status_code == 200
        html = html_res.text

        # Verify Navigation Items
        assert 'id="nav-resume"' in html, "Missing #nav-resume in desktop navigation"
        assert "switchTab('resume')" in html, "Missing switchTab('resume') in navigation bar"
        print("  ✓ Desktop 'Resume' navigation button verified (#nav-resume).")

        # Verify Hero Action CTA
        assert "Scan Resume ATS" in html, "Missing 'Scan Resume ATS' CTA on Dashboard"
        print("  ✓ Dashboard Hero 'Scan Resume ATS' CTA verified.")

        # Verify Section Views
        assert 'id="view-resume"' in html, "Missing #view-resume section in DOM"
        assert 'id="resume-dropzone"' in html, "Missing #resume-dropzone in DOM"
        assert 'id="resume-file-input"' in html, "Missing #resume-file-input in DOM"
        assert 'id="btn-analyze-resume"' in html, "Missing #btn-analyze-resume in DOM"
        assert 'id="resume-results-container"' in html, "Missing #resume-results-container in DOM"
        assert 'id="resume-score-circle-progress"' in html, "Missing circular score gauge in DOM"
        assert 'id="ai-improvement-studio"' in html, "Missing #ai-improvement-studio in DOM"
        assert 'id="resume-extraction-studio"' in html, "Missing #resume-extraction-studio in DOM"
        assert 'id="resume-history-section"' in html, "Missing #resume-history-section in DOM"
        print("  ✓ All 10 Google Stitch Resume Analyzer components present in live index.html.")

        # 3. Static JS Asset Verification
        print("\n[Step 3] Verifying Static JavaScript Serving (/js/resume.js)...")
        js_res = client.get("/js/resume.js")
        assert js_res.status_code == 200, f"Failed to fetch /js/resume.js: {js_res.status_code}"
        assert "startResumeAnalysis" in js_res.text
        assert "renderResumeAnalysis" in js_res.text
        assert "improveBulletWithAi" in js_res.text
        assert "downloadResumePdfReport" in js_res.text
        print(f"  ✓ js/resume.js verified ({len(js_res.text)} bytes).")

        # 4. Authenticate Test User
        print("\n[Step 4] Registering test user for authenticated workflows...")
        uid = uuid.uuid4().hex[:6]
        user_email = f"e2e_resume_{uid}@pathify.test"
        reg_res = client.post("/api/auth/register", json={
            "full_name": f"E2E Resume User {uid}",
            "email": user_email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        })
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
        auth_data = reg_res.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  ✓ Test user registered & authenticated: {user_email}")

        # 5. Upload Resume
        print("\n[Step 5] Uploading resume document (/api/resume/upload)...")
        files = {
            "file": ("Jordan_Taylor_Resume.txt", SAMPLE_RESUME.encode("utf-8"), "text/plain"),
        }
        upload_res = client.post("/api/resume/upload", headers=headers, files=files)
        assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
        upload_data = upload_res.json()
        assert upload_data["success"] is True
        assert upload_data["parsed"]["contact"]["email"] == "jordan.taylor@example.com"
        assert len(upload_data["parsed"]["extracted_skills"]) >= 5
        print(f"  ✓ Resume parsed: Extracted {len(upload_data['parsed']['extracted_skills'])} skills, email: {upload_data['parsed']['contact']['email']}")

        # 6. Analyze Resume
        print("\n[Step 6] Running Four-Pillar ATS Analysis & Scoring (/api/resume/analyze)...")
        analyze_payload = {
            "filename": "Jordan_Taylor_Resume.txt",
            "raw_text": SAMPLE_RESUME,
            "role_id": "role-1",  # Full-Stack Developer
            "job_description": "Seeking a Full-Stack Engineer with React, Node.js, Docker, and PostgreSQL experience.",
        }
        analyze_res = client.post("/api/resume/analyze", headers=headers, json=analyze_payload)
        assert analyze_res.status_code == 200, f"Analysis failed: {analyze_res.text}"
        analysis = analyze_res.json()
        analysis_id = analysis["id"]
        assert analysis["overall_score"] > 60
        print(f"  ✓ Four-Pillar Analysis complete: Overall ATS Score = {analysis['overall_score']}/100")
        print(f"    - Formatting Score: {analysis['pillar_formatting_score']}/100")
        print(f"    - Content Score:    {analysis['pillar_content_score']}/100")
        print(f"    - Skills Score:     {analysis['pillar_skills_score']}/100")
        print(f"    - Experience Score: {analysis['pillar_experience_score']}/100")
        jd_pct = analysis.get("jd_match_percentage") or analysis.get("jd_match", {}).get("match_percentage")
        print(f"    - JD Keyword Match: {jd_pct}%")

        # 7. AI Improvement Studio Bullet Point Rewriter
        print("\n[Step 7] Testing AI Bullet Point Improvement Studio (/api/resume/rewrite-bullet)...")
        bullet_payload = {
            "bullet_text": "Responsible for developing React components and improving website performance.",
            "target_role": "Full-Stack Developer",
        }
        rewrite_res = client.post("/api/resume/rewrite-bullet", headers=headers, json=bullet_payload)
        assert rewrite_res.status_code == 200, f"AI rewrite failed: {rewrite_res.text}"
        rewrite_data = rewrite_res.json()
        assert rewrite_data["success"] is True
        assert len(rewrite_data["rewrites"]) >= 2
        print(f"  ✓ AI Bullet Rewrites generated: {len(rewrite_data['rewrites'])} suggestions.")
        for idx, rw in enumerate(rewrite_data["rewrites"], 1):
            text_val = rw.get("text") or rw.get("rewritten")
            print(f"    [{idx}] {text_val}")

        # 8. Resume Analysis History
        print("\n[Step 8] Verifying Resume History persistence (/api/resume/history)...")
        history_res = client.get("/api/resume/history", headers=headers)
        assert history_res.status_code == 200
        hist_data = history_res.json()
        assert hist_data["total"] >= 1
        assert hist_data["history"][0]["id"] == analysis_id
        print(f"  ✓ Verified history persistence in PostgreSQL: Found {hist_data['total']} saved analysis.")

        # 9. Downloadable PDF Report
        print("\n[Step 9] Generating & Downloading Official PDF Report (/api/resume/report/{id}/download)...")
        pdf_res = client.get(f"/api/resume/report/{analysis_id}/download", headers=headers)
        assert pdf_res.status_code == 200, f"PDF report failed: {pdf_res.status_code}"
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF-")
        print(f"  ✓ Official ReportLab PDF Report compiled and streamed ({len(pdf_res.content)} bytes).")

        # 10. Sync Missing Skills to Roadmap
        print("\n[Step 10] Testing One-Click Missing Skills Sync to Roadmap (/api/resume/sync-to-roadmap/{id})...")
        sync_res = client.post(f"/api/resume/sync-to-roadmap/{analysis_id}", headers=headers)
        assert sync_res.status_code == 200, f"Roadmap sync failed: {sync_res.text}"
        sync_data = sync_res.json()
        assert sync_data["success"] is True
        print(f"  ✓ Missing skills synced to Roadmap: {sync_data['message']}")

    print("\n" + "=" * 80)
    print(">>> ALL 10 LIVE SERVER INTEGRATION STEPS PASSED 100% SUCCESSFULLY! <<<")
    print("=" * 80)

if __name__ == "__main__":
    main()
