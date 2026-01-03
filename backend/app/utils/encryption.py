"""
Encryption Utility for Sensitive Data

Provides Fernet-based symmetric encryption for storing sensitive credentials
like SmartAPI PIN and TOTP secrets.
"""
import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Fernet-based encryption service for sensitive data.

    Uses JWT_SECRET as the base key, deriving a Fernet-compatible key from it.
    """

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize encryption service.

        Args:
            secret_key: Base secret key (defaults to JWT_SECRET)
        """
        self._secret = secret_key or settings.JWT_SECRET
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """
        Create Fernet instance from secret key.

        Fernet requires a 32-byte URL-safe base64-encoded key.
        We derive this from JWT_SECRET using SHA256.
        """
        # Hash the secret to get exactly 32 bytes
        key_bytes = hashlib.sha256(self._secret.encode()).digest()
        # Encode to URL-safe base64 for Fernet
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Encryption failed: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails (invalid token or corrupted data)
        """
        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            logger.error("Decryption failed: Invalid token")
            raise ValueError("Decryption failed: Invalid or corrupted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Decryption failed: {e}")


# Global singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt(plaintext: str) -> str:
    """
    Convenience function to encrypt a string.

    Args:
        plaintext: String to encrypt

    Returns:
        Encrypted string
    """
    return get_encryption_service().encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    """
    Convenience function to decrypt a string.

    Args:
        ciphertext: Encrypted string

    Returns:
        Decrypted plaintext
    """
    return get_encryption_service().decrypt(ciphertext)
