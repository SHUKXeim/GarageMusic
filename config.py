# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STORAGE_CHAT_ID = int(os.getenv("STORAGE_CHAT_ID")) if os.getenv("STORAGE_CHAT_ID") else None
BOT_VERSION = os.getenv("BOT_VERSION", "v1.1")
