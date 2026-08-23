"""
Email alerts for newly reported incidents.

Uses plain smtplib (Gmail's SMTP server by default) -- no third-party
email service or paid API needed. Entirely optional: if SMTP_USER /
SMTP_PASSWORD aren't set, send_incident_alert_email() is a no-op rather
than an error, same pattern as GOOGLE_CLIENT_ID for Google Sign-In.

Design choices worth knowing:
  - One SMTP message with all recipients in BCC, not N individual sends.
    This means one SMTP transaction per incident report instead of N,
    and recipients can't see each other's addresses (privacy).
  - Called from a FastAPI BackgroundTask (see incidents.py) so a slow or
    failed email never delays or breaks the actual incident report
    request -- the API response goes out first, the email is best-effort
    afterward.
  - Gmail's regular (non-Workspace) SMTP has a ~500-recipients-per-day
    sending limit. Fine for a demo/student-project user base; would need
    a real transactional email provider (SendGrid, SES, etc.) beyond that.
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "TrafficVision AI")

SEVERITY_LABELS = {"minor": "Minor", "moderate": "Moderate", "major": "Major"}


def is_configured() -> bool:
    return bool(SMTP_USER and SMTP_PASSWORD)


def _build_message(recipient_email: str, subject: str, html_body: str, text_body: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    msg["To"] = recipient_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return msg


def send_incident_alert_email(
    recipient_emails: list,
    zone_name: str,
    incident_type: str,
    severity: str,
    description: str = None,
) -> bool:
    """
    Sends one individual email per recipient, each with their OWN address
    genuinely in the "To" field -- not a single all-Bcc broadcast.

    This was originally a single Bcc'd message (one SMTP transaction,
    "To: sender-own-address", every real recipient hidden in Bcc). That
    got a clean 250 OK from Gmail's SMTP server for every recipient, but
    real-world testing showed Gmail's receiving-side spam/security engine
    silently dropped the Bcc'd copies anyway -- not to Spam, not anywhere
    visible, just gone. That's a known pattern: Gmail is more suspicious
    of all-Bcc mail between two personal Gmail accounts where the visible
    "To" line isn't the actual recipient. Individual sends with a genuine
    "To: recipient" line are the standard, reliable pattern instead.

    Costs one SMTP send per recipient rather than one shared send -- fine
    at this project's scale (a handful of test/demo users). A production
    system with a large user base would want a real transactional email
    provider (SendGrid, SES) rather than looping raw SMTP sends.

    Returns True if at least one recipient succeeded, False if none did
    or SMTP isn't configured.
    """
    if not is_configured():
        return False
    if not recipient_emails:
        return False

    severity_label = SEVERITY_LABELS.get(severity, severity.title())
    incident_label = incident_type.replace("_", " ").title()
    subject = f"[TrafficVision AI] {severity_label} {incident_label} reported at {zone_name}"

    text_body = (
        f"A new incident has been reported on TrafficVision AI.\n\n"
        f"Location: {zone_name}\n"
        f"Type: {incident_label}\n"
        f"Severity: {severity_label}\n"
        + (f"Details: {description}\n" if description else "")
        + "\nOpen the app to view live traffic conditions and other active incidents."
    )
    html_body = f"""
    <div style="font-family: sans-serif; max-width: 480px;">
      <h2 style="margin-bottom: 4px;">New incident reported</h2>
      <p style="color: #555; margin-top: 0;">TrafficVision AI</p>
      <table style="border-collapse: collapse; margin: 12px 0;">
        <tr><td style="padding: 4px 12px 4px 0; color: #888;">Location</td><td><b>{zone_name}</b></td></tr>
        <tr><td style="padding: 4px 12px 4px 0; color: #888;">Type</td><td>{incident_label}</td></tr>
        <tr><td style="padding: 4px 12px 4px 0; color: #888;">Severity</td><td>{severity_label}</td></tr>
        {f'<tr><td style="padding: 4px 12px 4px 0; color: #888;">Details</td><td>{description}</td></tr>' if description else ''}
      </table>
      <p style="color: #888; font-size: 13px;">Open the app to view live traffic conditions and other active incidents.</p>
    </div>
    """

    sent_count = 0
    failed = {}
    print(f"[email_utils] Attempting to send to: {recipient_emails}")
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            for recipient in recipient_emails:
                msg = _build_message(recipient, subject, html_body, text_body)
                try:
                    refused = server.sendmail(SMTP_USER, [recipient], msg.as_string())
                    if refused:
                        failed[recipient] = refused[recipient]
                    else:
                        sent_count += 1
                except smtplib.SMTPException as e:
                    failed[recipient] = str(e)
    except Exception as e:
        print(f"[email_utils] Failed to connect/authenticate to SMTP server: {e}")
        return False

    print(f"[email_utils] Sent to {sent_count}/{len(recipient_emails)} recipients individually.")
    if failed:
        print(f"[email_utils] Failed for: {failed}")

    return sent_count > 0


def send_password_reset_email(recipient_email: str, reset_link: str) -> bool:
    """
    Sends a single password-reset email with a link containing the raw
    reset token as a query param. Same no-op-if-unconfigured behavior as
    send_incident_alert_email -- if SMTP isn't set up, this just returns
    False rather than raising, so local dev without email configured
    doesn't break (the forgot-password endpoint always returns a generic
    success message regardless, so this failing silently doesn't leak
    anything either).
    """
    if not is_configured():
        return False

    subject = "[TrafficVision AI] Reset your password"
    text_body = (
        "We received a request to reset your TrafficVision AI password.\n\n"
        f"Reset it here: {reset_link}\n\n"
        "This link expires in 30 minutes. If you didn't request this, "
        "you can safely ignore this email -- your password won't change."
    )
    html_body = f"""
    <div style="font-family: sans-serif; max-width: 480px;">
      <h2 style="margin-bottom: 4px;">Reset your password</h2>
      <p style="color: #555; margin-top: 0;">TrafficVision AI</p>
      <p>We received a request to reset your password. This link expires in 30 minutes.</p>
      <p style="margin: 20px 0;">
        <a href="{reset_link}" style="background: #111; color: #fff; padding: 10px 18px; border-radius: 6px; text-decoration: none;">
          Reset password
        </a>
      </p>
      <p style="color: #888; font-size: 13px;">
        If you didn't request this, you can safely ignore this email -- your password won't change.
      </p>
    </div>
    """

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            msg = _build_message(recipient_email, subject, html_body, text_body)
            refused = server.sendmail(SMTP_USER, [recipient_email], msg.as_string())
            return not refused
    except Exception as e:
        print(f"[email_utils] Failed to send password reset email: {e}")
        return False
