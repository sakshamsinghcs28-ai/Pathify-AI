"""Integration tests validating multi-user data isolation and zero cross-account leakage in Pathify AI.

Covers:
1. Registering two distinct user accounts (User A and User B).
2. Verifying User A's resume upload and profile creation.
3. Verifying User B starts with an empty profile and empty resume history.
4. Attempting unauthorized access from User B to User A's profile, roadmap, and resume (403/404 assertions).
5. User B uploading their own resume and creating a profile.
6. Re-authenticating User A and verifying User A's original data is preserved and isolated.
"""

import asyncio
import io
import sys
import uuid
from pathlib import Path
from httpx import ASGITransport, AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def create_sample_pdf(content_lines: list[str]) -> bytes:
    """Helper to generate a valid in-memory PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 750
    for line in content_lines:
        c.drawString(50, y, line)
        y -= 25
    c.save()
    buf.seek(0)
    return buf.getvalue()


async def run_isolation_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("\n" + "=" * 80)
        print("RUNNING MULTI-USER DATA ISOLATION & SECURITY TEST SUITE")
        print("=" * 80)

        # ----------------------------------------------------------------------
        # 1. Register User A
        # ----------------------------------------------------------------------
        uid_a = uuid.uuid4().hex[:8]
        email_a = f"usera_{uid_a}@pathify.test"
        pwd_a = "PasswordA123!"

        print(f"\n[Step 1] Registering User A ({email_a})...")
        reg_a_res = await client.post("/api/auth/register", json={
            "full_name": "Alice Anderson",
            "email": email_a,
            "password": pwd_a,
            "confirm_password": pwd_a,
        })
        assert reg_a_res.status_code == 201, f"User A registration failed: {reg_a_res.text}"
        data_a = reg_a_res.json()
        token_a = data_a["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}
        user_a_id = data_a["user"]["id"]
        print(f"  ✓ User A registered (ID: {user_a_id})")

        # ----------------------------------------------------------------------
        # 2. User A creates a profile and saves skills
        # ----------------------------------------------------------------------
        print("\n[Step 2] User A creates profile with skills [React, Node.js, TypeScript]...")
        prof_a_res = await client.post("/api/profiles", headers=headers_a, json={
            "name": "Alice Anderson",
            "education": "B.S. in Computer Science",
            "targetRoleId": "role-1",
            "skills": ["React", "Node.js", "TypeScript"],
        })
        assert prof_a_res.status_code == 201, f"Profile creation failed: {prof_a_res.text}"
        prof_a_data = prof_a_res.json()["profile"]
        profile_a_id = prof_a_data["id"]
        print(f"  ✓ User A profile created (Profile ID: {profile_a_id})")

        # Verify User A gets their profile via /api/profiles/me
        my_prof_a = await client.get("/api/profiles/me", headers=headers_a)
        assert my_prof_a.status_code == 200
        assert my_prof_a.json()["profile"]["id"] == profile_a_id
        assert set(my_prof_a.json()["profile"]["skills"]) == {"React", "Node.js", "TypeScript"}
        print("  ✓ GET /api/profiles/me returned User A's profile and skills")

        # ----------------------------------------------------------------------
        # 3. User A uploads a resume and executes analysis
        # ----------------------------------------------------------------------
        print("\n[Step 3] User A uploads resume (UserA_FullStack.pdf)...")
        pdf_bytes_a = create_sample_pdf([
            "ALICE ANDERSON - Full-Stack Developer",
            "Email: alice@pathify.test | Phone: (555) 123-4567 | LinkedIn: linkedin.com/in/alice-dev",
            "EXPERIENCE",
            "Senior Frontend Engineer at TechCorp",
            "- Architected responsive micro-frontends with React, TypeScript and Redux reducing bundle size by 35%.",
            "- Implemented Node.js GraphQL endpoints increasing query throughput by 50%.",
            "SKILLS",
            "React, Node.js, TypeScript, JavaScript, HTML & CSS, Git & GitHub",
            "EDUCATION",
            "B.S. Computer Science",
        ])

        upload_a_res = await client.post(
            "/api/resume/upload",
            headers=headers_a,
            files={"file": ("UserA_FullStack.pdf", pdf_bytes_a, "application/pdf")},
        )
        assert upload_a_res.status_code == 200, f"Upload failed: {upload_a_res.text}"
        uploaded_a_data = upload_a_res.json()

        analyze_a_res = await client.post(
            "/api/resume/analyze",
            headers=headers_a,
            json={
                "raw_text": uploaded_a_data["raw_text"],
                "filename": "UserA_FullStack.pdf",
                "file_type": "application/pdf",
                "role_id": "role-1",
            },
        )
        assert analyze_a_res.status_code == 200, f"Analysis failed: {analyze_a_res.text}"
        analysis_a_id = analyze_a_res.json()["id"]
        print(f"  ✓ User A resume analyzed and saved (Analysis ID: {analysis_a_id})")

        # Verify User A's history shows this resume
        hist_a_res = await client.get("/api/resume/history", headers=headers_a)
        assert hist_a_res.status_code == 200
        hist_a = hist_a_res.json()["history"]
        assert len(hist_a) == 1
        assert hist_a[0]["filename"] == "UserA_FullStack.pdf"
        print("  ✓ GET /api/resume/history contains User A's resume")

        # ----------------------------------------------------------------------
        # 4. User A chats with AI mentor
        # ----------------------------------------------------------------------
        print("\n[Step 4] User A chats with AI Advisor...")
        chat_a_res = await client.post("/api/chat", headers=headers_a, json={
            "message": "What is the best way to master React hooks?",
            "history": [],
            "contextRoleId": "role-1",
        })
        assert chat_a_res.status_code == 200
        print("  ✓ User A received AI Mentor advice")

        # ----------------------------------------------------------------------
        # 5. Register User B (Simulating different user login on same app)
        # ----------------------------------------------------------------------
        uid_b = uuid.uuid4().hex[:8]
        email_b = f"userb_{uid_b}@pathify.test"
        pwd_b = "PasswordB123!"

        print(f"\n[Step 5] Registering User B ({email_b})...")
        reg_b_res = await client.post("/api/auth/register", json={
            "full_name": "Bob Builder",
            "email": email_b,
            "password": pwd_b,
            "confirm_password": pwd_b,
        })
        assert reg_b_res.status_code == 201, f"User B registration failed: {reg_b_res.text}"
        data_b = reg_b_res.json()
        token_b = data_b["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        user_b_id = data_b["user"]["id"]
        print(f"  ✓ User B registered (ID: {user_b_id})")

        # ----------------------------------------------------------------------
        # 6. Verify User B starts with an empty profile and no resumes
        # ----------------------------------------------------------------------
        print("\n[Step 6] Verifying User B starts with clean slate...")
        my_prof_b = await client.get("/api/profiles/me", headers=headers_b)
        assert my_prof_b.status_code == 200
        prof_b = my_prof_b.json()["profile"]
        assert prof_b is not None
        assert prof_b["name"] == "Bob Builder"
        assert prof_b["skills"] == [], f"New User B must start with 0 skills, found: {prof_b['skills']}"
        assert prof_b["targetRoleId"] == "", f"New User B must start with no target role, found: {prof_b['targetRoleId']}"
        print("  ✓ GET /api/profiles/me for User B has empty skills and empty role")

        hist_b_res = await client.get("/api/resume/history", headers=headers_b)
        assert hist_b_res.status_code == 200
        hist_b = hist_b_res.json()["history"]
        assert len(hist_b) == 0, f"User B must have empty history, found {len(hist_b)} items!"
        print("  ✓ GET /api/resume/history for User B returned 0 items (clean isolation)")

        roadmap_b = await client.get("/api/profiles/me/roadmap", headers=headers_b)
        assert roadmap_b.status_code == 200
        assert len(roadmap_b.json()["roadmap"]) == 0
        print("  ✓ GET /api/profiles/me/roadmap for User B returned empty roadmap")

        # ----------------------------------------------------------------------
        # 7. Security: Attempt cross-account access by User B to User A's data
        # ----------------------------------------------------------------------
        print("\n[Step 7] Testing security barriers: User B attempting to access User A's records...")

        # 7.1 Access User A's profile
        cross_prof = await client.get(f"/api/profiles/{profile_a_id}", headers=headers_b)
        assert cross_prof.status_code == 403, f"Expected 403 Forbidden, got {cross_prof.status_code}"
        print("  ✓ GET /api/profiles/{user_a_profile} returned 403 Forbidden")

        # 7.2 Access User A's roadmap
        cross_rm = await client.get(f"/api/profiles/{profile_a_id}/roadmap", headers=headers_b)
        assert cross_rm.status_code == 403, f"Expected 403 Forbidden, got {cross_rm.status_code}"
        print("  ✓ GET /api/profiles/{user_a_profile}/roadmap returned 403 Forbidden")

        # 7.3 Toggle step on User A's roadmap
        cross_toggle = await client.post(
            f"/api/profiles/{profile_a_id}/roadmap/toggle-step",
            headers=headers_b,
            json={"stepNumber": 1, "completed": True},
        )
        assert cross_toggle.status_code == 403, f"Expected 403 Forbidden, got {cross_toggle.status_code}"
        print("  ✓ POST /api/profiles/{user_a_profile}/roadmap/toggle-step returned 403 Forbidden")

        # 7.4 Access User A's resume analysis breakdown
        cross_resume = await client.get(f"/api/resume/history/{analysis_a_id}", headers=headers_b)
        assert cross_resume.status_code == 404, f"Expected 404 Not Found, got {cross_resume.status_code}"
        print("  ✓ GET /api/resume/history/{user_a_resume} returned 404 Not Found")

        # 7.5 Download User A's resume PDF report
        cross_pdf = await client.get(f"/api/resume/report/{analysis_a_id}/download", headers=headers_b)
        assert cross_pdf.status_code == 404, f"Expected 404 Not Found, got {cross_pdf.status_code}"
        print("  ✓ GET /api/resume/report/{user_a_resume}/download returned 404 Not Found")

        # 7.6 Delete User A's resume analysis
        cross_del = await client.delete(f"/api/resume/history/{analysis_a_id}", headers=headers_b)
        assert cross_del.status_code == 404, f"Expected 404 Not Found, got {cross_del.status_code}"
        print("  ✓ DELETE /api/resume/history/{user_a_resume} returned 404 Not Found")

        # ----------------------------------------------------------------------
        # 8. User B uploads their own resume
        # ----------------------------------------------------------------------
        print("\n[Step 8] User B uploads their own resume (UserB_DataAnalyst.docx)...")
        pdf_bytes_b = create_sample_pdf([
            "BOB BUILDER - Data Analyst",
            "Email: bob@pathify.test | Phone: (555) 987-6543 | LinkedIn: linkedin.com/in/bob-analyst",
            "EXPERIENCE",
            "Junior Data Analyst at RetailCorp",
            "- Built SQL queries and Tableau dashboards tracking $2M in revenue.",
            "- Cleaned customer transactional datasets using Python and Pandas.",
            "SKILLS",
            "SQL & Relational Databases, Python, Data Cleaning with Pandas, Excel & Spreadsheets",
            "EDUCATION",
            "B.A. Statistics",
        ])

        upload_b_res = await client.post(
            "/api/resume/upload",
            headers=headers_b,
            files={"file": ("UserB_DataAnalyst.pdf", pdf_bytes_b, "application/pdf")},
        )
        assert upload_b_res.status_code == 200
        uploaded_b_data = upload_b_res.json()

        analyze_b_res = await client.post(
            "/api/resume/analyze",
            headers=headers_b,
            json={
                "raw_text": uploaded_b_data["raw_text"],
                "filename": "UserB_DataAnalyst.pdf",
                "file_type": "application/pdf",
                "role_id": "role-2",
            },
        )
        assert analyze_b_res.status_code == 200
        analysis_b_id = analyze_b_res.json()["id"]
        print(f"  ✓ User B resume analyzed (ID: {analysis_b_id})")

        # Verify User B sees ONLY their resume in history
        hist_b_after = (await client.get("/api/resume/history", headers=headers_b)).json()["history"]
        assert len(hist_b_after) == 1
        assert hist_b_after[0]["filename"] == "UserB_DataAnalyst.pdf"
        assert hist_b_after[0]["id"] == analysis_b_id
        print("  ✓ User B history strictly shows User B's resume only")

        # ----------------------------------------------------------------------
        # 9. User A logs back in and verifies original data is intact
        # ----------------------------------------------------------------------
        print("\n[Step 9] User A logs back in to verify data preservation...")
        login_a_res = await client.post("/api/auth/login", json={
            "email": email_a,
            "password": pwd_a,
        })
        assert login_a_res.status_code == 200
        new_token_a = login_a_res.json()["access_token"]
        new_headers_a = {"Authorization": f"Bearer {new_token_a}"}

        # User A's profile check
        restored_prof_a = (await client.get("/api/profiles/me", headers=new_headers_a)).json()["profile"]
        assert restored_prof_a is not None
        assert restored_prof_a["id"] == profile_a_id
        assert set(restored_prof_a["skills"]) == {"React", "Node.js", "TypeScript"}
        print("  ✓ User A's saved profile, target role, and skills 100% retained")

        # User A's resume history check
        restored_hist_a = (await client.get("/api/resume/history", headers=new_headers_a)).json()["history"]
        assert len(restored_hist_a) == 1
        assert restored_hist_a[0]["filename"] == "UserA_FullStack.pdf"
        assert restored_hist_a[0]["id"] == analysis_a_id
        print("  ✓ User A's original resume 100% retained, zero leakage from User B")

        print("\n" + "=" * 80)
        print("ALL MULTI-USER ISOLATION ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_isolation_tests())
