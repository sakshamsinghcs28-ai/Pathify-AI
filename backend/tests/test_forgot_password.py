"""
Test Suite for Forgot Password & Resend API Integration
"""
import asyncio
import sys
import uuid
from pathlib import Path
import httpx
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from backend.app.main import app
from backend.app.config import app_settings
from backend.app.services.email_service import send_password_reset_email
from backend.app.services.auth_service import resolve_frontend_base_url


async def run_tests():
    # 0. Test resolve_frontend_base_url sanitization
    print("[0/4] Testing resolve_frontend_base_url against null origin...")
    res = resolve_frontend_base_url(origin="null")
    assert res != "null"
    assert "null" not in res
    assert res == "http://localhost:5000"
    print("  -> Passed. Origin 'null' resolved to http://localhost:5000.")

    # 1. Test direct send_password_reset_email function with Resend API mock
    print("\n[1/4] Testing send_password_reset_email with Resend API...")
    with patch.object(app_settings, "resend_api_key", "re_test_key_12345678"):
        mock_success_resp = httpx.Response(200, json={"id": "resend_msg_abc123"})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_success_resp) as mock_post:
            result = await send_password_reset_email(
                "student_test@example.com",
                "http://localhost:5000/reset-password.html?token=sample_token_123",
            )
            assert result["id"] == "resend_msg_abc123"
            assert mock_post.called
            call_args, call_kwargs = mock_post.call_args
            assert call_args[0] == "https://api.resend.com/emails"
            assert call_kwargs["headers"]["Authorization"] == "Bearer re_test_key_12345678"
            assert call_kwargs["json"]["to"] == ["student_test@example.com"]
            assert "Reset Your Pathify AI Password" in call_kwargs["json"]["subject"]
            assert "sample_token_123" in call_kwargs["json"]["html"]
            assert "20 minutes" in call_kwargs["json"]["html"]
            print("  -> Passed. Resend API called with valid payload, headers, and 20-minute reset link.")

    # 2. Test send_password_reset_email error handling (No faking success!)
    print("\n[2/4] Testing Resend API error reporting (honest error handling)...")
    with patch.object(app_settings, "resend_api_key", "re_invalid_key"):
        mock_fail_resp = httpx.Response(401, json={"statusCode": 401, "message": "API key is invalid"})
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_fail_resp):
            try:
                await send_password_reset_email("student_test@example.com", "http://localhost:5000/reset-password.html?token=123")
                assert False, "Should have raised HTTPException"
            except HTTPException as exc:
                assert exc.status_code == 502
                assert "API key is invalid" in exc.detail
                print("  -> Passed. Resend 401 response properly converted to 502 Bad Gateway without faking delivery.")

    # 3. Test POST /api/auth/forgot-password end-to-end with Origin: null
    print("\n[3/4] Testing POST /api/auth/forgot-password route with Origin: null...")
    test_email = f"resend_test_{uuid.uuid4().hex[:6]}@pathify.test"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a fresh test user
        reg_payload = {
            "full_name": "Resend Tester",
            "email": test_email,
            "password": "InitialPassword123!",
            "confirm_password": "InitialPassword123!",
        }
        reg_res = await client.post("/api/auth/register", json=reg_payload)
        assert reg_res.status_code == 201

        # Mock email dispatch on auth_service
        with patch("backend.app.services.auth_service.send_password_reset_email", new_callable=AsyncMock) as mock_email:
            mock_email.return_value = {"id": "resend_mock_id_999"}
            res = await client.post(
                "/api/auth/forgot-password",
                json={"email": test_email},
                headers={"Origin": "null"},
            )
            assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
            data = res.json()
            assert data["success"] is True
            assert "dispatched" in data["message"] or "sent" in data["message"]
            assert mock_email.called
            called_args, called_kwargs = mock_email.call_args
            assert called_kwargs["to_email"] == test_email
            reset_url = called_kwargs["reset_url"]
            assert "null/" not in reset_url, f"Generated reset URL must NOT contain 'null/': {reset_url}"
            assert reset_url.startswith("http://localhost:5000/reset-password.html?token="), f"Invalid reset URL: {reset_url}"
            print(f"  -> Passed. /api/auth/forgot-password with Origin: null generated valid URL: {reset_url}")

            # Extract raw token from reset_url
            raw_token = reset_url.split("token=")[1]

        # 4. Test password reuse prevention: resetting with same password MUST fail
        print("\n[4/4] Testing password reuse rejection on reset-password...")
        reuse_res = await client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "password": "InitialPassword123!",
                "confirm_password": "InitialPassword123!",
            },
        )
        assert reuse_res.status_code == 400
        reuse_json = reuse_res.json()
        assert reuse_json.get("detail") == "You cannot reuse your current password. Please choose a different password."
        print("  -> Passed. Reusing current password rejected with 400 Bad Request.")

        # Confirm old password remains valid
        old_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "InitialPassword123!"},
        )
        assert old_login.status_code == 200
        print("  -> Passed. Old password remains valid after rejected reuse attempt.")

        # Resetting with a different password must succeed
        diff_res = await client.post(
            "/api/auth/reset-password",
            json={
                "token": raw_token,
                "password": "BrandNewPassword456!",
                "confirm_password": "BrandNewPassword456!",
            },
        )
        assert diff_res.status_code == 200
        print("  -> Passed. Resetting with a different password succeeded (200 OK).")

        # New password login succeeds
        new_login = await client.post(
            "/api/auth/login",
            json={"email": test_email, "password": "BrandNewPassword456!"},
        )
        assert new_login.status_code == 200
        print("  -> Passed. Login with new password succeeded.")

    print("\n" + "=" * 60)
    print("ALL FORGOT-PASSWORD & RESEND INTEGRATION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
