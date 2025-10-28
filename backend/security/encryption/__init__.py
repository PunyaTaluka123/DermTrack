"""
Encryption utilities for medical data protection.
Implements AES-256-GCM encryption with proper key management.
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os
import base64
import hashlib
from pathlib import Path
from typing import Tuple, Optional
import secrets


class EncryptionManager:
    """
    Handles AES-256-GCM encryption/decryption for medical data.

    Security features:
    - AES-256-GCM authenticated encryption
    - Separate keys per clinic
    - Monthly key rotation support
    - Never hardcodes keys
    - Generates SHA-256 checksums for integrity
    """

    def __init__(self, clinic_id: str = "default"):
        self.clinic_id = clinic_id
        self.key_version = self._get_current_key_version()

    def _get_current_key_version(self) -> str:
        """Get current key version for rotation tracking"""
        from datetime import datetime
        # Format: YYYY-MM (monthly rotation)
        return datetime.utcnow().strftime("%Y-%m")

    def _get_encryption_key(self) -> bytes:
        """
        Retrieve encryption key from environment or key store.
        NEVER hardcodes keys - always loads from secure storage.

        Key hierarchy:
        1. Check environment variable: ENCRYPTION_KEY_{CLINIC_ID}_{VERSION}
        2. Fall back to: ENCRYPTION_KEY_{CLINIC_ID}
        3. Fall back to: ENCRYPTION_KEY (shared key - not recommended for production)

        Returns 32-byte (256-bit) key for AES-256.
        """
        # Try versioned key first (for rotation)
        key_name = f"ENCRYPTION_KEY_{self.clinic_id.upper()}_{self.key_version.replace('-', '_')}"
        key_b64 = os.getenv(key_name)

        if not key_b64:
            # Fall back to clinic-specific key
            key_name = f"ENCRYPTION_KEY_{self.clinic_id.upper()}"
            key_b64 = os.getenv(key_name)

        if not key_b64:
            # Fall back to shared key (not recommended)
            key_b64 = os.getenv("ENCRYPTION_KEY")

        if not key_b64:
            raise ValueError(
                f"No encryption key found. Please set {key_name} environment variable. "
                "Generate one with: python -c 'import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())'"
            )

        try:
            key = base64.b64decode(key_b64)
            if len(key) != 32:
                raise ValueError(f"Encryption key must be 32 bytes (256 bits), got {len(key)} bytes")
            return key
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")

    def encrypt_data(self, plaintext: bytes) -> Tuple[bytes, str]:
        """
        Encrypt data using AES-256-GCM.

        Args:
            plaintext: Data to encrypt

        Returns:
            Tuple of (ciphertext, nonce_b64)
            - ciphertext: Encrypted data (includes authentication tag)
            - nonce_b64: Base64-encoded nonce (needed for decryption)
        """
        key = self._get_encryption_key()
        aesgcm = AESGCM(key)

        # Generate random 96-bit nonce (recommended for GCM)
        nonce = secrets.token_bytes(12)

        # Encrypt and authenticate
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

        return ciphertext, base64.b64encode(nonce).decode('utf-8')

    def decrypt_data(self, ciphertext: bytes, nonce_b64: str) -> bytes:
        """
        Decrypt data using AES-256-GCM.

        Args:
            ciphertext: Encrypted data
            nonce_b64: Base64-encoded nonce from encryption

        Returns:
            Decrypted plaintext

        Raises:
            cryptography.exceptions.InvalidTag: If authentication fails (tampering detected)
        """
        key = self._get_encryption_key()
        aesgcm = AESGCM(key)

        nonce = base64.b64decode(nonce_b64)
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)

        return plaintext

    def encrypt_file(self, input_path: Path, output_path: Path) -> dict:
        """
        Encrypt a file and generate integrity checksum.

        Args:
            input_path: Path to plaintext file
            output_path: Path to save encrypted file

        Returns:
            Metadata dict with nonce, checksums, and key version
        """
        # Read plaintext
        with open(input_path, 'rb') as f:
            plaintext = f.read()

        # Calculate checksum before encryption
        checksum_before = hashlib.sha256(plaintext).hexdigest()

        # Encrypt
        ciphertext, nonce_b64 = self.encrypt_data(plaintext)

        # Write encrypted data
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(ciphertext)

        # Calculate checksum after encryption
        checksum_after = hashlib.sha256(ciphertext).hexdigest()

        return {
            "nonce": nonce_b64,
            "checksum_plaintext": checksum_before,
            "checksum_ciphertext": checksum_after,
            "key_version": self.key_version,
            "clinic_id": self.clinic_id,
            "algorithm": "AES-256-GCM"
        }

    def decrypt_file(self, input_path: Path, output_path: Path, nonce_b64: str, verify_checksum: Optional[str] = None) -> dict:
        """
        Decrypt a file and optionally verify integrity.

        Args:
            input_path: Path to encrypted file
            output_path: Path to save decrypted file
            nonce_b64: Nonce from encryption metadata
            verify_checksum: Optional SHA-256 checksum to verify plaintext

        Returns:
            Metadata dict with checksums
        """
        # Read encrypted data
        with open(input_path, 'rb') as f:
            ciphertext = f.read()

        # Calculate checksum of ciphertext
        checksum_ciphertext = hashlib.sha256(ciphertext).hexdigest()

        # Decrypt
        plaintext = self.decrypt_data(ciphertext, nonce_b64)

        # Calculate checksum of plaintext
        checksum_plaintext = hashlib.sha256(plaintext).hexdigest()

        # Verify checksum if provided
        if verify_checksum and checksum_plaintext != verify_checksum:
            raise ValueError(f"Checksum mismatch! Expected {verify_checksum}, got {checksum_plaintext}")

        # Write decrypted data
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(plaintext)

        return {
            "checksum_plaintext": checksum_plaintext,
            "checksum_ciphertext": checksum_ciphertext,
            "verified": verify_checksum is not None
        }

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new AES-256 key (32 bytes).

        Returns:
            Base64-encoded key suitable for environment variable
        """
        key = secrets.token_bytes(32)
        return base64.b64encode(key).decode('utf-8')

    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()


def generate_new_encryption_key():
    """Helper function to generate a new encryption key"""
    print("Generating new AES-256 encryption key...")
    key = EncryptionManager.generate_key()
    print(f"\nNew encryption key (base64-encoded):\n{key}")
    print(f"\nAdd this to your .env file:")
    print(f"ENCRYPTION_KEY={key}")
    return key


if __name__ == "__main__":
    # Generate a new key if run directly
    generate_new_encryption_key()
