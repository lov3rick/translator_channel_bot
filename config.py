"""Глобальная конфигурация: токены, лимиты, пути."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN  = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")          # "@channel" или -100…
ADMIN_IDS  = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

BASE_DIR   = Path(__file__).resolve().parent
DB_PATH    = BASE_DIR / "posts.db"

# Лимиты Telegram (видимые символы)
MAX_CAPTION_LEN = 1_024
MAX_TEXT_LEN    = 4_096

# Для отладочных превью при ошибках
DEBUG_PREVIEW_LEN = 1_500
