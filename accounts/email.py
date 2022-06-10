from django.core.cache import cache
import datetime
from django.core.mail import send_mail
from django.conf import settings
from .models import User
import sendgrid
from sendgrid.helpers.mail import *
from .utils import generateKey
from django.conf import settings


def send_otp_via_email(to_email):
    """send otp via email using django cache

        # Example: creating cache
        cache.set_many({'a': 1, 'b': 2, 'c': 3})
        cache.get_many(['a', 'b', 'c'])

        # Check for expiry of cache
        sentinel = object()
        cache.get('my_key', sentinel) is sentinel
        False

        # Wait 30 seconds for 'my_key' to expire...
        cache.get('my_key', sentinel) is sentinel
        True

        # Delete cache
        cache.delete_many(['a', 'b', 'c'])
    """
    try:
        gen_key = generateKey()
        otp = gen_key.returnValue()["OTP"]
        cache.set_many({'user_otp': otp, 'creation_time': datetime.datetime.now(), 'otp_count': settings.OTP_MIN}, settings.OTP_DURATION)
        sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
        from_email = Email(settings.EMAIL_HOST_USER)
        subject = f"Your account verification OTP"
        content = Content("text/plain", f"Your OTP is {otp}")
        mail = Mail(from_email, to_email, subject, content)
        sg.client.mail.send.post(request_body=mail.get())

    except Exception as e:
        print(e)


def send_verification_email(to_email):
    """send account verification acknowledgement"""
    try:
        sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)
        from_email = Email(settings.EMAIL_HOST_USER)
        subject = f"Your account verification success"
        content = Content("text/plain", f"Your account is successfully verified")
        mail = Mail(from_email, to_email, subject, content)
        sg.client.mail.send.post(request_body=mail.get())

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
