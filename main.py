#!/usr/bin/env python3
"""Lawn watering advisor for 41 Chiswick Lane, West London (85 m² fine fescue lawn)."""

import argparse
import logging
import os
import smtplib
import sys
from datetime import date
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv

load_dotenv()

LAT = 51.4927
LON = -0.2678
RECIPIENTS = ["uk7priceisright@gmail.com", "uk7silvergirl@gmail.com"]
LOG_FILE = "lawn_watering.log"

THRESHOLD_LOW = 5.0   # mm — no action below this
THRESHOLD_MED = 12.0  # mm — moderate deficit
THRESHOLD_HIGH = 22.0 # mm — high deficit

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


def fetch_weather_data() -> tuple[list[float], list[float], list[str]]:
    """Fetch ET0 and precipitation for the last 7 days from Open-Meteo."""
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    daily = resp.json()["daily"]
    return (
        daily["et0_fao_evapotranspiration"],
        daily["precipitation_sum"],
        daily["time"],
    )


def calculate_deficit(et0_values: list[float], precip_values: list[float]) -> float:
    """Running cumulative deficit (mm), floored at 0 after each day with rain."""
    deficit = 0.0
    for et0, precip in zip(et0_values, precip_values):
        deficit = max(0.0, deficit + (et0 or 0.0) - (precip or 0.0))
    return round(deficit, 1)


def build_recommendation(deficit: float) -> tuple[str, str | None, int | None]:
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
        f"--- Automated Lawn Watering Advisor (Open-Meteo / FAO-56 ET₀) ---"
    )

    return label, body, minutes


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


def run(test_mode: bool = False) -> None:
    today_str = date.today().isoformat()
    try:
        et0_vals, precip_vals, dates = fetch_weather_data()
        deficit = calculate_deficit(et0_vals, precip_vals)
        label, body, minutes = build_recommendation(deficit)

        if test_mode:
            print(f"[TEST] Date        : {today_str}")
            print(f"[TEST] API dates   : {dates[0]} → {dates[-1]}")
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
            print(f"Email sent → {RECIPIENT}  |  deficit={deficit} mm  |  {label}")
        else:
            logger.info(
                "date=%s deficit=%.1fmm action=NO_ACTION label=%s",
                today_str, deficit, label,
            )
            print(f"No action needed. Deficit: {deficit} mm — lawn is well-watered.")

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
        help="Dry run: calculate and print result without sending email.",
    )
    args = parser.parse_args()
    run(test_mode=args.test)


if __name__ == "__main__":
    main()
