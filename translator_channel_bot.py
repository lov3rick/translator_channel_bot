import asyncio
import os
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ContentType
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
    InputMediaPhoto,
    InputMediaVideo,
)
from aiogram.client.default import DefaultBotProperties

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
DB_PATH = Path("posts.db")

ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
}


class MediaType(str, Enum):
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"


class PostStates(StatesGroup):
    waiting_en_version = State()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS posts
            (
                id
                INTEGER
                PRIMARY
                KEY
                AUTOINCREMENT,
                channel_msg_id
                INTEGER
                NOT
                NULL,
                media_type
                TEXT
                NOT
                NULL,
                ru_text
                TEXT,
                en_text
                TEXT,
                ru_file_id
                TEXT,
                en_file_id
                TEXT,
                ru_caption
                TEXT,
                en_caption
                TEXT,
                current_lang
                TEXT
                NOT
                NULL
                DEFAULT
                'ru'
            );
            """
        )
        await db.commit()


def ru_button(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🇬🇧 Show in English", callback_data=f"toggle_{post_id}")]]
    )


def en_button(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🇷🇺 Показать на русском", callback_data=f"toggle_{post_id}")]]
    )


bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


@dp.message(CommandStart(), F.from_user.id.in_(ADMIN_IDS))
async def start_admin(msg: Message):
    await msg.answer(
        "Привет! Пришли мне пост на <b>русском</b> (текст, фото или видео). После этого пришли <b>английскую</b> версию."
    )


@dp.message(StateFilter(None), F.from_user.id.in_(ADMIN_IDS))
async def receive_ru(msg: Message, state: FSMContext):
    data = {}
    if msg.content_type == ContentType.TEXT:
        data["media_type"] = MediaType.TEXT
        data["ru_text"] = msg.html_text
    elif msg.content_type == ContentType.PHOTO:
        data["media_type"] = MediaType.PHOTO
        data["ru_file_id"] = msg.photo[-1].file_id
        data["ru_caption"] = msg.html_text or ""
    elif msg.content_type == ContentType.VIDEO:
        data["media_type"] = MediaType.VIDEO
        data["ru_file_id"] = msg.video.file_id
        data["ru_caption"] = msg.html_text or ""
    else:
        await msg.answer("Поддерживаются только текст, фото и видео.")
        return

    await state.set_state(PostStates.waiting_en_version)
    await state.update_data(**data)
    await msg.answer("➕ Теперь пришли <b>английскую</b> версию этого поста.")


@dp.message(PostStates.waiting_en_version, F.from_user.id.in_(ADMIN_IDS))
async def receive_en(msg: Message, state: FSMContext):
    data = await state.get_data()
    media_type: MediaType = data["media_type"]

    if media_type == MediaType.TEXT and msg.content_type == ContentType.TEXT:
        data["en_text"] = msg.html_text
    elif media_type == MediaType.PHOTO and msg.content_type == ContentType.PHOTO:
        data["en_file_id"] = msg.photo[-1].file_id
        data["en_caption"] = msg.html_text or ""
    elif media_type == MediaType.VIDEO and msg.content_type == ContentType.VIDEO:
        data["en_file_id"] = msg.video.file_id
        data["en_caption"] = msg.html_text or ""
    else:
        await msg.answer("Тип контента не совпадает с русским сообщением. Пришли ту же медиа-тип.")
        return

    if media_type == MediaType.TEXT:
        sent = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=data["ru_text"],
            reply_markup=ru_button(0),
        )
    elif media_type == MediaType.PHOTO:
        sent = await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=data["ru_file_id"],
            caption=data.get("ru_caption", ""),
            reply_markup=ru_button(0),
        )
    else:
        sent = await bot.send_video(
            chat_id=CHANNEL_ID,
            video=data["ru_file_id"],
            caption=data.get("ru_caption", ""),
            reply_markup=ru_button(0),
        )

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO posts (channel_msg_id, media_type, ru_text, en_text, ru_file_id, en_file_id, ru_caption,
                               en_caption, current_lang)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ru')
            """,
            (
                sent.message_id,
                media_type.value,
                data.get("ru_text"),
                data.get("en_text"),
                data.get("ru_file_id"),
                data.get("en_file_id"),
                data.get("ru_caption"),
                data.get("en_caption"),
            ),
        )
        post_id = cursor.lastrowid
        await db.commit()

    await sent.edit_reply_markup(reply_markup=ru_button(post_id))

    await msg.answer("✅ Пост опубликован!")
    await state.clear()


@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_lang(callback: CallbackQuery):
    post_id = int(callback.data.split("_", 1)[1])

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM posts WHERE id = ?", (post_id,)) as cur:
            row = await cur.fetchone()

    if not row:
        await callback.answer("Post not found", show_alert=True)
        return

    (
        _id,
        channel_msg_id,
        media_type,
        ru_text,
        en_text,
        ru_file_id,
        en_file_id,
        ru_caption,
        en_caption,
        current_lang,
    ) = row

    new_lang = "en" if current_lang == "ru" else "ru"

    if media_type == MediaType.TEXT.value:
        new_text = en_text if new_lang == "en" else ru_text
        await bot.edit_message_text(
            chat_id=CHANNEL_ID,
            message_id=channel_msg_id,
            text=new_text,
            reply_markup=en_button(post_id) if new_lang == "en" else ru_button(post_id),
        )
    elif media_type == MediaType.PHOTO.value:
        new_file = en_file_id if new_lang == "en" else ru_file_id
        new_caption = en_caption if new_lang == "en" else ru_caption
        await bot.edit_message_media(
            chat_id=CHANNEL_ID,
            message_id=channel_msg_id,
            media=InputMediaPhoto(media=new_file, caption=new_caption),
            reply_markup=en_button(post_id) if new_lang == "en" else ru_button(post_id),
        )
    else:
        new_file = en_file_id if new_lang == "en" else ru_file_id
        new_caption = en_caption if new_lang == "en" else ru_caption
        await bot.edit_message_media(
            chat_id=CHANNEL_ID,
            message_id=channel_msg_id,
            media=InputMediaVideo(media=new_file, caption=new_caption),
            reply_markup=en_button(post_id) if new_lang == "en" else ru_button(post_id),
        )

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE posts SET current_lang = ? WHERE id = ?", (new_lang, post_id))
        await db.commit()


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())