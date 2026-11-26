"""
Complete Test Suite for Password Reset Link URL Resolution & Forgot Password Workflow
Pathify AI
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import AppSettings, app_settings
from backend.app.services.auth_service import (
    generate_reset_token,
    hash_password,
    hash_token,
    resolve_frontend_base_url,
    verify_password,
)
from backend.app.services.email_service import send_password_reset_email


def test_frontend_url_env_loading():
    """Verify FRONTEND_URL is loaded from environment and settings."""
    print("\n--- [1/6] Testing FRONTEND_URL Environment Loading ---")
    assert app_settings.frontend_url, "frontend_url must not be empty"
    assert app_settings.frontend_url.startswith("http"), f"Invalid frontend_url: {app_settings.frontend_url}"
    print(f"  ✓ Loaded app_settings.frontend_url: {app_settings.frontend_url}")

    # Test custom env var override
    with patch.dict(os.environ, {"FRONTEND_URL": "https://staging.pathify.ai"}):
        custom_settings = AppSettings()
        assert custom_settings.frontend_url == "https://staging.pathify.ai"
        print(f"  ✓ Custom FRONTEND_URL env override verified: {custom_settings.frontend_url}")


def test_resolve_frontend_base_url():
    """Verify resolve_frontend_base_url guarantees valid HTTP URL and NEVER returns null."""
    print("\n--- [2/6] Testing resolve_frontend_base_url Sanitization ---")

    # Critical bug scenario: browser sends Origin: null (from file:/// or sandbox)
    res_null = resolve_frontend_base_url(origin="null")
    assert res_null != "null", "resolve_frontend_base_url must NEVER return 'null'"
    assert res_null.startswith("http"), f"Must return valid HTTP URL, got: {res_null}"
    assert "null" not in res_null, f"URL must not contain 'null': {res_null}"
    print(f"  ✓ Origin='null' correctly resolved to: {res_null}")

    # Other invalid origin values
    for invalid in ["None", "undefined", "", "false", "0", "null/reset-password.html", "ftp://example.com"]:
        res_inv = resolve_frontend_base_url(origin=invalid)
        assert res_inv != invalid
        assert res_inv.startswith("http"), f"Failed for {invalid}: {res_inv}"
    print("  ✓ Invalid values ('None', 'undefined', '', etc.) safely rejected.")

    # None origin with referer
    res_ref = resolve_frontend_base_url(origin=None, referer="http://localhost:5000/login.html")
    assert res_ref == "http://localhost:5000"
    print(f"  ✓ Valid referer correctly extracted: {res_ref}")

    # Valid origin preserved (with trailing slash stripped)
    res_valid = resolve_frontend_base_url(origin="http://localhost:5000/")
    assert res_valid == "http://localhost:5000"
    print(f"  ✓ Valid origin formatted cleanly without trailing slash: {res_valid}")


def test_reset_token_security_and_expiry():
    """Verify token generation, SHA-256 hashing, and 20-minute expiry."""
    print("\n--- [3/6] Testing 20-Minute Single-Use Token Security ---")
    raw_token, token_hash = generate_reset_token()
    assert len(raw_token) >= 32, "Raw token must have high entropy"
    assert len(token_hash) == 64, "Token hash must be SHA-256 (64 hex characters)"
    assert hash_token(raw_token) == token_hash, "hash_token must match generated hash"
    assert raw_token != token_hash, "Raw token must not equal the hash"
    assert app_settings.reset_token_expire_minutes == 20, "Reset token must expire in exactly 20 minutes"
    print(f"  ✓ Token entropy and SHA-256 hashing verified.")
    print(f"  ✓ Reset token expiration set to: {app_settings.reset_token_expire_minutes} minutes.")


async def test_email_service_html_generation():
    """Verify email HTML contains valid reset URL, 20-min notice, and no null."""
    print("\n--- [4/6] Testing Email HTML Generation & Resend Dispatch ---")
    test_raw_token, _ = generate_reset_token()
    base_url = resolve_frontend_base_url(origin="null")
    reset_url = f"{base_url}/reset-password.html?token={test_raw_token}"

    assert "null" not in reset_url, f"reset_url must not contain null: {reset_url}"
    assert reset_url.startswith("http://localhost:5000/reset-password.html?token="), f"Unexpected reset_url: {reset_url}"

    with patch.object(app_settings, "resend_api_key", "re_test_dummy_key_123"):
        mock_resp = httpx.Response(200, json={"id": "resend_msg_test_123"})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
            res = await send_password_reset_email(
                to_email="student@pathify.test",
                reset_url=reset_url,
            )
            assert res["id"] == "resend_msg_test_123"
            assert mock_post.called
            _, call_kwargs = mock_post.call_args
            payload = call_kwargs["json"]
            html = payload["html"]

            assert reset_url in html, "HTML must contain the exact reset URL"
            assert "null/reset-password" not in html, "HTML must NOT contain null/reset-password"
            assert "20 minutes" in html, "HTML must emphasize 20-minute expiry"
            assert payload["to"] == ["student@pathify.test"]
            assert payload["subject"] == "Reset Your Pathify AI Password"
            print(f"  ✓ Reset URL embedded correctly in email HTML: {reset_url}")
            print("  ✓ Resend API dispatch payload verified.")


async def test_live_server_endpoints():
    """Test live server endpoints on http://127.0.0.1:5000."""
    print("\n--- [5/6] Testing Live HTTP Server & Frontend Accessibility ---")
    async with httpx.AsyncClient(base_url="http://127.0.0.1:5000", timeout=10.0) as client:
        # Check health
        health = await client.get("/api/health")
        assert health.status_code == 200, f"Health check failed: {health.text}"
        print("  ✓ /api/health returned 200 OK")

        # Check frontend static file accessibility
        resp_html = await client.get("/reset-password.html")
        assert resp_html.status_code == 200, f"reset-password.html failed: {resp_html.status_code}"
        assert "Reset Password" in resp_html.text
        print("  ✓ http://127.0.0.1:5000/reset-password.html is accessible (200 OK)")

        # Check clean path /reset-password (html=True static files)
        resp_clean = await client.get("/reset-password")
        assert resp_clean.status_code == 200
        print("  ✓ http://127.0.0.1:5000/reset-password is accessible (200 OK)")


async def test_full_forgot_password_flow():
    """Test the complete forgot-password flow with Origin: null against live database."""
    print("\n--- [6/6] Testing Full Password Reset Lifecycle with Origin: null ---")
    uid_suffix = uuid.uuid4().hex[:6]
    test_email = f"reset_test_{uid_suffix}@pathify.test"
    initial_pass = "InitialPass123!"
    new_pass = "UpdatedPass456!"

    async with httpx.AsyncClient(base_url="http://127.0.0.1:5000", timeout=15.0) as client:
        # 1. Register test user
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "full_name": f"Reset Tester {uid_suffix}",
                "email": test_email,
                "password": initial_pass,
                "confirm_password": initial_pass,
            },
        )
        assert reg_resp.status_code == 201, f"Register failed: {reg_resp.text}"
        print(f"  ✓ Test user registered: {test_email}")

        # 2. Call forgot-password with Origin: null (simulating file:/// origin)
        # We query the database to get the raw token hash and record
        from database import AsyncSessionLocal
        from database.models import User, PasswordResetToken
        from sqlalchemy import select

        # Make request to /api/auth/forgot-password with Origin: null
        # Note: If real Resend key is invalid/unconfigured in test, we handle either 200 or 502 with Resend message
        fp_headers = {"Origin": "null", "Referer": "file:///C:/pathify-ai/frontend/login.html"}
        fp_resp = await client.post(
            "/api/auth/forgot-password",
            json={"email": test_email},
            headers=fp_headers,
        )

        # Check token created in PostgreSQL
        async with AsyncSessionLocal() as session:
            user_res = await session.execute(select(User).where(User.email == test_email))
            user = user_res.scalar_one_or_none()
            assert user is not None, "User must exist in DB"

            token_res = await session.execute(
                select(PasswordResetToken)
                .where(PasswordResetToken.user_id == user.id)
                .order_by(PasswordResetToken.created_at.desc())
            )
            token_record = token_res.scalar_one_or_none()
            assert token_record is not None, "PasswordResetToken record must be created in PostgreSQL"
            assert token_record.used_at is None, "Token must be unused initially"
            now_utc = datetime.now(timezone.utc)
            # expires_at should be ~20 mins in future
            remaining = (token_record.expires_at - now_utc).total_seconds()
            assert 1100 <= remaining <= 1300, f"Token expires_at should be ~1200s (20 mins), got: {remaining}"
            print(f"  ✓ Token generated in DB: expires in {remaining:.0f}s (~20 mins), used_at=None")

            # Test token verification using an active token
            # Create a known test raw token for end-to-end verification and reset test
            test_raw, test_hash = generate_reset_token()
            token_record.token_hash = test_hash
            await session.commit()

        # 3. Verify token endpoint
        verify_resp = await client.get(f"/api/auth/verify-reset-token?token={test_raw}")
        assert verify_resp.status_code == 200, f"Token verify failed: {verify_resp.text}"
        assert verify_resp.json()["valid"] is True
        print("  ✓ /api/auth/verify-reset-token verified valid token (200 OK)")

        # 4. Reset password using token
        reset_resp = await client.post(
            "/api/auth/reset-password",
            json={
                "token": test_raw,
                "password": new_pass,
                "confirm_password": new_pass,
            },
        )
        assert reset_resp.status_code == 200, f"Reset password failed: {reset_resp.text}"
        print("  ✓ /api/auth/reset-password succeeded (200 OK)")

        # 5. Token is single-use: verifying or resetting again must FAIL
        verify_used_resp = await client.get(f"/api/auth/verify-reset-token?token={test_raw}")
        assert verify_used_resp.status_code == 400, "Used token must be rejected"
        print("  ✓ Used token correctly rejected on verify (single-use enforced: 400 Bad Request)")

        # 6. Verify login with old password fails
        old_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": initial_pass},
        )
        assert old_login.status_code == 401, "Old password must be rejected"
        print("  ✓ Old password login rejected (401 Unauthorized)")

        # 7. Verify login with new password succeeds
        new_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": new_pass},
        )
        assert new_login.status_code == 200, f"New password login failed: {new_login.text}"
        assert "access_token" in new_login.json(), "Login response must contain access_token"
        print("  ✓ New password login succeeded (200 OK, JWT issued)")


async def test_password_reuse_prevention():
    """Verify that resetting with the current password is strictly rejected,
    confirming old password remains valid and different password succeeds."""
    print("\n--- [7/7] Testing Password Reuse Prevention ---")
    uid_suffix = uuid.uuid4().hex[:6]
    test_email = f"reuse_test_{uid_suffix}@pathify.test"
    current_pass = "ExistingSecurePass123!"
    different_pass = "CompletelyNewSecurePass456!"

    async with httpx.AsyncClient(base_url="http://127.0.0.1:5000", timeout=15.0) as client:
        # 1. Register test user with current password
        reg_resp = await client.post(
            "/api/auth/register",
            json={
                "full_name": f"Reuse Tester {uid_suffix}",
                "email": test_email,
                "password": current_pass,
                "confirm_password": current_pass,
            },
        )
        assert reg_resp.status_code == 201, f"Register failed: {reg_resp.text}"
        print(f"  ✓ User registered with initial password: {test_email}")

        # 2. Generate a valid password reset token in DB
        from database import AsyncSessionLocal
        from database.models import User, PasswordResetToken
        from sqlalchemy import select
        from datetime import timedelta

        test_raw, test_hash = generate_reset_token()
        async with AsyncSessionLocal() as session:
            user_res = await session.execute(select(User).where(User.email == test_email))
            user = user_res.scalar_one_or_none()
            assert user is not None

            token_record = PasswordResetToken(
                user_id=user.id,
                token_hash=test_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
            )
            session.add(token_record)
            await session.commit()

        # 3. Attempt to reset password using the SAME password (must fail)
        reuse_resp = await client.post(
            "/api/auth/reset-password",
            json={
                "token": test_raw,
                "password": current_pass,
                "confirm_password": current_pass,
            },
        )
        assert reuse_resp.status_code == 400, f"Expected 400 for password reuse, got: {reuse_resp.status_code}"
        reuse_data = reuse_resp.json()
        expected_msg = "You cannot reuse your current password. Please choose a different password."
        assert reuse_data.get("detail") == expected_msg, f"Expected message '{expected_msg}', got: {reuse_data}"
        print(f"  ✓ Password reuse rejected with 400 Bad Request: \"{expected_msg}\"")

        # 4. Confirm old password remains valid when reuse is rejected
        old_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": current_pass},
        )
        assert old_login.status_code == 200, "Old password must remain valid when reuse is rejected"
        assert "access_token" in old_login.json()
        print("  ✓ Old password remains fully valid for authentication after rejected reuse attempt.")

        # 5. Confirm reset token is still active and can be used with a different password
        verify_resp = await client.get(f"/api/auth/verify-reset-token?token={test_raw}")
        assert verify_resp.status_code == 200, "Token should remain valid for retry with different password"

        # 6. Reset with a DIFFERENT password (must succeed)
        diff_resp = await client.post(
            "/api/auth/reset-password",
            json={
                "token": test_raw,
                "password": different_pass,
                "confirm_password": different_pass,
            },
        )
        assert diff_resp.status_code == 200, f"Reset with different password failed: {diff_resp.text}"
        print("  ✓ Reset with different password succeeded (200 OK).")

        # 7. Old password now rejected
        old_login_after = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": current_pass},
        )
        assert old_login_after.status_code == 401, "Old password must be rejected after successful reset"
        print("  ✓ Old password now rejected after successful reset (401 Unauthorized).")

        # 8. New password now authenticates
        new_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": different_pass},
        )
        assert new_login.status_code == 200, "New password must authenticate successfully"
        assert "access_token" in new_login.json()
        print("  ✓ User successfully logged in with new password (200 OK).")


async def main():
    print("=" * 70)
    print("RUNNING PATHIFY AI PASSWORD RESET URL & FORGOT PASSWORD WORKFLOW SUITE")
    print("=" * 70)

    test_frontend_url_env_loading()
    test_resolve_frontend_base_url()
    test_reset_token_security_and_expiry()
    await test_email_service_html_generation()
    await test_live_server_endpoints()
    await test_full_forgot_password_flow()
    await test_password_reuse_prevention()

    print("\n" + "=" * 70)
    print(">>> ALL 7 SUITES PASSED SUCCESSFULLY! <<<")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
