import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _fernet() -> Fernet:
    key = get_settings().bank_data_encryption_key.strip()
    if not key:
        raise RuntimeError("Bank data encryption is not configured.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("Bank data encryption key is invalid.") from exc

def encrypt_provider_account_id(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")

def decrypt_provider_account_id(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("Stored bank connection credentials could not be decrypted.") from exc

def provider_account_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
