# Daily-Mail
Collect gmail newsletters daily

## Overview

This project automatically extracts newsletters from Gmail and saves them as text files for easy reading and archiving. It searches for emails from specific newsletter sources in the last 24 hours and organizes them in a local folder.

## Supported Newsletter Sources

- pucknews.com
- economist.com
- punchbowlnews.com
- thetimes.co.uk

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Gmail API Access

Follow the detailed instructions in [OAUTH_SETUP.md](OAUTH_SETUP.md) to:
- Create a Google Cloud project
- Enable the Gmail API
- Set up OAuth2 credentials
- Download your `credentials.json` file

### 3. First Run

```bash
python extract_newsletters.py
```

On first run, you'll be prompted to authenticate via your browser. After successful authentication, a `token.json` file will be created for subsequent runs.

## Usage

Run the script anytime to extract newsletters from the last 24 hours:

```bash
python extract_newsletters.py
```

Extracted newsletters will be saved in the `newsletters/` directory with filenames formatted as:
```
YYYYMMDD_HHMMSS_domain_subject.txt
```

Example:
```
20260120_143022_economist.com_The_world_in_brief.txt
```

## Output Format

Each saved newsletter file contains:
- From header (sender information)
- Date received
- Subject line
- Full email body

## Security

- `credentials.json` and `token.json` are automatically excluded from git via `.gitignore`
- The script uses read-only Gmail API access
- Never commit your credential files to version control

## Scheduling (Optional)

To run this script daily automatically, you can set up a cron job (Linux/Mac) or Task Scheduler (Windows).

### Linux/Mac Cron Example

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 9 AM
0 9 * * * cd /path/to/Daily-Mail && /usr/bin/python3 extract_newsletters.py
```

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to Daily
4. Set action to run `python.exe` with argument `extract_newsletters.py`
5. Set start in directory to your project folder

## Troubleshooting

See [OAUTH_SETUP.md](OAUTH_SETUP.md) for common issues and solutions.

## License

This project is for personal use.

---

# Lawn Watering Advisor

Automated morning watering advisor for the 85 m² fine fescue lawn at 41 Chiswick Lane, West London. Every morning at 7 am it fetches the last 7 days of FAO-56 evapotranspiration (ET₀) and rainfall data from [Open-Meteo](https://open-meteo.com) (free, no API key required), calculates the cumulative water deficit, and sends a plain-text email alert when action is needed.

## Watering thresholds

| Deficit (mm) | Action |
|---|---|
| < 5 | No email — lawn is fine |
| 5–12 | Email: water 20 min with hose and sprinkler |
| 12–22 | Email: water 35 min today |
| > 22 | Email: water 50 min, urgent |

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Gmail App Password

> App Passwords let a script send email through your Gmail account without using your main password or OAuth flow. They require 2-Step Verification to be enabled on the account.

1. Go to your Google Account → **Security** → **2-Step Verification** (enable if not already on).
2. Back on the Security page, scroll to **App passwords** (or visit <https://myaccount.google.com/apppasswords>).
3. Choose app: **Mail**, device: **Other** (type "Lawn Advisor"), click **Generate**.
4. Copy the 16-character password shown — you won't see it again.

### 3. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in your Gmail address and the App Password you just generated:

```
GMAIL_USER=your.gmail.address@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

`.env` is excluded from git by `.gitignore` — never commit it.

### 4. Test manually

```bash
python main.py --test
```

This fetches live data, calculates the deficit, and prints what the email *would* say — without actually sending anything. No credentials needed for `--test` mode when deficit is below threshold (no email path is reached).

### 5. Schedule with cron (runs every day at 7 am)

```bash
crontab -e
```

Add this line (replace `/path/to/Daily-Mail` with the actual path):

```
0 6 * * * cd /path/to/Daily-Mail && /usr/bin/python3 main.py
```

To find the correct Python path: `which python3`

### 6. Check the log

Each run appends a line to `lawn_watering.log` in the project directory:

```
2026-05-11 07:00:01 INFO date=2026-05-11 deficit=8.3mm action=EMAIL_SENT label=Water 20 min
2026-05-12 07:00:01 INFO date=2026-05-12 deficit=0.0mm action=NO_ACTION label=No Action Needed
```

## Garden context

- **Location**: 41 Chiswick Lane, Chiswick, West London (lat 51.4927, lon −0.2678)
- **Lawn**: ~85 m² fine fescue blend (70%+ creeping red / chewing's / hard fescue)
- **Soil**: clay-loam
- **Irrigation**: automated system covers beds only — manual hose/sprinkler needed for lawn
- **Stress onset**: fine fescues begin showing drought stress at ~15 mm cumulative deficit

## Replying to log manual watering (optional)

You can reply to the morning email with how long you watered (e.g. `"watered 30 min"`, `"30"`, `"did 25 mins"`) or `"skip"` if you didn't. The next morning's run reads that reply, credits it against the deficit (at 15 L/min over 85 m² ≈ 0.18 mm/min), and confirms it at the top of that day's email.

This feature needs read/modify access to your Gmail inbox (to find the reply and mark it read), in addition to the SMTP App Password already used for sending — sending is unchanged.

### One-time setup

1. You need the same `credentials.json` OAuth client used for `extract_newsletters.py`. If you don't have one yet, follow [OAUTH_SETUP.md](OAUTH_SETUP.md) — the same client works for both scripts.
2. Run the bootstrap command once, interactively (not via cron):
   ```bash
   python3 main.py --authorize-gmail
   ```
3. A browser window opens — log in and approve access. This creates `watering_token.json`, which cron will reuse silently afterwards.

If you skip this step, the watering advisor still works exactly as before — replies are just never picked up (a warning is logged, the deficit calculation is unaffected).

### watering_log.json

A small JSON file tracking each day's sent message/thread IDs and any manual watering logged:

```json
{
  "2026-06-18": {
    "message_id": "18e4f2a3b1c...",
    "thread_id": "18e4f2a3b1c...",
    "manual_watering_mm": 5.3,
    "recommended_minutes": 35
  }
}
```

It's plain JSON — safe to open and hand-edit if you ever need to correct an entry.
