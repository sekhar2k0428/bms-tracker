"""Telegram + Email notification helpers. Both are no-ops if unconfigured."""

import smtplib
from email.mime.text import MIMEText
import requests


def send_telegram(token: str, chat_ids_str: str, text: str) -> None:
    if not token or not chat_ids_str:
        print("  Telegram not configured — skipping.")
        return
    
    # Split by comma to support multiple recipient IDs (personal + group chats)
    chat_ids = [cid.strip() for cid in chat_ids_str.split(",") if cid.strip()]
    for chat_id in chat_ids:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=15,
            )
            if resp.status_code != 200:
                print(f"  Telegram send failed for {chat_id}: {resp.status_code} {resp.text}")
            else:
                print(f"  Telegram notification sent successfully to {chat_id}")
        except requests.RequestException as e:
            print(f"  Telegram send failed for {chat_id}: {e}")


def send_email(host: str, port: int, user: str, password: str, to_addr: str,
                subject: str, body: str) -> None:
    if not (user and password and to_addr):
        print("  Email not configured — skipping.")
        return
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, [to_addr], msg.as_string())
    except Exception as e:
        print(f"  Email send failed: {e}")
