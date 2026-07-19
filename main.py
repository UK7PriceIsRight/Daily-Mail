#!/usr/bin/env python3
"""Lawn watering advisor for 41 Chiswick Lane, West London (85 m² fine fescue lawn)."""

import argparse
import json
import logging
import os
import re
import sys
import smtplib
import time
from base64 import urlsafe_b64decode
from datetime import date, timedelta
from email.mime.text import MIMEText
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

LAT = 51.4927
LON = -0.2678
RECIPIENTS = ["uk7priceisright@gmail.com", "uk7silvergirl@gmail.com"]
LOG_FILE = "lawn_watering.log"
WATERING_LOG_FILE = "watering_log.json"

THRESHOLD_LOW = 5.0   # mm — no action below this
THRESHOLD_MED = 12.0  # mm — moderate deficit
THRESHOLD_HIGH = 22.0 # mm — high deficit

LAWN_AREA_M2 = 85.0
HOSE_LITRES_PER_MINUTE = 15.0  # typical hose + sprinkler flow rate
MM_PER_MINUTE = HOSE_LITRES_PER_MINUTE / LAWN_AREA_M2  # 1 litre/m² == 1 mm depth

# Gmail API is used ONLY to search for/read/mark-read replies to the
# morning email. Sending still goes via SMTP (App Password) — unchanged.
GMAIL_API_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
GMAIL_API_TOKEN_FILE = "watering_token.json"
GMAIL_API_CREDENTIALS_FILE = "credentials.json"

API_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    f"&daily=et0_fao_evapotranspiration,precipitation_sum"
    f"&past_days=7&forecast_days=0&timezone=Europe%2FLondon"
)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# watering_log.json
# ---------------------------------------------------------------------------

def load_watering_log() -> dict:
    path = Path(WATERING_LOG_FILE)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read %s: %s — starting fresh", WATERING_LOG_FILE, exc)
        return {}


def save_watering_log(watering_log: dict) -> None:
    Path(WATERING_LOG_FILE).write_text(json.dumps(watering_log, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Weather / deficit
# ---------------------------------------------------------------------------

def fetch_weather_data() -> tuple[list[float], list[float], list[str]]:
    """Fetch ET0 and precipitation for the last 7 days from Open-Meteo."""
    attempts = 3
    delay = 30  # seconds between retries
    last_exc = None
    for attempt in range(attempts):
        try:
            resp = requests.get(API_URL, timeout=30)
            resp.raise_for_status()
            daily = resp.json()["daily"]
            return (
                daily["et0_fao_evapotranspiration"],
                daily["precipitation_sum"],
                daily["time"],
            )
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < attempts - 1:
                logger.warning("Open-Meteo attempt %d failed: %s — retrying in %ds", attempt + 1, exc, delay)
                time.sleep(delay)
    raise last_exc


def apply_manual_watering(dates: list[str], precip_values: list[float], watering_log: dict) -> list[float]:
    """Add any logged manual watering (mm) to precipitation on its date."""
    adjusted = list(precip_values)
    for i, day in enumerate(dates):
        entry = watering_log.get(day)
        if entry and entry.get("manual_watering_mm"):
            adjusted[i] = (adjusted[i] or 0.0) + entry["manual_watering_mm"]
    return adjusted


def calculate_deficit(et0_values: list[float], precip_values: list[float]) -> float:
    """Running cumulative deficit (mm), floored at 0 after each day with rain."""
    deficit = 0.0
    for et0, precip in zip(et0_values, precip_values):
        deficit = max(0.0, deficit + (et0 or 0.0) - (precip or 0.0))
    return round(deficit, 1)


def build_recommendation(deficit: float, header: str = "") -> tuple[str, str | None, int | None]:
    """Return (status_label, email_body_or_None, watering_minutes_or_None)."""
    today = date.today().strftime("%d %B %Y")

    if deficit < THRESHOLD_LOW:
        return "No Action Needed", None, None

    if deficit < THRESHOLD_MED:
        minutes = 20
        label = "Water 20 min"
        tip = "Early morning watering minimises evaporation and reduces fungal risk on fine fescues."
    elif deficit < THRESHOLD_HIGH:
        minutes = 35
        label = "Water 35 min"
        tip = "Water slowly on clay-loam to allow absorption without surface runoff."
    else:
        minutes = 50
        label = "URGENT – Water 50 min"
        tip = "Fine fescues are likely showing drought stress at this deficit — water today and plan again tomorrow."

    body = (
        f"{header}"
        f"Lawn Watering Advisor – {today}\n"
        f"{'=' * 50}\n\n"
        f"Cumulative water deficit (last 7 days): {deficit} mm\n"
        f"Recommended watering duration:          {minutes} minutes\n\n"
        f"Tip: {tip}\n\n"
        f"Garden details\n"
        f"--------------\n"
        f"Location : 41 Chiswick Lane, West London\n"
        f"Lawn area: ~85 m² fine fescue blend\n"
        f"           (70%+ creeping red / chewing's / hard fescue)\n"
        f"Soil type: clay-loam\n"
        f"Note     : irrigation system covers beds only — manual hose\n"
        f"           and sprinkler required for the lawn.\n\n"
        f"Deficit thresholds used\n"
        f"-----------------------\n"
        f"  < 5 mm  : no action\n"
        f"  5–12 mm : water 20 min\n"
        f" 12–22 mm : water 35 min\n"
        f"  > 22 mm : water 50 min (urgent)\n\n"
        f"Reply to this email with how long you watered (e.g. \"30 min\") and\n"
        f"it'll be credited against tomorrow's deficit. Reply \"skip\" if you\n"
        f"didn't water.\n\n"
        f"--- Automated Lawn Watering Advisor (Open-Meteo / FAO-56 ET₀) ---"
    )

    return label, body, minutes


# ---------------------------------------------------------------------------
# Reply parsing
# ---------------------------------------------------------------------------

_QUOTE_LINE_RE = re.compile(r"^On .{0,120} wrote:\s*$")
_NONE_RE = re.compile(r"\b(none|skip(?:ped)?|no water(?:ing)?|didn't water|did not water)\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")


def strip_quoted_reply(text: str) -> str:
    """Drop quoted original-message content so only the new reply text is parsed."""
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(">") or _QUOTE_LINE_RE.match(stripped):
            break
        kept.append(line)
    return "\n".join(kept).strip()


def parse_watering_reply(text: str) -> float | None:
    """Return minutes watered (0.0 for none/skip), or None if unparseable."""
    cleaned = strip_quoted_reply(text)
    if not cleaned:
        return None
    if _NONE_RE.search(cleaned):
        return 0.0
    match = _NUMBER_RE.search(cleaned)
    if match:
        return float(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Gmail API (reply tracking only — sending stays on SMTP)
# ---------------------------------------------------------------------------

def authorize_gmail_api() -> bool:
    """One-time interactive OAuth bootstrap. Run manually: python3 main.py --authorize-gmail"""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        print(f"ERROR: Gmail API libraries not installed: {exc}", file=sys.stderr)
        return False

    if not os.path.exists(GMAIL_API_CREDENTIALS_FILE):
        print(
            f"ERROR: {GMAIL_API_CREDENTIALS_FILE} not found. See README for OAuth setup.",
            file=sys.stderr,
        )
        return False

    flow = InstalledAppFlow.from_client_secrets_file(GMAIL_API_CREDENTIALS_FILE, GMAIL_API_SCOPES)
    creds = flow.run_local_server(port=0)
    Path(GMAIL_API_TOKEN_FILE).write_text(creds.to_json())
    print(f"Authorized. Saved {GMAIL_API_TOKEN_FILE} — reply tracking is now enabled.")
    return True


def get_gmail_api_service():
    """Non-interactive: build a Gmail API service from the cached token, or None on any failure."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        logger.warning("Gmail API libraries unavailable: %s — skipping reply tracking", exc)
        return None

    token_path = Path(GMAIL_API_TOKEN_FILE)
    if not token_path.exists():
        logger.warning(
            "%s not found — run `python3 main.py --authorize-gmail` once to enable reply tracking",
            GMAIL_API_TOKEN_FILE,
        )
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_API_SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                token_path.write_text(creds.to_json())
            else:
                logger.warning("Gmail API credentials invalid and not refreshable — skipping reply tracking")
                return None
        return build("gmail", "v1", credentials=creds)
    except Exception as exc:
        logger.warning("Gmail API auth/service init failed: %s — skipping reply tracking", exc)
        return None


def find_sent_message_id(service, recipient: str, attempts: int = 3, delay: float = 2.0):
    """Search Sent for the message we just SMTP-sent. Returns (message_id, thread_id) or None."""
    query = f"in:sent to:{recipient} newer_than:1d"
    for attempt in range(attempts):
        try:
            results = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
            messages = results.get("messages", [])
            if messages:
                return messages[0]["id"], messages[0]["threadId"]
        except Exception as exc:
            logger.warning("Gmail lookup of sent message failed (attempt %d): %s", attempt + 1, exc)
        if attempt < attempts - 1:
            time.sleep(delay)
    return None


def _extract_plain_text(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []) or []:
        text = _extract_plain_text(part)
        if text:
            return text
    return ""


def get_thread_reply(service, thread_id: str, original_message_id: str):
    """Return (reply_message_id, plain_text_body) for the latest reply, or None if none yet."""
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()
    messages = thread.get("messages", [])
    replies = [m for m in messages if m["id"] != original_message_id]
    if not replies:
        return None
    reply = replies[-1]
    return reply["id"], _extract_plain_text(reply["payload"])


def mark_as_read(service, message_id: str) -> None:
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def process_yesterday_reply(watering_log: dict, test_mode: bool = False) -> tuple[dict | None, bool]:
    """Check for + apply a reply to yesterday's email. Returns (yesterday_entry, just_processed)."""
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    entry = watering_log.get(yesterday_str)

    if not entry or not entry.get("thread_id") or entry.get("manual_watering_mm") is not None:
        return entry, False

    service = get_gmail_api_service()
    if service is None:
        return entry, False

    try:
        result = get_thread_reply(service, entry["thread_id"], entry["message_id"])
    except Exception as exc:
        logger.warning("Reply check failed for %s: %s — proceeding with unmodified deficit", yesterday_str, exc)
        return entry, False

    if result is None:
        return entry, False

    reply_id, body_text = result
    minutes = parse_watering_reply(body_text)

    if minutes is None:
        logger.warning("Could not parse watering reply for %s — treating as 0 min", yesterday_str)
        minutes = 0.0

    entry["manual_watering_mm"] = round(minutes * MM_PER_MINUTE, 1)

    if not test_mode:
        watering_log[yesterday_str] = entry
        try:
            mark_as_read(service, reply_id)
        except Exception as exc:
            logger.warning("Could not mark reply as read: %s", exc)

    return entry, True


def build_header(yesterday_entry: dict | None, just_processed: bool) -> str:
    if not yesterday_entry or not yesterday_entry.get("recommended_minutes"):
        return ""

    mm = yesterday_entry.get("manual_watering_mm")

    if just_processed:
        if mm:
            minutes = round(mm / MM_PER_MINUTE)
            return f"✓ Yesterday: you watered {minutes} min ({mm}mm applied). Deficit adjusted.\n\n"
        return "✓ Yesterday: you skipped watering. Noted — deficit carries forward.\n\n"

    if mm is None:
        return "ℹ️  No watering logged yesterday. Deficit carries forward.\n\n"

    return ""


# ---------------------------------------------------------------------------
# Email send (SMTP, unchanged)
# ---------------------------------------------------------------------------

def send_email(subject: str, body: str) -> None:
    """Send a plain-text email via Gmail SMTP using an App Password."""
    smtp_user = os.environ["GMAIL_USER"]
    smtp_pass = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(RECIPIENTS)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, RECIPIENTS, msg.as_string())


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run(test_mode: bool = False) -> None:
    today_str = date.today().isoformat()
    watering_log = load_watering_log()

    try:
        yesterday_entry, just_processed = process_yesterday_reply(watering_log, test_mode=test_mode)
    except Exception as exc:
        logger.warning("Reply-tracking step failed unexpectedly: %s — proceeding with unmodified deficit", exc)
        yesterday_entry, just_processed = watering_log.get((date.today() - timedelta(days=1)).isoformat()), False

    header = build_header(yesterday_entry, just_processed)

    try:
        et0_vals, precip_vals, dates = fetch_weather_data()
        adjusted_precip = apply_manual_watering(dates, precip_vals, watering_log)
        deficit = calculate_deficit(et0_vals, adjusted_precip)
        label, body, minutes = build_recommendation(deficit, header)

        if test_mode:
            print(f"[TEST] Date        : {today_str}")
            print(f"[TEST] API dates   : {dates[0]} → {dates[-1]}")
            if yesterday_entry:
                print(f"[TEST] Yesterday   : {yesterday_entry}")
            print(f"[TEST] Just processed reply: {just_processed}")
            print(f"[TEST] Deficit     : {deficit} mm")
            print(f"[TEST] Status      : {label}")
            if body:
                print(f"\n[TEST] Email that would be sent:\n{'-'*50}")
                print(f"Subject: 🌿 Lawn Watering – {today_str} – {label}")
                print(body)
            else:
                print("[TEST] No email would be sent (deficit below 5 mm threshold).")
            logger.info(
                "TEST | date=%s deficit=%.1fmm action=%s", today_str, deficit, label
            )
            return

        if body:
            subject = f"🌿 Lawn Watering – {today_str} – {label}"
            send_email(subject, body)
            logger.info(
                "date=%s deficit=%.1fmm action=EMAIL_SENT label=%s",
                today_str, deficit, label,
            )
            print(f"Email sent → {', '.join(RECIPIENTS)}  |  deficit={deficit} mm  |  {label}")

            sent_ids = None
            service = get_gmail_api_service()
            if service is not None:
                sent_ids = find_sent_message_id(service, RECIPIENTS[0])
            watering_log[today_str] = {
                "message_id": sent_ids[0] if sent_ids else None,
                "thread_id": sent_ids[1] if sent_ids else None,
                "manual_watering_mm": None,
                "recommended_minutes": minutes,
            }
        else:
            logger.info(
                "date=%s deficit=%.1fmm action=NO_ACTION label=%s",
                today_str, deficit, label,
            )
            print(f"No action needed. Deficit: {deficit} mm — lawn is well-watered.")
            watering_log[today_str] = {
                "message_id": None,
                "thread_id": None,
                "manual_watering_mm": None,
                "recommended_minutes": 0,
            }

        save_watering_log(watering_log)

    except KeyError as exc:
        msg = f"Missing environment variable: {exc}"
        logger.error("date=%s error=%s", today_str, msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as exc:
        msg = f"Open-Meteo API error: {exc}"
        logger.error("date=%s error=%s", today_str, msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)
    except smtplib.SMTPException as exc:
        msg = f"Email send failed: {exc}"
        logger.error("date=%s error=%s", today_str, msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lawn watering advisor — fetches ET₀/rain data and emails watering recommendations."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Dry run: calculate and print result without sending email or marking replies read.",
    )
    parser.add_argument(
        "--authorize-gmail",
        action="store_true",
        help="One-time interactive OAuth flow to enable reply tracking (run manually, not via cron).",
    )
    args = parser.parse_args()

    if args.authorize_gmail:
        sys.exit(0 if authorize_gmail_api() else 1)

    run(test_mode=args.test)


if __name__ == "__main__":
    main()
