import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def _get_recipients():
    """Read all recipient emails from EMAIL_RECIPIENTS (comma-separated)."""
    raw = os.getenv("EMAIL_RECIPIENTS", EMAIL_ADDRESS or "")
    return [e.strip() for e in raw.split(",") if e.strip()]


def send_morning_digest(articles):
    subject = f"KPK Pulse Morning Digest — {datetime.now().strftime('%B %d, %Y')}"
    html = _build_html(articles, "Morning Digest", "☀️")
    return _broadcast(subject, html)


def send_evening_summary(articles):
    subject = f"KPK Pulse Evening Summary — {datetime.now().strftime('%B %d, %Y')}"
    html = _build_html(articles, "Evening Summary", "🌙")
    return _broadcast(subject, html)


def send_to_specific(recipient, subject, html_body):
    """Send to a single specific address."""
    return _send_one(recipient, subject, html_body)


def _broadcast(subject, html_body):
    """Send to all configured recipients."""
    if not EMAIL_ADDRESS or "your_gmail" in (EMAIL_ADDRESS or ""):
        print(f"[email_digest] Mock email — configure EMAIL_ADDRESS in .env")
        return False
    recipients = _get_recipients()
    if not recipients:
        print("[email_digest] No EMAIL_RECIPIENTS configured.")
        return False
    results = [_send_one(r, subject, html_body) for r in recipients]
    return any(results)


def _send_one(recipient, subject, html_body):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = recipient
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())
        print(f"[email_digest] Sent to {recipient}: {subject}")
        return True
    except Exception as e:
        print(f"[email_digest] Error sending to {recipient}: {e}")
        return False


def _build_html(articles, digest_type, icon):
    now = datetime.now().strftime("%A, %B %d, %Y")
    items_html = ""
    for a in articles[:15]:
        title = a.get("title", "")
        source = a.get("source", "")
        description = a.get("description", "")[:200]
        url = a.get("url", "#")
        image_tag = ""
        if a.get("image"):
            image_tag = f'<img src="{a["image"]}" style="width:100%;max-height:160px;object-fit:cover;border-radius:6px;margin-bottom:8px;">'

        items_html += f"""
        <div style="background:#1a1f2e;border-radius:8px;padding:16px;margin-bottom:16px;border-left:4px solid #ef4444;">
          {image_tag}
          <a href="{url}" style="color:#f97316;text-decoration:none;font-size:16px;font-weight:bold;">{title}</a>
          <p style="color:#9ca3af;font-size:12px;margin:4px 0;">📰 {source}</p>
          <p style="color:#d1d5db;font-size:14px;margin:8px 0 0;">{description}</p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>KPK Pulse {digest_type}</title></head>
    <body style="background:#0f1117;font-family:Arial,sans-serif;margin:0;padding:20px;">
      <div style="max-width:600px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#ef4444,#f97316);padding:24px;border-radius:12px;text-align:center;margin-bottom:24px;">
          <h1 style="color:#fff;margin:0;font-size:28px;">{icon} KPK Pulse</h1>
          <p style="color:#fecaca;margin:8px 0 0;font-size:16px;">{digest_type} — {now}</p>
        </div>
        <div style="background:#111827;padding:20px;border-radius:12px;margin-bottom:16px;">
          <h2 style="color:#f97316;margin:0 0 16px;">Top Stories</h2>
          {items_html}
        </div>
        <p style="color:#6b7280;font-size:12px;text-align:center;">
          KPK Pulse — Real-Time KPK Media Intelligence
        </p>
      </div>
    </body>
    </html>
    """
