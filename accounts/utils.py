# utils module for accounts app
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle, UserRateThrottle
import pyotp, random, datetime


class generateKey:
    """Generates OTP"""

    @staticmethod
    def returnValue():
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, interval=86400)
        OTP = totp.now()
        return {"totp": secret, "OTP": OTP}


class OTPManager:
    """Manages user OTPs in django cache

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

    def create_user_otp(
        self,
        email,
        otp,
        otp_duration,
        otp_count=1,
        updation_time=datetime.datetime.now(),
    ):
        """Creates a user OTP for login or account verification"""
        return cache.set(
            email,
            {
                "email": email,
                "user_otp": otp,
                "otp_count": otp_count,
                "updation_time": updation_time,
            },
            otp_duration,
        )
