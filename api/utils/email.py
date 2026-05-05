# utils/email.py
"""
Email utility for sending the account verification link.
Configure EMAIL_* settings in settings.py (or .env) for your SMTP provider.
"""

from django.conf import settings
from django.core.mail import send_mail


def send_verification_email(user, token: str) -> None:
    """
    Send an email-verification link to the newly registered user.
    The frontend should handle the /verify-email?token=<token> route
    and POST it to /api/auth/verify-email/.
    """
    verification_url = (
        f"{settings.FRONTEND_URL}/verify-email?token={token}"
    )

    subject = "Verify your Library account"

    message = (
        f"Hi {user.username},\n\n"
        f"Thank you for registering. Please verify your email address by "
        f"clicking the link below (valid for 24 hours):\n\n"
        f"{verification_url}\n\n"
        f"If you did not register, you can ignore this email.\n\n"
        f"– Library Team"
    )

    html_message = f"""
    <p>Hi <strong>{user.username}</strong>,</p>
    <p>Thank you for registering. Please verify your email address by clicking the button below (valid for 24 hours):</p>
    <p>
        <a href="{verification_url}"
           style="background:#4f46e5;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">
            Verify Email
        </a>
    </p>
    <p>If you did not register, you can safely ignore this email.</p>
    <p>– Library Team</p>
    """

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )