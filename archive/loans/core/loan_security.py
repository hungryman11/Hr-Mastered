from django.conf import settings
from cryptography.fernet import Fernet
import base64
import hashlib


class LoanDocumentCipher:
    @staticmethod
    def _get_key() -> bytes:
        # Same reasoning as core.security.SensitiveValueCipher: no SECRET_KEY fallback.
        # Loan documents are as sensitive as payroll bank details and deserve the same
        # dedicated, independently-rotatable encryption key.
        secret = getattr(settings, 'FIELD_ENCRYPTION_KEY', '')
        if not secret:
            raise RuntimeError(
                'FIELD_ENCRYPTION_KEY must be configured (as its own dedicated secret, '
                'separate from SECRET_KEY) before encrypting or decrypting loan documents.'
            )
        return base64.urlsafe_b64encode(hashlib.sha256(secret.encode('utf-8')).digest())

    @classmethod
    def _is_encrypted(cls, value: str) -> bool:
        return bool(value) and value.startswith('gAAAA')

    @classmethod
    def encrypt(cls, value: str) -> str:
        if not value:
            return ''
        if cls._is_encrypted(value):
            return value
        return Fernet(cls._get_key()).encrypt(value.encode('utf-8')).decode('utf-8')

    @classmethod
    def decrypt(cls, value: str) -> str:
        return Fernet(cls._get_key()).decrypt(value.encode('utf-8')).decode('utf-8') if value else ''
