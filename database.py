"""SQLite-обёртка (init и простые запросы)."""

import aiosqlite
from config import DB_PATH


INIT_SQL = """
CREATE TABLE IF NOT EXISTS posts(
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_msg_id  INTEGER NOT NULL,
    media_type      TEXT    NOT NULL,
    ru_text         TEXT,
    en_text         TEXT,
    ru_file_id      TEXT,
    en_file_id      TEXT,
    ru_caption      TEXT,
    en_caption      TEXT,
    current_lang    TEXT    NOT NULL DEFAULT 'ru'
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(INIT_SQL)
        await db.commit()
