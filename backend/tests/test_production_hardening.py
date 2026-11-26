"""Unit and integration test verifying production hardening:
1. Rejection of hardcoded or missing JWT secrets in production mode.
2. Secure CORS configuration without wildcard credentials.
3. Prevention of internal exception details from leaking to users in 500/503 responses.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from starlette.requests import Request
from backend.app.config import AppSettings, app_settings
from backend.app.main import global_unhandled_exception_handler


def assert_raises(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception:
        return
    raise AssertionError(f"Expected exception was not raised by {fn}")


def test_jwt_production_validation():
    # 1. In production, missing or insecure key must be rejected
    os.environ["ENVIRONMENT"] = "production"
    try:
        # Insecure default string
        assert_raises(AppSettings, jwt_secret_key="pathify-ai-secret-key-prod-2026-supersecure")

        # Empty string
        assert_raises(AppSettings, jwt_secret_key="")

        # Short key (< 32 chars)
        assert_raises(AppSettings, jwt_secret_key="short-secret-key")

        # Valid high-entropy key
        valid_settings = AppSettings(jwt_secret_key="a" * 64)
        assert valid_settings.jwt_secret_key == "a" * 64
        print("  ✓ Production mode strictly rejects insecure or missing JWT secret keys.", flush=True)
    finally:
        os.environ["ENVIRONMENT"] = "development"

    # 2. In development, dynamic ephemeral secret generated if missing
    dev_settings = AppSettings(jwt_secret_key="")
    assert len(dev_settings.jwt_secret_key) >= 32
    print("  ✓ Development mode generates a secure dynamic key when omitted.", flush=True)


def test_cors_configuration():
    # 1. Comma-separated CORS string parsed properly
    s1 = AppSettings(cors_origins="https://pathify.ai, https://example.com, *")
    # Wildcard '*' must be stripped
    assert "*" not in s1.cors_origins
    assert "https://pathify.ai" in s1.cors_origins
    assert "https://example.com" in s1.cors_origins
    print("  ✓ Wildcard '*' stripped from CORS origins when credentials are enabled.", flush=True)

    # 2. Active app_settings has secure origins and regex
    assert "*" not in app_settings.cors_origins
    assert "http://localhost:5000" in app_settings.cors_origins
    assert app_settings.cors_origin_regex is not None
    print("  ✓ AppSettings CORS origins are verified safe for production.", flush=True)


def test_exception_masking_in_production():
    original_debug = app_settings.debug
    try:
        scope = {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "server": ("127.0.0.1", 5000),
            "path": "/api/test-failure",
            "headers": [],
        }
        req = Request(scope)
        sensitive_exc = RuntimeError("Database connection password=SuperSecret123 host=internal-pg-srv failed")

        # 1. When debug is False (production default)
        app_settings.debug = False
        coro = global_unhandled_exception_handler(req, sensitive_exc)
        try:
            coro.send(None)
        except StopIteration as e:
            res = e.value

        assert res.status_code == 500
        data = json.loads(res.body.decode("utf-8"))
        assert data["success"] is False
        assert "SuperSecret123" not in data["detail"]
        assert "internal-pg-srv" not in data["detail"]
        assert data["detail"] == "An internal server error occurred. Please try again later."
        print("  ✓ Global unhandled exception handler masks internal details when debug=False.", flush=True)

        # 2. When debug is True (development)
        app_settings.debug = True
        coro_dev = global_unhandled_exception_handler(req, sensitive_exc)
        try:
            coro_dev.send(None)
        except StopIteration as e:
            res_dev = e.value

        data_dev = json.loads(res_dev.body.decode("utf-8"))
        assert "SuperSecret123" in data_dev["detail"]
        print("  ✓ Global unhandled exception handler retains detail when debug=True for local troubleshooting.", flush=True)
    finally:
        app_settings.debug = original_debug


if __name__ == "__main__":
    print("\n--- Running Production Hardening Tests ---", flush=True)
    test_jwt_production_validation()
    test_cors_configuration()
    test_exception_masking_in_production()
    print("\nALL PRODUCTION HARDENING TESTS PASSED!\n", flush=True)
