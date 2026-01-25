# Quick Start Guide - macOS - Get Daily Newsletters at 5:45 AM

## Step 1: Install the Missing Anthropic Library

You're already in the Daily-Mail directory. Install the missing library:

```bash
pip install anthropic>=0.18.0
```

## Step 2: Find Your Current Directory Path

```bash
pwd
```

This will show your actual path (probably something like `/Users/Warrenhall/Daily-Mail`). **Use this path in all the steps below** instead of `/home/user/Daily-Mail`.

## Step 3: Set Your Anthropic API Key

Get your API key from [https://console.anthropic.com](https://console.anthropic.com), then:

```bash
# For zsh (default on macOS)
echo 'export ANTHROPIC_API_KEY="your-actual-api-key"' >> ~/.zshrc
source ~/.zshrc

# Or if you use bash
echo 'export ANTHROPIC_API_KEY="your-actual-api-key"' >> ~/.bashrc
source ~/.bashrc
```

## Step 4: Re-authenticate Gmail

```bash
rm -f token.json
python3 extract_newsletters.py
```

This will open your browser to authenticate with `gmail.send` permission.

## Step 5: Create macOS Wrapper Script

Update the `run_newsletter.sh` script with your actual path:

```bash
# First, find your current path
CURRENT_PATH=$(pwd)

# Create the wrapper script
cat > run_newsletter.sh << EOF
#!/bin/bash

# Load environment variables
source ~/.zshrc

# Change to script directory
cd "$CURRENT_PATH"

# Run the script and log output
/usr/bin/python3 extract_newsletters.py >> "$CURRENT_PATH/newsletter.log" 2>&1

# Add timestamp to log
echo "Completed at \$(date)" >> "$CURRENT_PATH/newsletter.log"
echo "---" >> "$CURRENT_PATH/newsletter.log"
EOF

# Make it executable
chmod +x run_newsletter.sh
```

## Step 6: Test It Works

```bash
./run_newsletter.sh
tail newsletter.log
```

Check that you received an email at uk7priceisright@gmail.com!

## Step 7: Schedule for 5:45 AM Daily with Cron

```bash
# Edit your crontab
crontab -e
```

Add this line (replace `/path/to/Daily-Mail` with your actual path from Step 2):

```
45 5 * * * /path/to/Daily-Mail/run_newsletter.sh
```

For example, if your path is `/Users/Warrenhall/Daily-Mail`:
```
45 5 * * * /Users/Warrenhall/Daily-Mail/run_newsletter.sh
```

Save and exit (press `i` to insert, type the line, press `Esc`, then type `:wq` and press Enter).

## Step 8: Verify the Setup

Check your cron job is scheduled:

```bash
crontab -l
```

## Done! 🎉

You'll now receive your AI-summarized newsletter every morning at 5:45 AM at uk7priceisright@gmail.com.

## Troubleshooting

### Check if cron is running on macOS
```bash
sudo launchctl list | grep cron
```

### View recent log entries
```bash
tail -50 newsletter.log
```

### If cron doesn't work on macOS

macOS may require additional permissions for cron. Alternative: use launchd instead.

Create a launchd plist file:

```bash
CURRENT_PATH=$(pwd)
cat > ~/Library/LaunchAgents/com.dailymail.newsletter.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailymail.newsletter</string>
    <key>ProgramArguments</key>
    <array>
        <string>$CURRENT_PATH/run_newsletter.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>5</integer>
        <key>Minute</key>
        <integer>45</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$CURRENT_PATH/newsletter.log</string>
    <key>StandardErrorPath</key>
    <string>$CURRENT_PATH/newsletter.log</string>
</dict>
</plist>
EOF

# Load the job
launchctl load ~/Library/LaunchAgents/com.dailymail.newsletter.plist
```

To check if it's loaded:
```bash
launchctl list | grep dailymail
```

To unload (if you need to make changes):
```bash
launchctl unload ~/Library/LaunchAgents/com.dailymail.newsletter.plist
```
