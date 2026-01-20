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
