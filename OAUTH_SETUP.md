# Gmail API OAuth2 Setup Instructions

This guide will walk you through setting up OAuth2 authentication for the Gmail API to use with the newsletter extraction script.

## Prerequisites

- A Google account with Gmail
- Python 3.7 or higher installed

## Step 1: Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** at the top, then click **"New Project"**
3. Enter a project name (e.g., "Gmail Newsletter Extractor")
4. Click **"Create"**

## Step 2: Enable Gmail API

1. In the Google Cloud Console, make sure your new project is selected
2. Go to **"APIs & Services" > "Library"** (or visit https://console.cloud.google.com/apis/library)
3. Search for **"Gmail API"**
4. Click on **"Gmail API"** in the results
5. Click the **"Enable"** button

## Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services" > "OAuth consent screen"**
2. Select **"External"** user type (unless you have a Google Workspace account)
3. Click **"Create"**
4. Fill in the required fields:
   - **App name**: Gmail Newsletter Extractor (or your preferred name)
   - **User support email**: Your email address
   - **Developer contact email**: Your email address
5. Click **"Save and Continue"**
6. On the **"Scopes"** page, click **"Save and Continue"** (default scopes are fine)
7. On the **"Test users"** page:
   - Click **"Add Users"**
   - Add your Gmail address
   - Click **"Save and Continue"**
8. Review the summary and click **"Back to Dashboard"**

## Step 4: Create OAuth2 Credentials

1. Go to **"APIs & Services" > "Credentials"**
2. Click **"Create Credentials"** at the top
3. Select **"OAuth client ID"**
4. For Application type, select **"Desktop app"**
5. Enter a name (e.g., "Newsletter Extractor Desktop Client")
6. Click **"Create"**
7. A dialog will appear with your client ID and client secret
8. Click **"Download JSON"**

## Step 5: Set Up Credentials File

1. Rename the downloaded JSON file to **`credentials.json`**
2. Move `credentials.json` to the same directory as `extract_newsletters.py`

**Important**: Keep this file secure and never commit it to version control!

## Step 6: Install Python Dependencies

Run the following command in your project directory:

```bash
pip install -r requirements.txt
```

## Step 7: First-Time Authentication

1. Run the script for the first time:
   ```bash
   python extract_newsletters.py
   ```

2. A browser window will open automatically
3. Log in with your Google account (the one you added as a test user)
4. You may see a warning that the app isn't verified. Click **"Advanced"** and then **"Go to [App Name] (unsafe)"**
5. Review the permissions and click **"Allow"**
6. The browser will show a success message. You can close it.

7. A `token.json` file will be created in your directory. This stores your access token for future runs.

## Step 8: Verify Setup

The script should now run and search for newsletters from the last 24 hours. Check the `newsletters/` directory for extracted emails.

## Troubleshooting

### "credentials.json not found" Error
- Make sure you downloaded the credentials file and renamed it to `credentials.json`
- Verify it's in the same directory as the script

### "Access Blocked" During Authentication
- Make sure you added your email as a test user in the OAuth consent screen
- Try using the same Google account that owns the Cloud Project

### "Invalid Grant" Error
- Delete `token.json` and run the script again to re-authenticate

### No Emails Found
- Verify you have emails from the specified sources (pucknews.com, economist.com, punchbowlnews.com, thetimes.co.uk) in the last 24 hours
- Check your Gmail to confirm the emails exist

## Security Notes

1. **Never commit `credentials.json` or `token.json` to version control**
2. Add them to your `.gitignore` file:
   ```
   credentials.json
   token.json
   ```

3. The script only requests **read-only** access to your Gmail (`gmail.readonly` scope)
4. You can revoke access anytime at https://myaccount.google.com/permissions

## Publishing the App (Optional)

If you want to use this without the "unverified app" warning:

1. Go to the OAuth consent screen in Google Cloud Console
2. Click **"Publish App"**
3. Note: For personal use with test users, publishing is not necessary

## Rate Limits

- Gmail API has usage limits (quotas)
- For free tier: 1 billion quota units per day
- Reading emails typically uses 5-10 quota units per request
- This should be more than sufficient for personal newsletter extraction

## Support

For more information, see the official documentation:
- [Gmail API Overview](https://developers.google.com/gmail/api/guides)
- [Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
