from django.core.mail import send_mail
from django.conf import settings
from .models import User
import sendgrid
from sendgrid.helpers.mail import *
from .utils import generateKey


def send_otp_via_email(to_email):
    """send otp via email"""
    gen_key = generateKey()
    otp = gen_key.returnValue()["OTP"]
    user_obj = User.objects.get(email=to_email)
    user_obj.otp = otp
    user_obj.save()
    sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
    from_email = Email(settings.EMAIL_HOST_USER)
    subject = f"Your account verification OTP"
    content = Content("text/plain", f"Your OTP is {otp}")
    mail = Mail(from_email, to_email, subject, content)
    sg.client.mail.send.post(request_body=mail.get())


def send_verification_email(to_email):
    """send account verification acknowledgement"""
    sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
    from_email = Email(settings.EMAIL_HOST_USER)
    subject = f"Your account verification success"
    content = Content("text/plain", f"Your account is successfully verified")
    mail = Mail(from_email, to_email, subject, content)
    sg.client.mail.send.post(request_body=mail.get())


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
