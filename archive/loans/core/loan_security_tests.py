"""
Unit tests for core.loan_security (LoanDocumentCipher).

This mirrors core/security_tests.py: LoanDocumentCipher had the same
SECRET_KEY-fallback issue as SensitiveValueCipher and previously had no test
coverage at all.
"""
from django.test import TestCase, override_settings
from core.loan_security import LoanDocumentCipher


class LoanDocumentCipherTests(TestCase):
    PLAINTEXT = "loan-agreement-reference-98765"

    def test_encrypt_returns_fernet_token_happy_path(self):
        token = LoanDocumentCipher.encrypt(self.PLAINTEXT)
        self.assertTrue(token.startswith("gAAAA"), f"Unexpected token prefix: {token[:10]}")

    def test_encrypt_is_idempotent_boundary(self):
        token = LoanDocumentCipher.encrypt(self.PLAINTEXT)
        token2 = LoanDocumentCipher.encrypt(token)
        self.assertEqual(token, token2)

    def test_encrypt_empty_string_returns_empty_string(self):
        self.assertEqual(LoanDocumentCipher.encrypt(""), "")

    def test_round_trip_decrypt_happy_path(self):
        token = LoanDocumentCipher.encrypt(self.PLAINTEXT)
        self.assertEqual(LoanDocumentCipher.decrypt(token), self.PLAINTEXT)

    def test_decrypt_empty_returns_empty_boundary(self):
        self.assertEqual(LoanDocumentCipher.decrypt(""), "")

    def test_decrypt_tampered_token_raises_error(self):
        token = LoanDocumentCipher.encrypt(self.PLAINTEXT)
        corrupted = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(Exception):
            LoanDocumentCipher.decrypt(corrupted)

    @override_settings(FIELD_ENCRYPTION_KEY="a-real-dedicated-encryption-key", SECRET_KEY="unrelated-django-secret-key")
    def test_uses_field_encryption_key_independently_of_secret_key(self):
        token = LoanDocumentCipher.encrypt("loan-doc")
        self.assertEqual(LoanDocumentCipher.decrypt(token), "loan-doc")

    @override_settings(FIELD_ENCRYPTION_KEY="", SECRET_KEY="a-non-empty-secret-key-that-must-not-be-used")
    def test_does_not_fall_back_to_secret_key_error(self):
        with self.assertRaises(RuntimeError):
            LoanDocumentCipher._get_key()

    @override_settings(FIELD_ENCRYPTION_KEY=None, SECRET_KEY=None)
    def test_raises_runtime_error_when_both_keys_absent_error(self):
        with self.assertRaises(RuntimeError):
            LoanDocumentCipher._get_key()
