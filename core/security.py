import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings


class SensitiveValueCipher:
    @staticmethod
    def _get_key() -> bytes:
        # Deliberately does NOT fall back to SECRET_KEY. SECRET_KEY is used for
        # session/CSRF/password-reset-token signing and may be rotated independently
        # for those reasons; silently reusing it here would mean rotating it also
        # breaks decryption of every stored bank/pension/tax value, and a leak of
        # SECRET_KEY (e.g. a permissive dev default) would directly compromise
        # payroll data too. FIELD_ENCRYPTION_KEY must be its own dedicated secret.
        secret = getattr(settings, 'FIELD_ENCRYPTION_KEY', '')
        if not secret:
            raise RuntimeError(
                'FIELD_ENCRYPTION_KEY must be configured (as its own dedicated secret, '
                'separate from SECRET_KEY) before encrypting or decrypting payroll fields.'
            )
        digest = hashlib.sha256(secret.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest)

    @classmethod
    def _is_encrypted(cls, value: str) -> bool:
        return bool(value) and value.startswith('gAAAA')

    @classmethod
    def encrypt_if_needed(cls, value: str) -> str:
        if not value:
            return ''
        if cls._is_encrypted(value):
            return value
        token = Fernet(cls._get_key()).encrypt(value.encode('utf-8'))
        return token.decode('utf-8')

    @classmethod
    def encrypt(cls, value: str) -> str:
        return cls.encrypt_if_needed(value)

    @classmethod
    def decrypt(cls, value: str) -> str:
        if not value:
            return ''
        return Fernet(cls._get_key()).decrypt(value.encode('utf-8')).decode('utf-8')
