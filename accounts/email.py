from django.core.cache import cache
import datetime
from django.core.mail import send_mail
from django.conf import settings
from .models import User
import sendgrid
from sendgrid.helpers.mail import *
from .utils import generateKey, OTPManager
from django.conf import settings

SG = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
FROM_EMAIL = Email(settings.EMAIL_HOST_USER)

def send_otp_via_email(to_email):
    """send otp via email using django cache"""
    try:
        gen_key = generateKey()
        otp = gen_key.returnValue()["OTP"]
        user_email = User.objects.filter(email=to_email)[0].email

        # store user otp
        otp_manager = OTPManager()
        otp_manager.create_user_otp(user_email, otp, settings.OTP_DURATION)
        print(cache.get(user_email))

        subject = f"Your account verification OTP"
        content = Content("text/plain", f"Your OTP is {otp}")
        mail = Mail(FROM_EMAIL, to_email, subject, content)
        SG.client.mail.send.post(request_body=mail.get())

    except Exception as e:
        print(e)


def send_verification_email(to_email):
    """send account verification acknowledgement"""
    try:
        subject = f"Your account verification success"
        content = Content("text/plain", f"Your account is successfully verified")
        mail = Mail(FROM_EMAIL, to_email, subject, content)
        SG.client.mail.send.post(request_body=mail.get())

    except Exception as e:
        print(e)


def send_recovery_otp(email):
    """send account recovery OTP"""
    subject = f"Your account recovery OTP"
    gen_key = generateKey()
    otp = gen_key.returnValue()["OTP"]
    message = f"Your account recovery OTP is {otp}"
    email_from = settings.EMAIL_HOST
    send_mail(subject, message, email_from, [email])
    user_obj = User.objects.get(email=email)
    user_obj.otp = otp
    user_obj.save()


def send_account_recovery_email(email):
    """send account verification acknowledgement"""
    subject = f"Your account password reset success"
    message = f"Your account password is reset successfully"
    email_from = settings.EMAIL_HOST
    send_mail(subject, message, email_from, [email])
