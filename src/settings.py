import os
import subprocess
from dataclasses import dataclass
from logging import DEBUG, INFO

from lib.aws.secrets_manager import get_secret

print("Loading settings...")


@dataclass
class Settings:
    SRC_VERSION: str
    STAGE: str
    APP_NAME: str
    LOGLEVEL: int
    TIMEZONE: str
    FERNET_KEY: str
    """A URL-safe base64-encoded 32-byte key. Use Fernet.generate_key().decode() to generate a new key."""
    BOT_USERID: str
    """Bluesky Bot User Handle"""
    BOT_APP_PASSWORD: str
    """Bluesky Bot App Password"""
    FOLLOWED_QUEUE_URL: str
    USERINFO_BUCKET_NAME: str

    def __new__(cls, *args, **kargs):
        """Singletonパターン"""
        if not hasattr(cls, "_instance"):
            cls._instance = super(Settings, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """設定を読み込む"""
        _secrets = get_secret(f"{os.getenv('SECRET_NAME')}")
        self.FERNET_KEY = _secrets.get("fernet_key")
        self.BOT_USERID = _secrets.get("bot_userid")
        self.BOT_APP_PASSWORD = _secrets.get("bot_app_password")
        self.APP_NAME = os.getenv("APP_NAME", default="wmput")
        self.STAGE = os.getenv("STAGE", default="dev")
        self.LOGLEVEL = INFO if self.STAGE.lower == "prod" else DEBUG
        self.SRC_VERSION = self._get_src_version()
        self.TIMEZONE = os.getenv("TIMEZONE", default="Asia/Tokyo")
        self.FOLLOWED_QUEUE_URL = os.getenv("FOLLOWED_QUEUE_URL")
        self.USERINFO_BUCKET_NAME = os.getenv("USERINFO_BUCKET_NAME")
        print(f"Application Version: {self.SRC_VERSION}")

    def _get_src_version(self) -> str:
        """ソースコードのcommit hashをバージョンとして取得する"""
        try:
            revparsed: str = subprocess.check_output("git rev-parse --short HEAD").decode("utf-8")
            return revparsed.strip()
        except BaseException:
            return "0.0.0"


settings = Settings()
