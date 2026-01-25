#!/usr/bin/env python3
"""
Gmail Newsletter Extractor and Summarizer

This script connects to Gmail via the Gmail API and extracts newsletters
from specific sources (pucknews.com, economist.com, punchbowlnews.com, thetimes.co.uk)
from the last 24 hours. It saves them to separate text files and uses AI (Claude)
to generate a concise, well-structured HTML summary organized by US Politics and UK News,
which is then sent via email.

Requirements:
- ANTHROPIC_API_KEY environment variable must be set
"""

import os
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from html.parser import HTMLParser
import anthropic

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

# Newsletter sources to search for
NEWSLETTER_SOURCES = [
    'pucknews.com',
    'economist.com',
    'punchbowlnews.com',
    'thetimes.co.uk'
]


def get_gmail_service():
    """
    Authenticate and return Gmail API service instance.

    Returns:
        Resource: Gmail API service instance
    """
    creds = None

    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please follow OAuth2 setup instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def build_search_query():
    """
    Build Gmail search query for the last 24 hours from specified sources.

    Returns:
        str: Gmail search query string
    """
    # Calculate date for 24 hours ago
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y/%m/%d')

    # Build query with OR conditions for each source
    from_queries = ' OR '.join([f'from:{source}' for source in NEWSLETTER_SOURCES])

    # Combine with date filter
    query = f'({from_queries}) after:{date_str}'

    return query


def extract_email_body(payload):
    """
    Recursively extract email body from message payload.

    Args:
        payload (dict): Message payload from Gmail API

    Returns:
        str: Extracted email body text
    """
    body = ""

    if 'parts' in payload:
        for part in payload['parts']:
            body += extract_email_body(part)
    else:
        if payload.get('mimeType') in ['text/plain', 'text/html']:
            data = payload.get('body', {}).get('data')
            if data:
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                body += decoded + "\n"

    return body


def get_header_value(headers, name):
    """
    Get value of a specific header from email headers list.

    Args:
        headers (list): List of header dictionaries
        name (str): Header name to search for

    Returns:
        str: Header value or empty string if not found
    """
    for header in headers:
        if header['name'].lower() == name.lower():
            return header['value']
    return ""


def sanitize_filename(text):
    """
    Sanitize text for use as filename.

    Args:
        text (str): Text to sanitize

    Returns:
        str: Sanitized filename
    """
    # Remove or replace invalid characters
    text = re.sub(r'[<>:"/\\|?*]', '_', text)
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # Limit length
    return text[:100]


def extract_sender_domain(from_header):
    """
    Extract domain from email From header.

    Args:
        from_header (str): Email From header value

    Returns:
        str: Domain name
    """
    # Extract email address from "Name <email@domain.com>" format
    match = re.search(r'[\w\.-]+@([\w\.-]+)', from_header)
    if match:
        return match.group(1)
    return "unknown"


class HTMLStripper(HTMLParser):
    """Simple HTML tag stripper."""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return ''.join(self.text)


def strip_html(html_content):
    """
    Strip HTML tags from content, leaving only text.

    Args:
        html_content (str): HTML content

    Returns:
        str: Plain text content
    """
    stripper = HTMLStripper()
    stripper.feed(html_content)
    return stripper.get_data()


def send_email(service, to_email, subject, body_html, body_text=""):
    """
    Send an HTML email using the Gmail API.

    Args:
        service: Gmail API service instance
        to_email (str): Recipient email address
        subject (str): Email subject
        body_html (str): Email body in HTML format
        body_text (str): Plain text version (optional)

    Returns:
        dict: Sent message details
    """
    message = MIMEMultipart('alternative')
    message['to'] = to_email
    message['from'] = 'me'
    message['subject'] = subject

    # Create plain text version if not provided
    if not body_text:
        body_text = "Please view this email in an HTML-compatible email client."

    # Attach parts in order: plain text first, then HTML
    # Email clients display the last alternative they can handle
    text_part = MIMEText(body_text, 'plain', 'utf-8')
    html_part = MIMEText(body_html, 'html', 'utf-8')

    message.attach(text_part)
    message.attach(html_part)

    # Encode the message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    # Send the message
    sent_message = service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()

    return sent_message


def generate_newsletter_summary(newsletters_data):
    """
    Generate a structured HTML summary of newsletters using Claude AI.

    Args:
        newsletters_data (list): List of dictionaries containing newsletter information

    Returns:
        str: HTML formatted summary
    """
    # Get API key from environment
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.Anthropic(api_key=api_key)

    # Prepare newsletter content for summarization
    newsletters_text = ""
    sources = set()

    for newsletter in newsletters_data:
        sources.add(newsletter['domain'])
        newsletters_text += f"\n\n--- Newsletter from {newsletter['domain']} ---\n"
        newsletters_text += f"Subject: {newsletter['subject']}\n"
        newsletters_text += f"Date: {newsletter['received_date']}\n\n"
        # Strip HTML tags and limit length
        plain_text = strip_html(newsletter['body'])
        newsletters_text += plain_text[:5000]

    # Create prompt for Claude
    prompt = f"""Please create a concise, 10-minute readable summary of these newsletters.

Structure your response as follows:

**US POLITICS**
Draw heavily from Puck News (pucknews.com) and Punchbowl News (punchbowlnews.com). Cover key political developments, insider perspectives, and legislative updates.

**UK NEWS**
Anchor this in The Times (thetimes.co.uk) coverage, but also draw on insights from other sources as relevant. Cover major UK political, economic, and social developments.

Format requirements:
- Use **bold** for section headers
- Use simple paragraphs with blank lines between topics
- Scannable and focused on the most important information
- Professional but engaging tone
- Approximately 10 minutes of reading time
- NO HTML tags, NO markdown formatting beyond **bold** for headers
- Just plain text with double line breaks between sections

Here are the newsletters:

{newsletters_text}

Provide ONLY the summary text - I will add HTML formatting separately."""

    # Call Claude API
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=3000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    summary_content = message.content[0].text

    # Convert **bold** to HTML strong tags and paragraphs
    # Split by double line breaks to get paragraphs
    paragraphs = summary_content.split('\n\n')
    formatted_content = ""

    for para in paragraphs:
        if para.strip():
            # Convert **text** to <strong>text</strong>
            para = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', para)
            # Convert single line breaks to <br>
            para = para.replace('\n', '<br>')
            formatted_content += f"<p>{para}</p>\n"

    # Build HTML email with inline styles for better email client compatibility
    sources_list = ", ".join(sorted(sources))
    today = datetime.now().strftime('%B %d, %Y')

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;font-family:Georgia,serif;line-height:1.6;color:#333;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f9f9f9;">
<tr>
<td align="center" style="padding:20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:white;border-radius:8px;max-width:600px;">
<tr>
<td style="padding:30px;">
<h1 style="color:#1a1a1a;border-bottom:3px solid #0066cc;padding-bottom:10px;margin:0 0 20px 0;font-size:28px;">Daily Newsletter Summary</h1>
<p style="color:#888;font-style:italic;margin:0 0 20px 0;">{today}</p>
<div style="background-color:#f0f0f0;padding:15px;border-radius:5px;margin:20px 0;font-size:0.9em;color:#666;">
<strong>Sources:</strong> {sources_list}
</div>
<div style="color:#333;line-height:1.6;">
{formatted_content}
</div>
<div style="margin-top:40px;padding-top:20px;border-top:1px solid #ddd;font-size:0.85em;color:#666;text-align:center;">
<p>Want to add or remove newsletter sources?<br>
<a href="https://github.com/UK7PriceIsRight/Daily-Mail" style="color:#0066cc;text-decoration:none;">Edit your sources on GitHub</a> or update the NEWSLETTER_SOURCES list in extract_newsletters.py</p>
</div>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>"""

    return html


def save_email_to_file(email_data, newsletters_dir):
    """
    Save email to a text file.

    Args:
        email_data (dict): Dictionary containing email data
        newsletters_dir (Path): Directory to save newsletters
    """
    domain = email_data['domain']
    date_str = email_data['date']
    subject = email_data['subject']
    body = email_data['body']

    # Create filename
    safe_subject = sanitize_filename(subject)
    filename = f"{date_str}_{domain}_{safe_subject}.txt"
    filepath = newsletters_dir / filename

    # Prepare content
    content = f"From: {email_data['from']}\n"
    content += f"Date: {email_data['received_date']}\n"
    content += f"Subject: {subject}\n"
    content += f"\n{'='*80}\n\n"
    content += body

    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Saved: {filename}")


def main():
    """
    Main function to extract newsletters from Gmail and send them via email.
    """
    try:
        # Create newsletters directory
        newsletters_dir = Path('newsletters')
        newsletters_dir.mkdir(exist_ok=True)

        print("Authenticating with Gmail API...")
        service = get_gmail_service()

        print("Building search query...")
        query = build_search_query()
        print(f"Query: {query}")

        print("\nSearching for emails...")
        results = service.users().messages().list(
            userId='me',
            q=query
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print("No newsletters found from the last 24 hours.")
            return

        print(f"Found {len(messages)} email(s)\n")

        # List to collect all newsletter data for summarization
        newsletters_data = []

        # Process each message
        for idx, message in enumerate(messages, 1):
            msg_id = message['id']
            print(f"[{idx}/{len(messages)}] Processing message ID: {msg_id}")

            # Get full message details
            msg = service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            # Extract headers
            headers = msg['payload']['headers']
            from_header = get_header_value(headers, 'From')
            subject = get_header_value(headers, 'Subject')
            date_header = get_header_value(headers, 'Date')

            # Extract domain
            domain = extract_sender_domain(from_header)

            # Extract body
            body = extract_email_body(msg['payload'])

            # Get internal date and format it
            internal_date = int(msg['internalDate']) / 1000
            received_datetime = datetime.fromtimestamp(internal_date)
            date_str = received_datetime.strftime('%Y%m%d_%H%M%S')

            # Prepare email data
            email_data = {
                'from': from_header,
                'subject': subject,
                'received_date': date_header,
                'date': date_str,
                'domain': domain,
                'body': body
            }

            # Save to file (for backup)
            save_email_to_file(email_data, newsletters_dir)

            # Add to collection for summarization
            newsletters_data.append(email_data)

        print(f"\n✓ Successfully extracted {len(messages)} newsletter(s) to '{newsletters_dir}' directory")

        # Generate and send summarized email
        if newsletters_data:
            print("\nGenerating newsletter summary with AI...")
            try:
                html_summary = generate_newsletter_summary(newsletters_data)

                print("Sending summary email...")
                today = datetime.now().strftime('%Y-%m-%d')
                email_subject = f"Daily Newsletters - {today}"

                send_email(
                    service=service,
                    to_email='uk7priceisright@gmail.com',
                    subject=email_subject,
                    body_html=html_summary
                )
                print(f"✓ Successfully sent email to uk7priceisright@gmail.com")
            except ValueError as ve:
                print(f"Configuration error: {ve}")
                print("Please set ANTHROPIC_API_KEY environment variable")
            except HttpError as email_error:
                print(f"Failed to send email: {email_error}")
            except Exception as e:
                print(f"Error generating or sending summary: {e}")

    except HttpError as error:
        print(f"An error occurred: {error}")
    except FileNotFoundError as error:
        print(f"Error: {error}")
    except Exception as error:
        print(f"An unexpected error occurred: {error}")


if __name__ == '__main__':
    main()
