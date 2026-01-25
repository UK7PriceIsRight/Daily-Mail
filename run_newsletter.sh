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
