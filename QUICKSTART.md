# Quick Start Guide - Get Daily Newsletters at 5:45 AM

## TL;DR - Fast Setup

```bash
# 1. Install dependencies
cd /home/user/Daily-Mail
pip install -r requirements.txt

# 2. Set your Anthropic API key (get from https://console.anthropic.com)
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
source ~/.bashrc

# 3. Re-authenticate Gmail if needed
rm -f token.json
python3 extract_newsletters.py

# 4. Test it works
./run_newsletter.sh
tail newsletter.log

# 5. Schedule for 5:45 AM daily
crontab -e
# Add this line:
# 45 5 * * * /home/user/Daily-Mail/run_newsletter.sh
```

Done! You'll receive your newsletter summary at uk7priceisright@gmail.com every morning at 5:45 AM.

For detailed instructions and troubleshooting, see [SETUP_AUTOMATION.md](SETUP_AUTOMATION.md)
