# utils module for accounts app
from django.core.cache import cache
import pyotp


class generateKey:
    """Generates OTP"""

    @staticmethod
    def returnValue():
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret, interval=86400)
        OTP = totp.now()
        return {"totp": secret, "OTP": OTP}

