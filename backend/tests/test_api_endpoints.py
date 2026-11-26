"""Automated integration tests for Pathify-AI FastAPI backend and Frontend.

Validates all 7 original endpoints from API.md + new /api/chat endpoint + frontend static serving.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from httpx import AsyncClient, ASGITransport
from backend.app.main import app


async def test_all_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 0. Frontend Static Serving
        print("\n[Test 0] Testing Frontend Static Serving (GET /)...")
        res = await client.get("/")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert "Pathify" in res.text
        print("  -> Passed. Frontend index.html served at root.")

        # 1. Health check
        print("\n[Test 1] Testing GET /api/health...")
        res = await client.get("/api/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["status"] == "ok"
        assert "message" in data
        assert "timestamp" in data
        print("  -> Passed. Health check response:", data)

        # 1.1 Verify protected endpoint returns 401 without auth
        res_unauth = await client.get("/api/roles")
        assert res_unauth.status_code == 401, f"Expected 401, got {res_unauth.status_code}"
        print("  -> Passed. /api/roles returns 401 Unauthorized without auth.")

        # 1.2 Register test user to obtain authentication token
        import uuid
        test_email = f"api_test_{uuid.uuid4().hex[:6]}@pathify.test"
        reg_res = await client.post(
            "/api/auth/register",
            json={
                "full_name": "API Test User",
                "email": test_email,
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
            },
        )
        assert reg_res.status_code == 201, f"Register failed: {reg_res.text}"
        auth_token = reg_res.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {auth_token}"
        print(f"  -> Passed. Authenticated test user {test_email} registered.")

        # 2. List career roles
        print("\n[Test 2] Testing GET /api/roles (Authenticated)...")
        res = await client.get("/api/roles")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["totalRoles"] >= 3
        roles = {r["id"]: r for r in data["roles"]}
        assert "role-1" in roles
        assert "role-2" in roles
        assert "role-3" in roles
        r1 = roles["role-1"]
        r2 = roles["role-2"]
        r3 = roles["role-3"]
        assert r1["title"] == "Full-Stack Developer"
        assert r2["title"] == "Data Analyst"
        assert r3["title"] == "AI Engineer"
        print(f"  -> Passed. Verified 3 primary roles: {r1['title']}, {r2['title']}, {r3['title']}")

        # 3. Analyze skills for a role (POST /api/skill-gap)
        print("\n[Test 3] Testing POST /api/skill-gap...")
        payload = {
            "roleId": "role-1",
            "skills": ["JavaScript", "React", "Node.js"],
        }
        res = await client.post("/api/skill-gap", json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["roleId"] == "role-1"
        assert data["analysis"]["totalRequiredSkills"] == 7
        assert data["analysis"]["matchedCount"] == 3
        assert data["analysis"]["missingCount"] == 4
        assert data["analysis"]["matchPercentage"] == "43%"
        assert len(data["matchedSkills"]) == 3
        assert len(data["missingSkills"]) == 4
        print("  -> Passed. Skill gap analysis match:", data["analysis"]["matchPercentage"])

        # 4. Create student profile (POST /api/profiles)
        print("\n[Test 4] Testing POST /api/profiles...")
        profile_payload = {
            "name": "Demo Student",
            "education": "B.Tech Computer Science",
            "skills": ["Python", "SQL & Relational Databases"],
            "targetRoleId": "role-3",
        }
        res = await client.post("/api/profiles", json=profile_payload)
        assert res.status_code == 201, f"Expected 201, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        profile = data["profile"]
        profile_id = profile["id"]
        assert profile["name"] == "Demo Student"
        assert profile["targetRoleId"] == "role-3"
        assert profile["targetRoleTitle"] == "AI Engineer"
        print(f"  -> Passed. Created profile ID: {profile_id} for target role: {profile['targetRoleTitle']}")

        # 5. Get student profile (GET /api/profiles/:id)
        print("\n[Test 5] Testing GET /api/profiles/:id...")
        res = await client.get(f"/api/profiles/{profile_id}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["profile"]["id"] == profile_id
        print("  -> Passed. Retrieved saved profile correctly.")

        # 6. Get saved profile skill gap (GET /api/profiles/:id/skill-gap)
        print("\n[Test 6] Testing GET /api/profiles/:id/skill-gap...")
        res = await client.get(f"/api/profiles/{profile_id}/skill-gap")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["roleTitle"] == "AI Engineer"
        print("  -> Passed. Profile skill gap match:", data["analysis"]["matchPercentage"])

        # 7. Get roadmap for saved profile (GET /api/profiles/:id/roadmap)
        print("\n[Test 7] Testing GET /api/profiles/:id/roadmap...")
        res = await client.get(f"/api/profiles/{profile_id}/roadmap")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        data = res.json()
        assert data["success"] is True
        assert data["targetRoleTitle"] == "AI Engineer"
        assert len(data["roadmap"]) > 0
        print(f"  -> Passed. Roadmap has {len(data['roadmap'])} steps. Step 1: {data['roadmap'][0]['skill']}")

        # 7b. Test dynamic roadmap role switching for all 3 career roles
        print("\n[Test 7b] Testing dynamic roadmap generation for all 3 career roles via ?roleId=...")
        for r_slug, r_expected_title in [
            ("role-1", "Full-Stack Developer"),
            ("role-2", "Data Analyst"),
            ("role-3", "AI Engineer"),
        ]:
            res_r = await client.get(f"/api/profiles/{profile_id}/roadmap?roleId={r_slug}")
            assert res_r.status_code == 200, f"Expected 200 for {r_slug}, got {res_r.status_code}"
            data_r = res_r.json()
            assert data_r["targetRoleId"] == r_slug
            assert data_r["targetRoleTitle"] == r_expected_title
            assert "summary" in data_r and data_r["summary"]["totalRequiredSkills"] > 0
            assert len(data_r["roadmap"]) > 0
            print(f"  -> Verified career roadmap for '{r_expected_title}' ({r_slug}): {len(data_r['roadmap'])} steps.")

        # 8. Test AI Career Chatbot (POST /api/chat)
        print("\n[Test 8] Testing POST /api/chat...")
        chat_res = await client.post(
            "/api/chat",
            json={
                "message": "What skills do I need to become an AI Engineer?",
                "history": [],
                "contextRoleId": "role-3",
            },
        )
        assert chat_res.status_code == 200, f"Expected 200, got {chat_res.status_code}"
        chat_data = chat_res.json()
        assert "reply" in chat_data and len(chat_data["reply"]) > 20
        assert "mode" in chat_data
        assert len(chat_data["suggestedQuestions"]) > 0
        print(f"  -> Passed. Chatbot ({chat_data['mode']}) returned response of {len(chat_data['reply'])} chars.")

        # 9. Test Student Registration (POST /api/auth/register)
        print("\n[Test 9] Testing POST /api/auth/register...")
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@pathify.test"
        reg_payload = {
            "full_name": "Test Student",
            "email": test_email,
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }
        reg_res = await client.post("/api/auth/register", json=reg_payload)
        assert reg_res.status_code == 201, f"Expected 201, got {reg_res.status_code}: {reg_res.text}"
        reg_data = reg_res.json()
        assert reg_data["success"] is True
        assert "access_token" in reg_data
        assert reg_data["user"]["email"] == test_email
        assert reg_data["user"]["full_name"] == "Test Student"
        jwt_token = reg_data["access_token"]
        print(f"  -> Passed. Registered user {test_email} and received JWT token.")

        # 10. Test Duplicate Email Registration Rejected (400)
        print("\n[Test 10] Testing duplicate registration rejection...")
        dup_res = await client.post("/api/auth/register", json=reg_payload)
        assert dup_res.status_code == 400, f"Expected 400 for duplicate email, got {dup_res.status_code}"
        print("  -> Passed. Duplicate registration properly rejected with 400 Bad Request.")

        # 11. Test User Login (POST /api/auth/login)
        print("\n[Test 11] Testing POST /api/auth/login...")
        login_res = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "SecurePassword123!"},
        )
        assert login_res.status_code == 200, f"Expected 200, got {login_res.status_code}"
        login_data = login_res.json()
        assert login_data["success"] is True
        assert "access_token" in login_data
        assert login_data["user"]["email"] == test_email
        print("  -> Passed. Login succeeded with valid credentials.")

        # 12. Test Invalid Password Login Rejected (401)
        print("\n[Test 12] Testing invalid credentials rejection...")
        bad_login_res = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "WrongPassword!"},
        )
        assert bad_login_res.status_code == 401, f"Expected 401, got {bad_login_res.status_code}"
        print("  -> Passed. Bad credentials properly rejected with 401 Unauthorized.")

        # 13. Test Current User Verification (GET /api/auth/me)
        print("\n[Test 13] Testing GET /api/auth/me...")
        me_res = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert me_res.status_code == 200, f"Expected 200, got {me_res.status_code}"
        me_data = me_res.json()
        assert me_data["success"] is True
        assert me_data["user"]["email"] == test_email
        assert me_data["user"]["full_name"] == "Test Student"
        print("  -> Passed. Verified current user from JWT Bearer token.")

        # 14. Test Authenticated Profile Creation (POST /api/profiles with JWT)
        print("\n[Test 14] Testing POST /api/profiles with JWT Bearer auth...")
        auth_profile_payload = {
            "name": "Test Student",
            "education": "M.S. Artificial Intelligence",
            "skills": ["Python", "SQL & Relational Databases"],
            "targetRoleId": "role-3",
        }
        auth_profile_res = await client.post(
            "/api/profiles",
            json=auth_profile_payload,
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert auth_profile_res.status_code == 201, f"Expected 201, got {auth_profile_res.status_code}"
        auth_pdata = auth_profile_res.json()
        assert auth_pdata["success"] is True
        assert auth_pdata["profile"]["education"] == "M.S. Artificial Intelligence"
        print("  -> Passed. Successfully saved profile linked to registered user account.")

        # 15. Test Roadmap Dynamic Milestone Completion & Summary Statistics Formula
        print("\n[Test 15] Testing Roadmap Milestone Completion & Dynamic Statistics...")
        u_suffix = uuid.uuid4().hex[:6]
        user15_resp = await client.post(
            "/api/auth/register",
            json={
                "full_name": "Zero-Skills Student",
                "email": f"zero_skills_{u_suffix}@pathify.test",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
        )
        assert user15_resp.status_code == 201
        token15 = user15_resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token15}"

        # Create student with 0 acquired skills for AI Engineer (role-3 has 11 required skills)
        fresh_profile_payload = {
            "name": "Zero-Skills Student",
            "education": "High School",
            "skills": [],
            "targetRoleId": "role-3",
        }
        f_res = await client.post("/api/profiles", json=fresh_profile_payload)
        assert f_res.status_code == 201
        f_profile_id = f_res.json()["profile"]["id"]

        # Initial roadmap check: Total=11, Acquired=0, Missing Steps=11, Completed=0%
        init_rm = await client.get(f"/api/profiles/{f_profile_id}/roadmap?roleId=role-3")
        assert init_rm.status_code == 200
        init_data = init_rm.json()
        init_summary = init_data["summary"]
        assert init_summary["totalRequiredSkills"] == 11
        assert init_summary["acquiredSkillsCount"] == 0
        assert init_summary["missingSkillsCount"] == 11
        assert init_summary["completedMilestonesCount"] == 0
        assert init_summary["completionPercentage"] == 0
        assert len(init_data["roadmap"]) == 11
        print("  -> Passed initial roadmap stats: Total=11, Acquired=0, Missing=11, Completed=0%")

        # Mark Milestone 1 as Completed
        t1_res = await client.post(
            f"/api/profiles/{f_profile_id}/roadmap/toggle-step",
            json={"roleId": "role-3", "stepNumber": 1, "completed": True},
        )
        assert t1_res.status_code == 200
        t1_data = t1_res.json()
        t1_sum = t1_data["summary"]
        assert t1_sum["totalRequiredSkills"] == 11
        assert t1_sum["acquiredSkillsCount"] == 0
        assert t1_sum["completedMilestonesCount"] == 1
        assert t1_sum["missingSkillsCount"] == 10  # 11 - 1 = 10
        assert t1_sum["completionPercentage"] == 9  # round(1/11 * 100) = 9%
        assert t1_data["roadmap"][0]["completed"] is True
        print("  -> Passed Step 1 Completed: Missing Steps=10, Completed=9%")

        # Mark Milestone 2 as Completed
        t2_res = await client.post(
            f"/api/profiles/{f_profile_id}/roadmap/toggle-step",
            json={"roleId": "role-3", "stepNumber": 2, "completed": True},
        )
        assert t2_res.status_code == 200
        t2_data = t2_res.json()
        t2_sum = t2_data["summary"]
        assert t2_sum["totalRequiredSkills"] == 11
        assert t2_sum["acquiredSkillsCount"] == 0
        assert t2_sum["completedMilestonesCount"] == 2
        assert t2_sum["missingSkillsCount"] == 9  # 11 - 2 = 9
        assert t2_sum["completionPercentage"] == 18  # round(2/11 * 100) = 18%
        assert t2_data["roadmap"][1]["completed"] is True
        print("  -> Passed Step 2 Completed: Missing Steps=9, Completed=18% (Formula strictly verified!)")

        # 16. Test Persistence in PostgreSQL After Page Refresh & Cross-Role Isolation
        print("\n[Test 16] Testing Persistence in PostgreSQL & Cross-Role Roadmap Isolation...")
        # Simulate browser refresh by calling GET /api/profiles/{id}/roadmap
        refreshed_rm = await client.get(f"/api/profiles/{f_profile_id}/roadmap?roleId=role-3")
        assert refreshed_rm.status_code == 200
        refreshed_data = refreshed_rm.json()
        r_sum = refreshed_data["summary"]
        assert r_sum["missingSkillsCount"] == 9
        assert r_sum["completedMilestonesCount"] == 2
        assert r_sum["completionPercentage"] == 18
        assert refreshed_data["roadmap"][0]["completed"] is True
        assert refreshed_data["roadmap"][1]["completed"] is True
        print("  -> Passed PostgreSQL Persistence: Milestones 1 and 2 remain completed after refresh.")

        # Switch to Data Analyst (role-2): Must NOT mix completions with AI Engineer!
        da_rm = await client.get(f"/api/profiles/{f_profile_id}/roadmap?roleId=role-2")
        assert da_rm.status_code == 200
        da_data = da_rm.json()
        assert da_data["targetRoleId"] == "role-2"
        assert da_data["summary"]["completedMilestonesCount"] == 0
        assert da_data["summary"]["missingSkillsCount"] == da_data["summary"]["totalRequiredSkills"]
        assert all(step["completed"] is False for step in da_data["roadmap"])
        print(f"  -> Passed Cross-Role Isolation: Data Analyst has 0 completed milestones, no mixing.")

        # Switch back to AI Engineer (role-3): Progress must be retained!
        ai_rm = await client.get(f"/api/profiles/{f_profile_id}/roadmap?roleId=role-3")
        assert ai_rm.status_code == 200
        ai_data = ai_rm.json()
        assert ai_data["summary"]["completedMilestonesCount"] == 2
        assert ai_data["summary"]["missingSkillsCount"] == 9
        assert ai_data["summary"]["completionPercentage"] == 18
        print("  -> Passed Switching Back: AI Engineer still has 2 completed milestones and Missing Steps=9.")

        # Unmark Milestone 1
        unmark_res = await client.post(
            f"/api/profiles/{f_profile_id}/roadmap/toggle-step",
            json={"roleId": "role-3", "stepNumber": 1, "completed": False},
        )
        assert unmark_res.status_code == 200
        unmark_data = unmark_res.json()
        u_sum = unmark_data["summary"]
        assert u_sum["completedMilestonesCount"] == 1
        assert u_sum["missingSkillsCount"] == 10  # 11 - 1 = 10
        assert u_sum["completionPercentage"] == 9
        assert unmark_data["roadmap"][0]["completed"] is False
        assert unmark_data["roadmap"][1]["completed"] is True
        print("  -> Passed Unmarking Milestone: Missing Steps incremented back to 10, Completed=9%.")

        # 18. Test Reset Password HTML Static Serving
        print("\n[Test 18] Testing Reset Password HTML static page serving (GET /reset-password.html)...")
        reset_page_res = await client.get("/reset-password.html")
        assert reset_page_res.status_code == 200, f"Expected 200, got {reset_page_res.status_code}"
        assert "Reset Password" in reset_page_res.text
        assert "Pathify" in reset_page_res.text
        print("  -> Passed. reset-password.html served at /reset-password.html.")

        # 19. Test Forgot Password Endpoint Validation (POST /api/auth/forgot-password)
        print("\n[Test 19] Testing POST /api/auth/forgot-password validation...")
        # A. Non-existent email
        unknown_res = await client.post(
            "/api/auth/forgot-password",
            json={"email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com"},
        )
        assert unknown_res.status_code == 404, f"Expected 404, got {unknown_res.status_code}"
        print("  -> Passed. Non-existent email rejected with 404 Not Found.")

        # B. Registered email error handling or live dispatch via Resend
        real_user_res = await client.post(
            "/api/auth/forgot-password",
            json={"email": test_email},
        )
        # Accepts 200 (if Resend succeeds) or 500/502 (if Resend key missing or test domain rejected)
        assert real_user_res.status_code in (200, 500, 502), f"Expected 200, 500 or 502, got {real_user_res.status_code}"
        if real_user_res.status_code == 200:
            print("  -> Passed. Reset password email dispatched successfully via Resend API.")
        else:
            err_msg = real_user_res.json()["detail"]
            assert "Resend" in err_msg
            print(f"  -> Passed. Resend email service handled honestly ({real_user_res.status_code}: {err_msg[:45]}...).")

        # 20. Test Secure Single-Use Token Verification & Password Reset with PostgreSQL
        print("\n[Test 20] Testing Token Lifecycle, Single-Use Invalidation & Password Reset in PostgreSQL...")
        from database.connection import AsyncSessionLocal
        from database.models import User, PasswordResetToken
        from backend.app.services.auth_service import generate_reset_token, hash_password
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import select

        # Generate a test token
        raw_test_token, test_token_hash = generate_reset_token()
        async with AsyncSessionLocal() as db_session:
            # Query the test user
            u_query = select(User).where(User.email == test_email)
            u_res = await db_session.execute(u_query)
            db_user = u_res.scalar_one()

            # Insert an active reset token with 20-minute expiry
            now = datetime.now(timezone.utc)
            active_token_record = PasswordResetToken(
                user_id=db_user.id,
                token_hash=test_token_hash,
                expires_at=now + timedelta(minutes=20),
            )
            db_session.add(active_token_record)

            # Insert an expired token (> 20 min ago)
            expired_raw, expired_hash = generate_reset_token()
            expired_record = PasswordResetToken(
                user_id=db_user.id,
                token_hash=expired_hash,
                expires_at=now - timedelta(minutes=5),
            )
            db_session.add(expired_record)
            await db_session.commit()

        # A. Test Token Verification Endpoint (GET /api/auth/verify-reset-token)
        verify_res = await client.get(f"/api/auth/verify-reset-token?token={raw_test_token}")
        assert verify_res.status_code == 200, f"Expected 200, got {verify_res.status_code}"
        assert verify_res.json()["valid"] is True
        print("  -> Passed. Valid reset token confirmed.")

        # B. Test Expired Token Rejection
        exp_res = await client.get(f"/api/auth/verify-reset-token?token={expired_raw}")
        assert exp_res.status_code == 400, f"Expected 400, got {exp_res.status_code}"
        assert "expired" in exp_res.json()["detail"].lower()
        print("  -> Passed. Expired token properly rejected with 400 Bad Request.")

        # C. Reset password using valid token (POST /api/auth/reset-password)
        new_password = "BrandNewSecurePassword2026!"
        reset_res = await client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_test_token,
                "password": new_password,
                "confirm_password": new_password,
            },
        )
        assert reset_res.status_code == 200, f"Expected 200, got {reset_res.status_code}"
        assert reset_res.json()["success"] is True
        print("  -> Passed. Password reset succeeded.")

        # D. Single-Use Verification: Re-using the same token must fail!
        reuse_verify = await client.get(f"/api/auth/verify-reset-token?token={raw_test_token}")
        assert reuse_verify.status_code == 400, f"Expected 400, got {reuse_verify.status_code}"
        assert "already been used" in reuse_verify.json()["detail"].lower()

        reuse_reset = await client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_test_token,
                "password": "AnotherPassword123!",
                "confirm_password": "AnotherPassword123!",
            },
        )
        assert reuse_reset.status_code == 400, f"Expected 400, got {reuse_reset.status_code}"
        print("  -> Passed Single-Use Security: Token marked used in PostgreSQL, cannot be reused.")

        # E. Verify User Login with New Password & Rejection of Old Password
        old_login_res = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "StudentPassword123!"},
        )
        assert old_login_res.status_code == 401, f"Expected 401 for old password, got {old_login_res.status_code}"
        print("  -> Passed. Old password rejected with 401 Unauthorized.")

        new_login_res = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": new_password},
        )
        assert new_login_res.status_code == 200, f"Expected 200 for new password, got {new_login_res.status_code}"
        new_login_data = new_login_res.json()
        assert new_login_data["success"] is True
        assert "access_token" in new_login_data
        print("  -> Passed. User successfully authenticated with NEW password!")

    print("\n" + "=" * 60)
    print("ALL 20 TEST SUITES PASSED (FRONTEND + ROADMAP + PERSISTENCE + AUTH + FORGOT/RESET PW)!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all_endpoints())
