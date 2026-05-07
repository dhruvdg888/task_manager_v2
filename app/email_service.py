# SMTP : Simple Mail Transfer Protocol

from .config import settings

import smtplib
from email.mime.text import MIMEText

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.email
    msg["To"] = to_email

    with smtplib.SMTP(settings.smtp_server,settings.smtp_port) as server:
        server.starttls()
        server.login(settings.email,settings.email_password)
        server.send_message(msg)

