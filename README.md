# Daily-Mail
Collect gmail newsletters daily

## Overview

This project automatically extracts newsletters from Gmail, saves them as text files, and uses AI to generate a concise, well-structured summary that's emailed to you. It searches for emails from specific newsletter sources in the last 24 hours, creates a 10-minute readable summary organized by topic (US Politics, UK News), and sends it as a formatted HTML email.

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
- Set up OAuth2 credentials with both `gmail.readonly` and `gmail.send` scopes
- Download your `credentials.json` file

**Important:** If you've already set up OAuth with only `gmail.readonly`, delete `token.json` and re-authenticate to get the `gmail.send` permission.

### 3. Set Up Anthropic API Key

The script uses Claude AI to generate summaries. You need an Anthropic API key:

1. Sign up at [https://console.anthropic.com](https://console.anthropic.com)
2. Generate an API key
3. Set it as an environment variable:

```bash
# Linux/Mac
export ANTHROPIC_API_KEY='your-api-key-here'

# Or add to your ~/.bashrc or ~/.zshrc for persistence
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.bashrc

# Windows (Command Prompt)
set ANTHROPIC_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="your-api-key-here"
```

### 4. First Run

```bash
python extract_newsletters.py
```

On first run, you'll be prompted to authenticate via your browser. After successful authentication, a `token.json` file will be created for subsequent runs.

The script will:
1. Fetch newsletters from the last 24 hours
2. Save them to the `newsletters/` directory
3. Generate an AI summary
4. Send the formatted summary email

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

### Local Backup Files

Each saved newsletter file (in `newsletters/` directory) contains:
- From header (sender information)
- Date received
- Subject line
- Full email body

### Email Summary

You'll receive an HTML-formatted email with:
- **Sources list** at the top
- **US Politics section** - Drawing from Puck News and Punchbowl News
- **UK News section** - Anchored in The Times, with insights from other sources
- Clean, professional formatting optimized for readability
- Approximately 10 minutes of reading time

The email is sent to `uk7priceisright@gmail.com` (configurable in the script).

## Security

- `credentials.json` and `token.json` are automatically excluded from git via `.gitignore`
- The script uses Gmail API with read and send access
- Your Anthropic API key should be stored as an environment variable
- Never commit credential files or API keys to version control

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
