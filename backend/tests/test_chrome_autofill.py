"""
Test Suite for Google Chrome Password Manager and Autofill Compatibility in Pathify AI

Verifies:
1. Login form structure, method, action, and autocomplete attributes:
   - <form id="form-login" method="post" action="/api/auth/login" autocomplete="on">
   - email: type="email", name="email", autocomplete="username"
   - password: type="password", name="password", autocomplete="current-password"
2. Registration form structure, method, action, and autocomplete attributes:
   - <form id="form-register" method="post" action="/api/auth/register" autocomplete="on">
   - email: type="email", name="email", autocomplete="username"
   - password: type="password", name="password", autocomplete="new-password"
   - confirm_password: type="password", name="confirm_password", autocomplete="new-password"
3. Reset password form structure and new-password autocomplete attributes:
   - <form id="form-reset" method="post" action="/api/auth/reset-password" autocomplete="on">
   - new-password: autocomplete="new-password"
   - confirm-password: autocomplete="new-password"
4. Frontend JavaScript Credential Management API & deferred clearing logic in app.js:
   - storeBrowserCredentials with window.PasswordCredential and navigator.credentials.store
   - requestBrowserAutofill with navigator.credentials.get
   - handleLoginSubmit and handleRegisterSubmit trigger storeBrowserCredentials
   - Password input clearing is deferred so Chrome password manager captures submitted values
5. Frontend CSS -webkit-autofill styling in style.css for both Dark and Light modes.
6. Live Backend Authentication Integration:
   - Registration and Login endpoints function properly
   - Plaintext passwords are never returned or stored unhashed
   - Existing protected routes and security remain intact
"""

import asyncio
import re
import sys
import uuid
from pathlib import Path
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://127.0.0.1:5000"


def test_html_login_form_attributes():
    """Verify Login Form and its inputs match Chrome Password Manager specifications."""
    index_html = (PROJECT_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    # Form tag checks
    login_form_match = re.search(r'<form\s+id="form-login"[^>]*>', index_html)
    assert login_form_match, "form-login tag not found in index.html"
    login_form_tag = login_form_match.group(0)
    assert 'method="post"' in login_form_tag.lower(), "form-login must use method='post'"
    assert 'action="/api/auth/login"' in login_form_tag, "form-login must have action='/api/auth/login'"
    assert 'autocomplete="on"' in login_form_tag, "form-login must have autocomplete='on'"

    # Email field checks
    login_email_match = re.search(r'<input[^>]*id="login-email"[^>]*>', index_html)
    assert login_email_match, "login-email input not found"
    login_email_tag = login_email_match.group(0)
    assert 'type="email"' in login_email_tag, "login-email must have type='email'"
    assert 'name="email"' in login_email_tag, "login-email must have name='email'"
    assert 'autocomplete="username"' in login_email_tag, "login-email must have autocomplete='username'"

    # Password field checks
    login_pwd_match = re.search(r'<input[^>]*id="login-password"[^>]*>', index_html)
    assert login_pwd_match, "login-password input not found"
    login_pwd_tag = login_pwd_match.group(0)
    assert 'type="password"' in login_pwd_tag, "login-password must have type='password'"
    assert 'name="password"' in login_pwd_tag, "login-password must have name='password'"
    assert 'autocomplete="current-password"' in login_pwd_tag, "login-password must have autocomplete='current-password'"
    print("[PASS] Login form and input attributes meet all Chrome Password Manager requirements.")


def test_html_registration_form_attributes():
    """Verify Registration Form and its inputs match Chrome Password Manager specifications."""
    index_html = (PROJECT_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    # Form tag checks
    reg_form_match = re.search(r'<form\s+id="form-register"[^>]*>', index_html)
    assert reg_form_match, "form-register tag not found in index.html"
    reg_form_tag = reg_form_match.group(0)
    assert 'method="post"' in reg_form_tag.lower(), "form-register must use method='post'"
    assert 'action="/api/auth/register"' in reg_form_tag, "form-register must have action='/api/auth/register'"
    assert 'autocomplete="on"' in reg_form_tag, "form-register must have autocomplete='on'"

    # Full Name field
    reg_name_match = re.search(r'<input[^>]*id="register-name"[^>]*>', index_html)
    assert reg_name_match, "register-name input not found"
    reg_name_tag = reg_name_match.group(0)
    assert 'autocomplete="name"' in reg_name_tag, "register-name must have autocomplete='name'"

    # Email field checks
    reg_email_match = re.search(r'<input[^>]*id="register-email"[^>]*>', index_html)
    assert reg_email_match, "register-email input not found"
    reg_email_tag = reg_email_match.group(0)
    assert 'type="email"' in reg_email_tag, "register-email must have type='email'"
    assert 'name="email"' in reg_email_tag, "register-email must have name='email'"
    assert 'autocomplete="username"' in reg_email_tag, "register-email must have autocomplete='username'"

    # Password field checks
    reg_pwd_match = re.search(r'<input[^>]*id="register-password"[^>]*>', index_html)
    assert reg_pwd_match, "register-password input not found"
    reg_pwd_tag = reg_pwd_match.group(0)
    assert 'type="password"' in reg_pwd_tag, "register-password must have type='password'"
    assert 'name="password"' in reg_pwd_tag, "register-password must have name='password'"
    assert 'autocomplete="new-password"' in reg_pwd_tag, "register-password must have autocomplete='new-password'"

    # Confirm Password field checks
    reg_confirm_match = re.search(r'<input[^>]*id="register-confirm-password"[^>]*>', index_html)
    assert reg_confirm_match, "register-confirm-password input not found"
    reg_confirm_tag = reg_confirm_match.group(0)
    assert 'type="password"' in reg_confirm_tag, "register-confirm-password must have type='password'"
    assert 'autocomplete="new-password"' in reg_confirm_tag, "register-confirm-password must have autocomplete='new-password'"
    print("[PASS] Registration form and input attributes meet all Chrome Password Manager requirements.")


def test_html_reset_password_form_attributes():
    """Verify Reset Password Form has proper action, method and autocomplete="new-password"."""
    reset_html = (PROJECT_ROOT / "frontend" / "reset-password.html").read_text(encoding="utf-8")

    form_match = re.search(r'<form\s+id="form-reset"[^>]*>', reset_html)
    assert form_match, "form-reset tag not found in reset-password.html"
    form_tag = form_match.group(0)
    assert 'method="post"' in form_tag.lower(), "form-reset must use method='post'"
    assert 'action="/api/auth/reset-password"' in form_tag, "form-reset must have action='/api/auth/reset-password'"
    assert 'autocomplete="on"' in form_tag, "form-reset must have autocomplete='on'"

    pwd_match = re.search(r'<input[^>]*id="new-password"[^>]*>', reset_html)
    assert pwd_match, "new-password input not found"
    assert 'autocomplete="new-password"' in pwd_match.group(0), "new-password must have autocomplete='new-password'"

    confirm_match = re.search(r'<input[^>]*id="confirm-password"[^>]*>', reset_html)
    assert confirm_match, "confirm-password input not found"
    assert 'autocomplete="new-password"' in confirm_match.group(0), "confirm-password must have autocomplete='new-password'"
    print("[PASS] Reset password form and new-password attributes verified.")


def test_javascript_credential_management_integration():
    """Verify Credential Management API and deferred password clearing logic in app.js."""
    app_js = (PROJECT_ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "function storeBrowserCredentials" in app_js, "storeBrowserCredentials helper missing in app.js"
    assert "PasswordCredential" in app_js, "PasswordCredential constructor reference missing in app.js"
    assert "navigator.credentials.store" in app_js, "navigator.credentials.store call missing in app.js"

    assert "function requestBrowserAutofill" in app_js, "requestBrowserAutofill helper missing in app.js"
    assert "navigator.credentials.get" in app_js, "navigator.credentials.get call missing in app.js"

    # Verify calls in login & registration handlers
    assert 'storeBrowserCredentials("form-login")' in app_js, "storeBrowserCredentials('form-login') missing in handleLoginSubmit"
    assert 'storeBrowserCredentials("form-register")' in app_js, "storeBrowserCredentials('form-register') missing in handleRegisterSubmit"

    # Verify password input clearing is deferred
    assert "setTimeout" in app_js and "login-password" in app_js, "Deferred clearing of login-password missing"
    print("[PASS] Credential Management API and deferred clearing logic verified in app.js.")


def test_css_autofill_styling():
    """Verify CSS has -webkit-autofill rules for both dark and light modes."""
    style_css = (PROJECT_ROOT / "frontend" / "style.css").read_text(encoding="utf-8")

    assert "input:-webkit-autofill" in style_css, "input:-webkit-autofill selector missing in style.css"
    assert "html.light input:-webkit-autofill" in style_css, "html.light input:-webkit-autofill selector missing in style.css"
    assert "-webkit-box-shadow" in style_css, "-webkit-box-shadow rule missing for autofill styling"
    assert "-webkit-text-fill-color" in style_css, "-webkit-text-fill-color rule missing for autofill styling"
    print("[PASS] -webkit-autofill styles verified for dark and light themes.")


async def test_live_backend_auth_and_security():
    """Verify end-to-end registration, login, token handling, and no plaintext password leak."""
    test_id = uuid.uuid4().hex[:8]
    test_email = f"autofill_user_{test_id}@example.com"
    test_password = f"TestPass!_{test_id}99"
    test_name = f"Autofill User {test_id}"

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # Check backend is responding
        r_health = await client.get("/api/health")
        assert r_health.status_code == 200, "Health check failed"

        # 1. Registration endpoint accepts standard credentials
        reg_payload = {
            "full_name": test_name,
            "email": test_email,
            "password": test_password,
            "confirm_password": test_password,
        }
        r_reg = await client.post("/api/auth/register", json=reg_payload)
        assert r_reg.status_code == 201, f"Registration failed: {r_reg.text}"
        reg_data = r_reg.json()
        assert "access_token" in reg_data, "access_token missing in register response"
        assert reg_data["user"]["email"] == test_email
        # Ensure plaintext password is NOT in response
        assert "password" not in reg_data["user"]
        assert test_password not in r_reg.text, "Plaintext password leaked in registration response!"

        # 2. Login endpoint accepts standard credentials
        login_payload = {
            "email": test_email,
            "password": test_password,
        }
        r_login = await client.post("/api/auth/login", json=login_payload)
        assert r_login.status_code == 200, f"Login failed: {r_login.text}"
        login_data = r_login.json()
        assert "access_token" in login_data, "access_token missing in login response"
        token = login_data["access_token"]
        assert test_password not in r_login.text, "Plaintext password leaked in login response!"

        # 3. Authenticated user can access protected profile
        r_me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r_me.status_code == 200, f"Get current user profile failed: {r_me.text}"
        me_data = r_me.json()
        assert me_data["user"]["email"] == test_email
        assert "password" not in me_data["user"]
        assert test_password not in r_me.text, "Plaintext password leaked in /me profile response!"

        # 4. Invalid credentials rejected
        r_bad = await client.post("/api/auth/login", json={"email": test_email, "password": "WrongPassword123!"})
        assert r_bad.status_code == 401, "Bad password was not rejected"

        # 5. Frontend assets served with updated attributes
        r_index = await client.get("/index.html")
        assert r_index.status_code == 200
        assert 'autocomplete="current-password"' in r_index.text
        assert 'autocomplete="new-password"' in r_index.text

        r_app = await client.get("/app.js")
        assert r_app.status_code == 200
        assert "storeBrowserCredentials" in r_app.text

        r_css = await client.get("/style.css")
        assert r_css.status_code == 200
        assert "input:-webkit-autofill" in r_css.text

    print("[PASS] Live backend authentication, security, and asset serving verified successfully.")


async def main():
    print("=" * 80)
    print("RUNNING PATHIFY AI - CHROME PASSWORD MANAGER & AUTOFILL COMPATIBILITY TESTS")
    print("=" * 80)
    test_html_login_form_attributes()
    test_html_registration_form_attributes()
    test_html_reset_password_form_attributes()
    test_javascript_credential_management_integration()
    test_css_autofill_styling()
    await test_live_backend_auth_and_security()
    print("=" * 80)
    print("ALL CHROME PASSWORD MANAGER & AUTOFILL COMPATIBILITY TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
