"""
Unit tests for core.security (SensitiveValueCipher).

Coverage targets
────────────────
- encrypt_if_needed / encrypt:  happy path, idempotent re-encrypt, empty value
- decrypt:                      happy path, empty value, tampered ciphertext (error)
- _get_key:                     requires its own FIELD_ENCRYPTION_KEY, never falls
                                 back to SECRET_KEY
"""
from django.test import TestCase, override_settings
from core.security import SensitiveValueCipher


class SensitiveValueCipherTests(TestCase):
    PLAINTEXT = "0123456789"

    # ── encrypt_if_needed / encrypt ─────────────────────────────────────────

    def test_encrypt_returns_fernet_token_happy_path(self):
        token = SensitiveValueCipher.encrypt(self.PLAINTEXT)
        # Fernet tokens always start with gAAAA after URL-safe base64 encoding
        self.assertTrue(token.startswith("gAAAA"), f"Unexpected token prefix: {token[:10]}")

    def test_encrypt_is_idempotent_boundary(self):
        """Encrypting an already-encrypted value must not double-encrypt it."""
        token = SensitiveValueCipher.encrypt(self.PLAINTEXT)
        token2 = SensitiveValueCipher.encrypt_if_needed(token)
        self.assertEqual(token, token2)

    def test_encrypt_empty_string_returns_empty_string(self):
        self.assertEqual(SensitiveValueCipher.encrypt(""), "")

    def test_encrypt_if_needed_returns_empty_for_none_equivalent(self):
        self.assertEqual(SensitiveValueCipher.encrypt_if_needed(""), "")

    # ── decrypt ─────────────────────────────────────────────────────────────

    def test_round_trip_decrypt_happy_path(self):
        token = SensitiveValueCipher.encrypt(self.PLAINTEXT)
        decrypted = SensitiveValueCipher.decrypt(token)
        self.assertEqual(decrypted, self.PLAINTEXT)

    def test_decrypt_empty_returns_empty_boundary(self):
        self.assertEqual(SensitiveValueCipher.decrypt(""), "")

    def test_decrypt_tampered_token_raises_error(self):
        token = SensitiveValueCipher.encrypt(self.PLAINTEXT)
        # Flip one character to corrupt the MAC
        corrupted = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(Exception):
            SensitiveValueCipher.decrypt(corrupted)

    # ── key derivation ───────────────────────────────────────────────────────

    @override_settings(FIELD_ENCRYPTION_KEY="a-real-dedicated-encryption-key", SECRET_KEY="unrelated-django-secret-key")
    def test_uses_field_encryption_key_independently_of_secret_key(self):
        """A configured FIELD_ENCRYPTION_KEY is used regardless of SECRET_KEY."""
        token = SensitiveValueCipher.encrypt("bank-account")
        decrypted = SensitiveValueCipher.decrypt(token)
        self.assertEqual(decrypted, "bank-account")

    @override_settings(FIELD_ENCRYPTION_KEY="", SECRET_KEY="a-non-empty-secret-key-that-must-not-be-used")
    def test_does_not_fall_back_to_secret_key_error(self):
        """FIELD_ENCRYPTION_KEY is mandatory: a present SECRET_KEY must never be used
        as a silent substitute, since the two secrets serve different purposes and
        rotating one must not silently affect the other."""
        with self.assertRaises(RuntimeError):
            SensitiveValueCipher._get_key()

    @override_settings(FIELD_ENCRYPTION_KEY=None, SECRET_KEY=None)
    def test_raises_runtime_error_when_both_keys_absent_error(self):
        with self.assertRaises(RuntimeError):
            SensitiveValueCipher._get_key()
