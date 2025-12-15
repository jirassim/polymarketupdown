"""
Test Email Notification
Quick test to verify Gmail App Password is working
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_FROM = os.getenv('EMAIL_FROM', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_TO = os.getenv('EMAIL_TO', '')

print("📧 Testing Email Configuration...")
print(f"SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
print(f"From: {EMAIL_FROM}")
print(f"To: {EMAIL_TO}")
print(f"Password: {'*' * len(EMAIL_PASSWORD) if EMAIL_PASSWORD else 'NOT SET'}")
print()

if not all([EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO]):
    print("❌ Error: Email configuration incomplete!")
    print(f"EMAIL_FROM: {'✓' if EMAIL_FROM else '✗'}")
    print(f"EMAIL_PASSWORD: {'✓' if EMAIL_PASSWORD else '✗'}")
    print(f"EMAIL_TO: {'✓' if EMAIL_TO else '✗'}")
    exit(1)

try:
    # Create test message
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = "🧪 Test Email - Polymarket Bot"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #4CAF50;">✅ Email Test Successful!</h2>

        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p>This is a test email from the Polymarket UP/DOWN Registration Bot.</p>
            <p>If you're receiving this, your Gmail App Password is configured correctly!</p>
        </div>

        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #0c5460;">Configuration Details:</h3>
            <p><strong>SMTP Server:</strong> smtp.gmail.com:587</p>
            <p><strong>From:</strong> {EMAIL_FROM}</p>
            <p><strong>Status:</strong> ✅ Working</p>
        </div>

        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            Test performed at: {datetime.datetime.now()}
        </p>
    </body>
    </html>
    """

    msg.attach(MIMEText(body, 'html'))

    print("📤 Connecting to Gmail SMTP server...")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        print("🔐 Starting TLS encryption...")
        server.starttls()

        print("🔑 Logging in...")
        server.login(EMAIL_FROM, EMAIL_PASSWORD)

        print("📨 Sending email...")
        server.send_message(msg)

    print()
    print("✅ SUCCESS! Email sent successfully!")
    print(f"📬 Check your inbox at: {EMAIL_TO}")
    print()

except smtplib.SMTPAuthenticationError as e:
    print()
    print("❌ AUTHENTICATION ERROR!")
    print("The Gmail App Password is incorrect or invalid.")
    print()
    print("Please check:")
    print("1. App Password is correct (16 characters, no spaces)")
    print("2. 2-Step Verification is enabled on Gmail")
    print("3. App Password was created for 'Mail' application")
    print()
    print(f"Error details: {e}")

except Exception as e:
    print()
    print(f"❌ ERROR: {type(e).__name__}")
    print(f"Details: {e}")
    print()
