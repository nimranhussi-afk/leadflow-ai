import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import settings

def send_email_notification(lead_name: str, lead_email: str, summary: str, draft_response: str):
    """
    Sends an email notification to the business owner via SMTP using SSL.
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_ADDRESS
        msg["To"] = settings.EMAIL_ADDRESS  # Sends notification to your own business email inbox
        msg["Subject"] = f"🚀 New Lead Received: {lead_name}"

        body = f"""
You have received a new lead!

- Name: {lead_name}
- Email: {lead_email}

AI Summary:
{summary}

Suggested Draft Response:
{draft_response}
        """

        msg.attach(MIMEText(body, "plain"))

        # Connect to Gmail SMTP server using SSL on port 465
        with smtplib.SMTP_SSL(settings.EMAIL_SMTP_SERVER, 465) as server:
            server.login(settings.EMAIL_ADDRESS, settings.EMAIL_APP_PASSWORD)
            server.send_message(msg)
            
        return {"status": "success", "message": "Email notification sent successfully."}

    except Exception as e:
        print(f"SMTP Error: {str(e)}")
        raise Exception(f"Failed to send email notification: {str(e)}")