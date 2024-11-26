import os
from pathlib import Path
from typing import Any, List
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic.v1 import BaseSettings, validator

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = os.path.join(BASE_DIR, "prod.env")
DEBUG = True
import logging

logger = logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Emoji ranglarini qo'shamiz
LOG_COLORS = {
    'INFO': '🔵',
    'WARNING': '⚠️',
    'ERROR': '🔴',
    'SUCCESS': '✅'
}

class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: str
    WEBHOOK_HOST: str = "https://590a-213-230-118-68.ngrok-free.app"  # Ngrok URL
    WEBHOOK_PATH: str = "/bot/webhook/{token}"
    ADMIN: int = 889121031

    # Webhook URL composition
    @property
    def WEBHOOK_URL(self) -> str:
        return f"{self.WEBHOOK_HOST}{self.WEBHOOK_PATH}"

    # Update settings
    SLEEP_TIME: float = 0.3
    ALLOWED_CONTENT_TYPES: List[str] = [
        "text",
        "photo",
        "audio",
        "video",
        "video_note",
        "voice"
    ]
    USED_UPDATE_TYPES: List[str] = [
        "message",
        "callback_query",
        "chat_member"
    ]

    # Bot settings
    MAX_CONNECTIONS: int = 100
    WEBHOOK_MAX_CONNECTIONS: int = 40
    RETRY_AFTER: int = 3
    MAX_RETRIES: int = 3

    # Additional settings
    DEFAULT_PARSE_MODE: str = "HTML"
    MESSAGE_RATE_LIMIT: int = 30
    COMMAND_RATE_LIMIT: int = 10
    MEDIA_GROUP_RATE_LIMIT: int = 10

    # Validators
    @validator("WEBHOOK_HOST")
    def validate_webhook_host(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook host must start with http:// or https://")
        return v.rstrip("/")  # Remove trailing slash

    @validator("BOT_TOKEN")
    def validate_bot_token(cls, v):
        if not v or len(v.split(":")) != 2:
            raise ValueError("Invalid bot token format")
        return v

    class Config:
        env_file = ENV_FILE
        env_file_encoding = 'utf-8'
        case_sensitive = True


# Initialize settings
try:
    settings_conf = Settings()
except Exception as e:
    raise Exception(f"Failed to load settings: {e}. Make sure {ENV_FILE} exists and contains required values.")

# Scheduler configuration
scheduler_config = {
    'jobstores': {
        'default': SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")
    },
    'executors': {
        'default': AsyncIOExecutor(),
        'processpool': ProcessPoolExecutor(max_workers=1)
    },
    'job_defaults': {
        'misfire_grace_time': 15 * 60,
        'coalesce': False,
        'max_instances': 1,
    }
}

# Initialize scheduler
try:
    scheduler = AsyncIOScheduler(**scheduler_config)
except Exception as e:
    raise Exception(f"Failed to initialize scheduler: {e}")