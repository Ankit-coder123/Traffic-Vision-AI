"""
Email alerts for newly reported incidents and password resets.
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
# Remove all spaces from Gmail app passwords if copy-pasted with formatting
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "TrafficVision AI").strip()

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
    if not is_configured():
        print("[email_utils] SMTP not configured, skipping incident broadcast.")
        return False

    # Filter out empty entries and undeliverable placeholder domains
    valid_recipients = [
        email.strip()
        for email in recipient_emails
        if email and "@" in email and not email.strip().lower().endswith("@trafficvision.ai")
    ]

    if not valid_recipients:
        print("[email_utils] No deliverable recipient emails found.")
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
    print(f"[email_utils] Attempting to send to: {valid_recipients}")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            for recipient in valid_recipients:
                try:
                    msg = _build_message(recipient, subject, html_body, text_body)
                    refused = server.sendmail(SMTP_USER, [recipient], msg.as_string())
                    if refused:
                        failed[recipient] = refused[recipient]
                    else:
                        sent_count += 1
                        print(f"[email_utils] Successfully sent to: {recipient}")
                except Exception as rec_err:
                    failed[recipient] = str(rec_err)
                    print(f"[email_utils] Failed delivery to {recipient}: {rec_err}")
    except Exception as e:
        print(f"[email_utils] Failed to connect/authenticate to SMTP server: {e}")
        return False

    print(f"[email_utils] Sent to {sent_count}/{len(valid_recipients)} recipients individually.")
    if failed:
        print(f"[email_utils] Delivery failures: {failed}")

    return sent_count > 0


def send_password_reset_email(recipient_email: str, reset_link: str) -> bool:
    if not is_configured():
        return False

    recipient = recipient_email.strip()
    if not recipient or recipient.lower().endswith("@trafficvision.ai"):
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
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            msg = _build_message(recipient, subject, html_body, text_body)
            refused = server.sendmail(SMTP_USER, [recipient], msg.as_string())
            return not refused
    except Exception as e:
        print(f"[email_utils] Failed to send password reset email: {e}")
        return False