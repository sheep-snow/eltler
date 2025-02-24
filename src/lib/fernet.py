from cryptography.fernet import Fernet

from settings import settings


def encrypt(message: str) -> str:
    return Fernet(settings.FERNET_KEY).encrypt(message.encode()).decode()


def decrypt(encrypted: str) -> str:
    return Fernet(settings.FERNET_KEY).decrypt(encrypted)
