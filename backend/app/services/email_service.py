import logging
import httpx
from fastapi import HTTPException, status
from backend.app.config import app_settings

logger = logging.getLogger("pathify.email")


async def send_password_reset_email(to_email: str, reset_url: str) -> dict:
    """Send a real password reset email via the Resend API."""
    api_key = app_settings.resend_api_key.strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Resend API key is not configured on the server. "
                "Please configure RESEND_API_KEY in your .env file to enable password reset emails."
            ),
        )

    raw_from = app_settings.resend_from_email.strip() or "Pathify AI <onboarding@resend.dev>"
    if "<" not in raw_from and "@" in raw_from:
        from_email = f"Pathify AI <{raw_from}>"
    else:
        from_email = raw_from
    subject = "Reset Your Pathify AI Password"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your Password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f8fafc; margin: 0; padding: 40px 16px;">
  <div style="max-width: 540px; margin: 0 auto; background: #131c2e; border-radius: 20px; border: 1px solid #1e293b; padding: 36px 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
    <div style="margin-bottom: 24px; text-align: center;">
      <h2 style="margin: 0; font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">
        Pathify<span style="color: #6366f1;">.AI</span>
      </h2>
      <p style="margin: 6px 0 0; font-size: 11px; color: #818cf8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600;">
        Career Roadmap &amp; Skill Mapping Engine
      </p>
    </div>

    <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 12px; padding: 12px 16px; margin-bottom: 20px; text-align: center;">
      <span style="font-size: 13px; font-weight: 600; color: #a5b4fc;">Password Reset Request</span>
    </div>

    <p style="font-size: 14px; line-height: 1.6; color: #cbd5e1; margin-bottom: 24px;">
      Hello,<br><br>
      We received a request to reset the password for your Pathify AI student account. Click the button below to choose a new, secure password.
    </p>

    <div style="text-align: center; margin: 32px 0;">
      <a href="{reset_url}" style="background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; font-size: 14px; font-weight: 700; border-radius: 12px; display: inline-block; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);">
        Reset Password
      </a>
    </div>

    <p style="font-size: 12px; line-height: 1.6; color: #94a3b8; margin-bottom: 24px;">
      <strong>Note:</strong> This link is single-use and will expire in <strong>20 minutes</strong>. If you did not make this request, you can safely ignore this email and your password will remain unchanged.
    </p>

    <div style="background: #0b0f19; border: 1px solid #1e293b; border-radius: 10px; padding: 12px; margin-bottom: 24px;">
      <p style="margin: 0; font-size: 11px; color: #64748b; word-break: break-all;">
        If the button does not work, copy and paste this URL into your browser:<br>
        <a href="{reset_url}" style="color: #6366f1;">{reset_url}</a>
      </p>
    </div>

    <hr style="border: 0; border-top: 1px solid #1e293b; margin: 24px 0 16px;">

    <p style="font-size: 11px; text-align: center; color: #475569; margin: 0;">
      Pathify AI &bull; Automated System Notification &bull; Do not reply to this email.
    </p>
  </div>
</body>
</html>"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
        except httpx.RequestError as exc:
            logger.exception(f"Resend network request failed: {exc}")
            detail_msg = (
                f"Unable to reach Resend API: {str(exc)}"
                if app_settings.debug
                else "Unable to reach the email delivery service. Please try again later."
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail_msg,
            )

        if response.status_code not in (200, 201):
            logger.error(f"Resend email dispatch error: {response.text}")
            error_detail = response.text
            try:
                err_json = response.json()
                error_detail = err_json.get("message") or err_json.get("name") or error_detail
            except Exception:
                pass
            detail_msg = (
                f"Resend email dispatch error: {error_detail}"
                if app_settings.debug
                else "Unable to send email. Please verify your address or try again later."
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail_msg,
            )

        return response.json()
