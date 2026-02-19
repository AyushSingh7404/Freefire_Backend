"""
Email service using fastapi-mail with Gmail SMTP.

Gmail setup steps (do this once):
  1. Enable 2-Factor Authentication on your Gmail account
  2. Go to: Google Account → Security → App Passwords
  3. Create an app password for "Mail"
  4. Use that 16-character password as MAIL_PASSWORD in your .env
     (NOT your real Gmail password)

fastapi-mail 1.6.1 changes vs older versions:
  - ConnectionConfig uses MAIL_STARTTLS=True, MAIL_SSL_TLS=False for port 587
  - MAIL_SSL_TLS=True, MAIL_STARTTLS=False for port 465
"""
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.config import settings

# Build connection config once at module level — don't rebuild on every request
mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=True,    # required for port 587 (STARTTLS)
    MAIL_SSL_TLS=False,    # don't use SSL on port 587
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

fast_mail = FastMail(mail_config)


async def send_otp_email(email_to: str, otp: str, purpose: str) -> None:
    """
    Send an OTP email. Called via FastAPI BackgroundTasks so the HTTP response
    is returned to the user immediately — they don't wait for SMTP to complete.

    Args:
        email_to: recipient email address
        otp: the raw 6-digit OTP string (never stored raw in DB)
        purpose: "register" | "login" | "forgot_password"
    """
    subject_map = {
        "register": "Verify your FireEsports account",
        "login": "Your FireEsports login OTP",
        "forgot_password": "Reset your FireEsports password",
    }
    body_map = {
        "register": (
            f"Welcome to FireEsports!\n\n"
            f"Your verification OTP is: {otp}\n\n"
            f"This OTP is valid for 10 minutes.\n"
            f"Do not share this with anyone.\n\n"
            f"If you did not create an account, please ignore this email."
        ),
        "login": (
            f"Your FireEsports login OTP is: {otp}\n\n"
            f"Valid for 10 minutes. Do not share this with anyone.\n\n"
            f"If you did not request this, your password may be compromised."
        ),
        "forgot_password": (
            f"Your FireEsports password reset OTP is: {otp}\n\n"
            f"Valid for 10 minutes.\n"
            f"If you did not request a password reset, please ignore this email."
        ),
    }

    message = MessageSchema(
        subject=subject_map.get(purpose, "Your FireEsports OTP"),
        recipients=[email_to],
        body=body_map.get(
            purpose,
            f"Your OTP is: {otp}\n\nValid for 10 minutes.",
        ),
        subtype=MessageType.plain,
    )

    await fast_mail.send_message(message)
