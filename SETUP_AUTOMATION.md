# Automated Daily Newsletter Setup

Follow these steps to receive your newsletter summary every morning at 5:45 AM.

## Step 1: Install Dependencies

```bash
cd /home/user/Daily-Mail
pip install -r requirements.txt
```

## Step 2: Set Up Anthropic API Key

1. Get your API key from [https://console.anthropic.com](https://console.anthropic.com)
2. Add it to your shell profile for persistence:

```bash
# Add to ~/.bashrc (or ~/.zshrc if you use zsh)
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**Replace `your-api-key-here` with your actual API key!**

## Step 3: Re-authenticate Gmail (if needed)

If you previously authenticated with only `gmail.readonly` scope, delete the token and re-authenticate:

```bash
cd /home/user/Daily-Mail
rm -f token.json
python3 extract_newsletters.py
```

This will open your browser to authenticate with the new `gmail.send` permission.

## Step 4: Set Up Cron Job for Daily Execution

Create a shell script wrapper that ensures the environment is set up correctly:

```bash
# Create the wrapper script
cat > /home/user/Daily-Mail/run_newsletter.sh << 'EOF'
#!/bin/bash

# Load environment variables
source ~/.bashrc

# Change to script directory
cd /home/user/Daily-Mail

# Run the script and log output
/usr/bin/python3 extract_newsletters.py >> /home/user/Daily-Mail/newsletter.log 2>&1

# Add timestamp to log
echo "Completed at $(date)" >> /home/user/Daily-Mail/newsletter.log
echo "---" >> /home/user/Daily-Mail/newsletter.log
EOF

# Make it executable
chmod +x /home/user/Daily-Mail/run_newsletter.sh
```

Now add the cron job to run at 5:45 AM daily:

```bash
# Edit your crontab
crontab -e

# Add this line (paste it in the editor that opens):
45 5 * * * /home/user/Daily-Mail/run_newsletter.sh
```

### Understanding the Cron Syntax

```
45 5 * * *
│  │ │ │ │
│  │ │ │ └─── Day of week (0-7, Sunday=0 or 7)
│  │ │ └───── Month (1-12)
│  │ └─────── Day of month (1-31)
│  └───────── Hour (0-23)
└─────────── Minute (0-59)
```

So `45 5 * * *` means: "Run at 5:45 AM every day"

## Step 5: Verify the Setup

Test that everything works manually first:

```bash
# Run the wrapper script manually
/home/user/Daily-Mail/run_newsletter.sh

# Check the log
tail -f /home/user/Daily-Mail/newsletter.log
```

You should see:
1. Authentication success
2. Newsletters being extracted
3. AI summary being generated
4. Email being sent to uk7priceisright@gmail.com

## Step 6: Check Your Email

Within a minute or two, check `uk7priceisright@gmail.com` for your newsletter summary!

## Troubleshooting

### Check if cron job is scheduled
```bash
crontab -l
```

### View recent log entries
```bash
tail -50 /home/user/Daily-Mail/newsletter.log
```

### Test environment variables in cron
```bash
# Add this temporary test to see if env vars are loaded
45 5 * * * echo $ANTHROPIC_API_KEY > /tmp/cron_test.txt
```

### Common Issues

1. **"ANTHROPIC_API_KEY environment variable not set"**
   - Make sure the key is in your ~/.bashrc
   - Make sure the wrapper script sources ~/.bashrc

2. **"No newsletters found"**
   - The script only looks for emails from the last 24 hours
   - Check that you're receiving newsletters from the configured sources

3. **Gmail authentication errors**
   - Re-run the authentication: `rm token.json && python3 extract_newsletters.py`
   - Make sure both `gmail.readonly` and `gmail.send` scopes are enabled

4. **Cron job not running**
   - Check cron is running: `sudo systemctl status cron`
   - Check system logs: `grep CRON /var/log/syslog`

## Optional: Different Schedule Times

Want to run at a different time? Modify the cron schedule:

- **Every day at 6:00 AM**: `0 6 * * *`
- **Every weekday at 7:30 AM**: `30 7 * * 1-5`
- **Twice daily (6 AM and 6 PM)**: `0 6,18 * * *`

## Managing Newsletter Sources

To add or remove sources, edit the `NEWSLETTER_SOURCES` list in `extract_newsletters.py`:

```python
NEWSLETTER_SOURCES = [
    'pucknews.com',
    'economist.com',
    'punchbowlnews.com',
    'thetimes.co.uk',
    # Add more here...
]
```

After making changes, commit them to your repository:

```bash
git add extract_newsletters.py
git commit -m "Update newsletter sources"
git push
```
