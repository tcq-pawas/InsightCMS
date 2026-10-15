import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.utils import timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_google_oauth_credentials(company):
    """
    Builds and refreshes Google OAuth2 Credentials for a company if available.
    Returns Credentials object or None.
    """
    if not company or not company.google_refresh_token:
        return None

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
    token_uri = "https://oauth2.googleapis.com/token"

    creds = Credentials(
        token=company.google_access_token or None,
        refresh_token=company.google_refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=getattr(settings, 'GOOGLE_OAUTH_SCOPES', ['https://www.googleapis.com/auth/gmail.send'])
    )

    # Check if access token is expired or missing; refresh it if needed
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                company.google_access_token = creds.token
                if creds.expiry:
                    company.google_token_expiry = creds.expiry
                company.save(update_fields=['google_access_token', 'google_token_expiry'])
            except Exception as e:
                logger.error(f"Error refreshing Google OAuth token for {company}: {e}")
                return None
    return creds


def send_via_gmail_api(company, recipient_list, subject, html_message, text_message=""):
    """
    Sends email using Google Gmail API with OAuth 2.0 credentials.
    """
    creds = get_google_oauth_credentials(company)
    if not creds:
        raise ValueError("Google OAuth credentials not configured or expired for this company.")

    sender_email = company.google_email
    sender_name = company.smtp_from_name or company.company_name or ""
    sender_header = f"{sender_name} <{sender_email}>" if sender_name else sender_email

    service = build('gmail', 'v1', credentials=creds)

    for recipient in recipient_list:
        message = MIMEMultipart('alternative')
        message['to'] = recipient
        message['from'] = sender_header
        message['subject'] = subject

        if text_message:
            part1 = MIMEText(text_message, 'plain')
            message.attach(part1)
        if html_message:
            part2 = MIMEText(html_message, 'html')
            message.attach(part2)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        body = {'raw': raw_message}

        service.users().messages().send(userId='me', body=body).execute()

    return True


def send_company_email(company, recipient_list, subject, html_message, text_message=""):
    """
    Unified email sender:
    1. Checks if company.email_provider == 'google' and has valid google credentials.
       If so, sends via Gmail API (One-Click OAuth).
    2. Else, sends via company's configured Manual SMTP.
    3. Falls back to Django default EMAIL_HOST settings.
    """
    if isinstance(recipient_list, str):
        recipient_list = [recipient_list]

    # Mode 1: Google OAuth (One-Click)
    if company and company.email_provider == 'google' and company.google_refresh_token:
        try:
            return send_via_gmail_api(company, recipient_list, subject, html_message, text_message)
        except Exception as e:
            logger.warning(f"Failed sending via Gmail API, attempting fallback: {e}")

    # Mode 2: Manual SMTP with company custom credentials
    if company and company.smtp_user and company.smtp_password:
        sender_name = company.smtp_from_name or company.company_name or ""
        from_email = f"{sender_name} <{company.smtp_user}>" if sender_name else company.smtp_user

        custom_connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=company.smtp_host or 'smtp.gmail.com',
            port=company.smtp_port or 587,
            username=company.smtp_user,
            password=company.smtp_password,
            use_tls=company.smtp_use_tls,
            fail_silently=False
        )

        email = EmailMessage(
            subject=subject,
            body=html_message or text_message,
            from_email=from_email,
            to=recipient_list,
            connection=custom_connection
        )
        if html_message:
            email.content_subtype = "html"
        email.send(fail_silently=False)
        return True

    # Mode 3: Fallback to Django default connection
    email = EmailMessage(
        subject=subject,
        body=html_message or text_message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=recipient_list,
    )
    if html_message:
        email.content_subtype = "html"
    email.send(fail_silently=False)
    return True
