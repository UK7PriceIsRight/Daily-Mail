#!/usr/bin/env python3
"""
Gmail Newsletter Extractor and Sender

This script connects to Gmail via the Gmail API and extracts newsletters
from specific sources (pucknews.com, economist.com, punchbowlnews.com, thetimes.co.uk)
from the last 24 hours. It saves them to separate text files and sends a
consolidated email with all newsletter content to the specified recipient.
"""

import os
import base64
import re
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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


def send_email(service, to_email, subject, body):
    """
    Send an email using the Gmail API.

    Args:
        service: Gmail API service instance
        to_email (str): Recipient email address
        subject (str): Email subject
        body (str): Email body text

    Returns:
        dict: Sent message details
    """
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject

    # Encode the message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    # Send the message
    sent_message = service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()

    return sent_message


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

        # List to collect all newsletter content for the email
        all_newsletters = []

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

            # Add to collection for emailing
            newsletter_content = f"From: {from_header}\n"
            newsletter_content += f"Date: {date_header}\n"
            newsletter_content += f"Subject: {subject}\n"
            newsletter_content += f"\n{'='*80}\n\n"
            newsletter_content += body
            newsletter_content += f"\n\n{'='*80}\n\n"

            all_newsletters.append(newsletter_content)

        print(f"\n✓ Successfully extracted {len(messages)} newsletter(s) to '{newsletters_dir}' directory")

        # Send consolidated email with all newsletters
        if all_newsletters:
            print("\nSending newsletters via email...")
            today = datetime.now().strftime('%Y-%m-%d')
            email_subject = f"Daily Newsletters - {today}"
            email_body = "\n".join(all_newsletters)

            try:
                send_email(
                    service=service,
                    to_email='mattjochim@gmail.com',
                    subject=email_subject,
                    body=email_body
                )
                print(f"✓ Successfully sent email to mattjochim@gmail.com")
            except HttpError as email_error:
                print(f"Failed to send email: {email_error}")

    except HttpError as error:
        print(f"An error occurred: {error}")
    except FileNotFoundError as error:
        print(f"Error: {error}")
    except Exception as error:
        print(f"An unexpected error occurred: {error}")


if __name__ == '__main__':
    main()
