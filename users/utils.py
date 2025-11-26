from cryptography.fernet import Fernet
from config import settings

# 32 byte secret base64 bilan
fernet = Fernet(settings.CRYPTO_KEY)

def encrypt_value(value):
    if value is None:
        return None
    return fernet.encrypt(str(value).encode()).decode()

def decrypt_value(value: str) -> str:
    """Shifrlangan matnni decrypt qilish"""
    if not value:
        return ""
    return fernet.decrypt(value.encode()).decode()
