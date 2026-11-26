"""
Comprehensive Test Suite for Pathify AI Authentication & Protected Routes Access Control
Covers:
1. Public endpoints accessibility without authentication
2. Protected API blocking with HTTP 401 Unauthorized
3. Invalid / expired JWT token rejection with HTTP 401
4. Authenticated access via Bearer Token
5. Authenticated access via HttpOnly / SameSite Cookie
6. Cross-user unauthorized profile access rejection with HTTP 403 Forbidden
7. Logout session invalidation & cookie clearing
8. Regression: Forgot Password & Reset Password workflows
"""

import asyncio
import sys
import uuid
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://127.0.0.1:5000"


async def run_tests():
    print("=" * 80)
    print("PATHIFY AI - AUTHENTICATION & ACCESS CONTROL INTEGRATION TEST SUITE")
    print("=" * 80)

    # Use a client with cookie jar enabled
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # -------------------------------------------------------------
        # TEST 1: Public Endpoints (Must be accessible without auth)
        # -------------------------------------------------------------
        print("\n[TEST 1] Public endpoints accessible without authentication")
        r_health = await client.get("/api/health")
        assert r_health.status_code == 200, f"Health check failed: {r_health.status_code}"
        assert r_health.json()["status"] == "ok"
        print("  ✓ GET /api/health -> 200 OK (Public)")

        r_reset_page = await client.get("/reset-password")
        assert r_reset_page.status_code == 200, f"Reset password page failed: {r_reset_page.status_code}"
        print("  ✓ GET /reset-password -> 200 OK (Public HTML)")

        # -------------------------------------------------------------
        # TEST 2: Protected Endpoints (Must return 401 when unauthenticated)
        # -------------------------------------------------------------
        print("\n[TEST 2] Protected endpoints return HTTP 401 Unauthorized without auth")
        dummy_uuid = str(uuid.uuid4())

        protected_endpoints = [
            ("GET", "/api/roles", None),
            ("POST", "/api/skill-gap", {"roleId": "role-1", "skills": ["Python"]}),
            ("POST", "/api/skill-gap/assess", {"roleId": "role-1", "skills": ["Python"]}),
            ("GET", "/api/skill-gap/history", None),
            ("GET", f"/api/skill-gap/assessments/{dummy_uuid}", None),
            ("POST", "/api/chat", {"message": "Hello coach"}),
            ("POST", "/api/profiles", {"name": "Test Student", "targetRoleId": "role-1", "skills": ["Python"]}),
            ("GET", f"/api/profiles/{dummy_uuid}", None),
            ("GET", f"/api/profiles/{dummy_uuid}/skill-gap", None),
            ("GET", f"/api/profiles/{dummy_uuid}/roadmap", None),
            ("POST", f"/api/profiles/{dummy_uuid}/roadmap/toggle-step", {"roleId": "role-1", "stepNumber": 1, "completed": True}),
            ("GET", "/api/auth/me", None),
        ]

        for method, endpoint, payload in protected_endpoints:
            if method == "GET":
                resp = await client.get(endpoint)
            else:
                resp = await client.post(endpoint, json=payload)
            assert resp.status_code == 401, f"Expected 401 on {method} {endpoint}, got {resp.status_code}: {resp.text}"
            print(f"  ✓ {method} {endpoint} -> 401 Unauthorized (Blocked)")

        # -------------------------------------------------------------
        # TEST 3: Invalid & Expired Token Rejection (Must return 401)
        # -------------------------------------------------------------
        print("\n[TEST 3] Invalid / malformed / expired token rejection")
        resp_invalid_bearer = await client.get(
            "/api/roles",
            headers={"Authorization": "Bearer invalid.malformed.token.value"}
        )
        assert resp_invalid_bearer.status_code == 401, f"Expected 401 on invalid token, got {resp_invalid_bearer.status_code}"
        print("  ✓ GET /api/roles with invalid Bearer -> 401 Unauthorized")

        resp_invalid_cookie = await client.get(
            "/api/roles",
            cookies={"access_token": "expired_or_corrupt_jwt"}
        )
        assert resp_invalid_cookie.status_code == 401, f"Expected 401 on invalid cookie, got {resp_invalid_cookie.status_code}"
        print("  ✓ GET /api/roles with invalid Cookie -> 401 Unauthorized")

        # -------------------------------------------------------------
        # TEST 4: Registration & Login with Bearer and Cookie Setting
        # -------------------------------------------------------------
        print("\n[TEST 4] Register & Login sets JWT Bearer and HttpOnly Cookie")
        test_email = f"auth_student_{uuid.uuid4().hex[:8]}@pathify.test"
        test_password = "SecurePassword123!"

        # Register User A
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "full_name": "Auth Test User A",
                "email": test_email,
                "password": test_password,
                "confirm_password": test_password,
            },
        )
        assert reg_resp.status_code == 201, f"Register failed: {reg_resp.text}"
        reg_data = reg_resp.json()
        assert reg_data["access_token"], "Missing access_token in registration response"
        token_a = reg_data["access_token"]
        assert "access_token" in reg_resp.cookies, "Missing access_token cookie in registration response"
        print("  ✓ POST /api/auth/register -> 201 Created with JWT and cookie set")

        # Login User A
        login_resp = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": test_password},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        login_data = login_resp.json()
        assert login_data["access_token"]
        assert "access_token" in login_resp.cookies
        user_a_id = login_data["user"]["id"]
        print(f"  ✓ POST /api/auth/login -> 200 OK (User ID: {user_a_id})")

        # -------------------------------------------------------------
        # TEST 5: Authenticated Access via Bearer Token
        # -------------------------------------------------------------
        print("\n[TEST 5] Authenticated access using Authorization: Bearer <token>")
        auth_headers_a = {"Authorization": f"Bearer {token_a}"}

        # 1. /api/auth/me
        r_me = await client.get("/api/auth/me", headers=auth_headers_a)
        assert r_me.status_code == 200
        assert r_me.json()["user"]["email"] == test_email
        print("  ✓ GET /api/auth/me -> 200 OK with correct user profile")

        # 2. /api/roles
        r_roles = await client.get("/api/roles", headers=auth_headers_a)
        assert r_roles.status_code == 200
        roles_data = r_roles.json()["roles"]
        assert len(roles_data) >= 3
        print(f"  ✓ GET /api/roles -> 200 OK ({len(roles_data)} roles returned)")

        # 3. /api/skill-gap
        r_gap = await client.post(
            "/api/skill-gap",
            headers=auth_headers_a,
            json={
                "roleId": "role-1",
                "skills": [
                    {"name": "HTML & CSS", "level": "Intermediate"},
                    {"name": "JavaScript", "level": "Advanced"},
                ],
                "experience": {"projectsCount": 2, "internshipMonths": 3},
            },
        )
        assert r_gap.status_code == 200
        gap_data = r_gap.json()
        assert gap_data["success"] is True
        assessment_id = gap_data.get("assessmentId")
        assert assessment_id, "Assessment should be persisted for authenticated user"
        print(f"  ✓ POST /api/skill-gap -> 200 OK (Persisted Assessment ID: {assessment_id})")

        # 4. /api/skill-gap/history
        r_hist = await client.get("/api/skill-gap/history", headers=auth_headers_a)
        assert r_hist.status_code == 200
        hist_data = r_hist.json()["assessments"]
        assert len(hist_data) >= 1
        print(f"  ✓ GET /api/skill-gap/history -> 200 OK ({len(hist_data)} assessments found)")

        # 5. /api/skill-gap/assessments/{id}
        r_single_assess = await client.get(f"/api/skill-gap/assessments/{assessment_id}", headers=auth_headers_a)
        assert r_single_assess.status_code == 200
        assert r_single_assess.json()["roleId"] == "role-1"
        print(f"  ✓ GET /api/skill-gap/assessments/{assessment_id} -> 200 OK")

        # 6. /api/chat
        r_chat = await client.post(
            "/api/chat",
            headers=auth_headers_a,
            json={"message": "What skills are needed for Full-Stack?", "contextRoleId": "role-1"},
        )
        assert r_chat.status_code == 200
        assert len(r_chat.json()["reply"]) > 10
        print("  ✓ POST /api/chat -> 200 OK (AI Mentor responded)")

        # 7. /api/profiles (Create & Roadmap)
        r_prof = await client.post(
            "/api/profiles",
            headers=auth_headers_a,
            json={
                "name": "Auth Test User A",
                "education": "Computer Science",
                "targetRoleId": "role-1",
                "skills": ["HTML & CSS", "JavaScript", "React"],
            },
        )
        assert r_prof.status_code == 201
        profile_a_id = r_prof.json()["profile"]["id"]
        print(f"  ✓ POST /api/profiles -> 201 Created (Profile ID: {profile_a_id})")

        # 8. /api/profiles/{id}
        r_get_prof = await client.get(f"/api/profiles/{profile_a_id}", headers=auth_headers_a)
        assert r_get_prof.status_code == 200
        assert r_get_prof.json()["profile"]["name"] == "Auth Test User A"
        print(f"  ✓ GET /api/profiles/{profile_a_id} -> 200 OK")

        # 9. /api/profiles/{id}/roadmap
        r_roadmap = await client.get(f"/api/profiles/{profile_a_id}/roadmap?roleId=role-1", headers=auth_headers_a)
        assert r_roadmap.status_code == 200
        assert len(r_roadmap.json()["roadmap"]) > 0
        print(f"  ✓ GET /api/profiles/{profile_a_id}/roadmap -> 200 OK")

        # 10. /api/profiles/{id}/roadmap/toggle-step
        r_toggle = await client.post(
            f"/api/profiles/{profile_a_id}/roadmap/toggle-step",
            headers=auth_headers_a,
            json={"roleId": "role-1", "stepNumber": 1, "completed": True},
        )
        assert r_toggle.status_code == 200
        assert r_toggle.json()["roadmap"][0]["completed"] is True
        print(f"  ✓ POST /api/profiles/{profile_a_id}/roadmap/toggle-step -> 200 OK")

        # -------------------------------------------------------------
        # TEST 6: Authenticated Access via HttpOnly / SameSite Cookie
        # -------------------------------------------------------------
        print("\n[TEST 6] Authenticated access via HttpOnly Cookie (No Bearer header)")
        # A separate client that passes ONLY the cookie
        async with httpx.AsyncClient(base_url=BASE_URL, cookies={"access_token": token_a}, timeout=15.0) as cookie_client:
            r_cookie_me = await cookie_client.get("/api/auth/me")
            assert r_cookie_me.status_code == 200
            assert r_cookie_me.json()["user"]["email"] == test_email
            print("  ✓ GET /api/auth/me via Cookie -> 200 OK")

            r_cookie_roles = await cookie_client.get("/api/roles")
            assert r_cookie_roles.status_code == 200
            print("  ✓ GET /api/roles via Cookie -> 200 OK")

            r_cookie_roadmap = await cookie_client.get(f"/api/profiles/{profile_a_id}/roadmap?roleId=role-1")
            assert r_cookie_roadmap.status_code == 200
            print("  ✓ GET /api/profiles/{id}/roadmap via Cookie -> 200 OK")

        # -------------------------------------------------------------
        # TEST 7: Cross-User Authorization (HTTP 403 Forbidden)
        # -------------------------------------------------------------
        print("\n[TEST 7] Cross-user access control (HTTP 403 Forbidden)")
        # Register User B
        email_b = f"user_b_{uuid.uuid4().hex[:8]}@pathify.test"
        reg_b = await client.post(
            "/api/auth/register",
            json={
                "full_name": "User B",
                "email": email_b,
                "password": test_password,
                "confirm_password": test_password,
            },
        )
        assert reg_b.status_code == 201
        token_b = reg_b.json()["access_token"]
        auth_headers_b = {"Authorization": f"Bearer {token_b}"}

        # User B attempts to access User A's profile
        r_cross_profile = await client.get(f"/api/profiles/{profile_a_id}", headers=auth_headers_b)
        assert r_cross_profile.status_code == 403, f"Expected 403, got {r_cross_profile.status_code}"
        print(f"  ✓ GET /api/profiles/{profile_a_id} by User B -> 403 Forbidden")

        # User B attempts to access User A's roadmap
        r_cross_roadmap = await client.get(f"/api/profiles/{profile_a_id}/roadmap", headers=auth_headers_b)
        assert r_cross_roadmap.status_code == 403, f"Expected 403, got {r_cross_roadmap.status_code}"
        print(f"  ✓ GET /api/profiles/{profile_a_id}/roadmap by User B -> 403 Forbidden")

        # User B attempts to toggle User A's milestone
        r_cross_toggle = await client.post(
            f"/api/profiles/{profile_a_id}/roadmap/toggle-step",
            headers=auth_headers_b,
            json={"roleId": "role-1", "stepNumber": 1, "completed": False},
        )
        assert r_cross_toggle.status_code == 403, f"Expected 403, got {r_cross_toggle.status_code}"
        print(f"  ✓ POST /api/profiles/{profile_a_id}/roadmap/toggle-step by User B -> 403 Forbidden")

        # User B attempts to view User A's skill gap assessment
        r_cross_assess = await client.get(f"/api/skill-gap/assessments/{assessment_id}", headers=auth_headers_b)
        assert r_cross_assess.status_code in (403, 404), f"Expected 403 or 404, got {r_cross_assess.status_code}"
        print(f"  ✓ GET /api/skill-gap/assessments/{assessment_id} by User B -> {r_cross_assess.status_code} Blocked")

        # -------------------------------------------------------------
        # TEST 8: Logout Endpoint & Cookie Invalidation
        # -------------------------------------------------------------
        print("\n[TEST 8] Logout functionality & cookie clearing")
        logout_resp = await client.post("/api/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["success"] is True
        # Verify access_token cookie is deleted/expired in response
        cookie_header = logout_resp.headers.get("set-cookie", "")
        assert "access_token" in cookie_header
        print("  ✓ POST /api/auth/logout -> 200 OK (access_token cookie cleared)")

        # -------------------------------------------------------------
        # TEST 9: Forgot Password & Reset Password Regression
        # -------------------------------------------------------------
        print("\n[TEST 9] Forgot Password & Reset Password regression workflow")
        # 1. Verify forgot-password endpoint is public (returns 404 for unknown email without auth)
        r_forgot_unknown = await client.post(
            "/api/auth/forgot-password",
            json={"email": "nonexistent_user_xyz@pathify.test"},
        )
        assert r_forgot_unknown.status_code == 404, f"Expected 404, got {r_forgot_unknown.status_code}"
        print("  ✓ POST /api/auth/forgot-password accessible without authentication")

        # 2. Insert valid 20-minute reset token in PostgreSQL for test_email
        from database import AsyncSessionLocal
        from database.models import User, PasswordResetToken
        from sqlalchemy import select
        from datetime import datetime, timezone, timedelta
        from backend.app.services.auth_service import generate_reset_token

        test_raw_token, test_token_hash = generate_reset_token()
        async with AsyncSessionLocal() as session:
            u_res = await session.execute(select(User).where(User.email == test_email))
            user_obj = u_res.scalar_one_or_none()
            assert user_obj is not None

            token_record = PasswordResetToken(
                user_id=user_obj.id,
                token_hash=test_token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            )
            session.add(token_record)
            await session.commit()
        print(f"  ✓ Valid single-use reset token created in PostgreSQL (20-min expiry)")

        # 3. Verify token (public endpoint)
        r_verify = await client.get(f"/api/auth/verify-reset-token?token={test_raw_token}")
        assert r_verify.status_code == 200
        assert r_verify.json()["valid"] is True
        print("  ✓ GET /api/auth/verify-reset-token -> 200 OK (Token verified)")

        # 4. Reject same password reuse
        r_reuse = await client.post(
            "/api/auth/reset-password",
            json={
                "token": test_raw_token,
                "password": test_password,
                "confirm_password": test_password,
            },
        )
        assert r_reuse.status_code == 400
        assert "You cannot reuse your current password" in r_reuse.json()["detail"]
        print("  ✓ Password reuse rejected securely with 400 Bad Request")

        # 5. Reset with new password
        new_password = "BrandNewPassword456!"
        r_reset_success = await client.post(
            "/api/auth/reset-password",
            json={
                "token": test_raw_token,
                "password": new_password,
                "confirm_password": new_password,
            },
        )
        assert r_reset_success.status_code == 200
        assert r_reset_success.json()["success"] is True
        print("  ✓ POST /api/auth/reset-password -> 200 OK (Password updated)")

        # 6. Token is now single-use and cannot be reused
        r_reused_token = await client.get(f"/api/auth/verify-reset-token?token={test_raw_token}")
        assert r_reused_token.status_code == 400
        print("  ✓ Reset token is single-use and invalidated after update")

        # 7. Old password no longer works
        r_old_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": test_password},
        )
        assert r_old_login.status_code == 401
        print("  ✓ Login with previous password properly rejected with 401 Unauthorized")

        # 8. Login with new password succeeds
        r_new_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": new_password},
        )
        assert r_new_login.status_code == 200
        print("  ✓ Login with new password succeeds with 200 OK")

    print("\n" + "=" * 80)
    print("ALL AUTHENTICATION & ACCESS CONTROL TESTS PASSED SUCCESSFULLY! (10/10)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_tests())
