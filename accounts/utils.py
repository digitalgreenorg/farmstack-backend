# utils module for accounts app
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle, UserRateThrottle
import pyotp
import random


class generateKey:
    """Generates OTP"""

    @staticmethod
    def returnValue():
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, interval=86400)
        OTP = totp.now()
        return {"totp": secret, "OTP": OTP}


class UserOTPThrottle(BaseThrottle):
    """Throttling or rate limiting requests for user OTP"""

    def allow_request(self, request, view):
        """Return `True` if the request should be allowed, `False` otherwise. """
        return random.randint(1, 10) != 1

    def wait(self):
        """
        Optionally, return a recommended number of seconds to wait before
        the next request.
        """
        cu_second = 600
        return cu_second

class UserSecThrottle(UserOTPThrottle, UserRateThrottle):   # or AnonRateThrottle
    scope = 'user_sec'

