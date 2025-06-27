import asyncio, html as html_lib
from enum import Enum

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ContentType, ChatAction
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    InputMediaPhoto, InputMediaVideo,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.client.default import DefaultBotProperties

from config import (BOT_TOKEN, CHANNEL_ID, ADMIN_IDS,
                    MAX_CAPTION_LEN, MAX_TEXT_LEN,
                    DEBUG_PREVIEW_LEN, DB_PATH)
from database import init_db
from services.translator import translate_html_preserve_format
from utils import raw_len
from ui import ru_button, en_button


# ────────────────────────── MODELS ──────────────────────────────────
class MediaType(str, Enum):
    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"


class Draft(StatesGroup):
    waiting_decision = State()
    waiting_custom_en = State()


# ────────────────────────── BOT CORE ────────────────────────────────
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()


# ────────────────────────── UI HELPERS ──────────────────────────────
def decision_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="draft_publish"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="draft_edit"),
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="draft_cancel")],
    ])


async def send_preview(admin_id: int, mtype: MediaType, data: dict) -> Message:
    if mtype == MediaType.TEXT:
        return await bot.send_message(admin_id, data["en_text"], reply_markup=decision_kb())
    elif mtype == MediaType.PHOTO:
        return await bot.send_photo(
            admin_id, data["ru_file_id"],
            caption=data["en_caption"], reply_markup=decision_kb())
    else:
        return await bot.send_video(
            admin_id, data["ru_file_id"],
            caption=data["en_caption"], reply_markup=decision_kb())


# ────────────────────────── Animation «Перевожу…» NOT WORKING ────────────────────
# async def animate_dots(msg: Message, stop: asyncio.Event) -> None:
#     dots = ["", ".", "..", "..."]
#     idx = 0
#     while not stop.is_set():
#         try:
#             await msg.edit_text(f"⏳ Перевожу{dots[idx % 4]}")
#         except Exception:
#             pass
#         idx += 1
#         try:
#             await asyncio.wait_for(stop.wait(), timeout=0.6)
#         except asyncio.TimeoutError:
#             continue
#
#
# # ────────────────────────── /start ──────────────────────────────────
@dp.message(CommandStart(), F.from_user.id.in_(ADMIN_IDS))
async def start_admin(msg: Message) -> None:
    await msg.answer(
        "Пришли пост на <b>русском</b> (текст, фото или видео) — бот переведёт, "
        "покажет превью и спросит, публиковать ли его."
    )


# ────────────────────────── RU-INPUT ────────────────────────────────
@dp.message(
    F.from_user.id.in_(ADMIN_IDS),
    StateFilter(None, Draft.waiting_decision)
)
async def handle_ru(msg: Message, state: FSMContext) -> None:
    data: dict[str, str] = {}

    # ---------- RU-content -----------------------------------------
    if msg.content_type == ContentType.TEXT:
        mtype = MediaType.TEXT
        data["ru_text"] = msg.html_text or ""
        if raw_len(data["ru_text"]) > MAX_TEXT_LEN:
            await msg.answer("⚠️ Текст вместе с тегами длиннее 4 096 символов.")
            return

    elif msg.content_type == ContentType.PHOTO:
        mtype, data["ru_file_id"] = MediaType.PHOTO, msg.photo[-1].file_id
        data["ru_caption"] = msg.html_text or ""
        if raw_len(data["ru_caption"]) > MAX_CAPTION_LEN:
            await msg.answer("⚠️ Подпись вместе с тегами длиннее 1 024 символов.")
            return

    elif msg.content_type == ContentType.VIDEO:
        mtype, data["ru_file_id"] = MediaType.VIDEO, msg.video.file_id
        data["ru_caption"] = msg.html_text or ""
        if raw_len(data["ru_caption"]) > MAX_CAPTION_LEN:
            await msg.answer("⚠️ Подпись вместе с тегами длиннее 1 024 символов.")
            return
    else:
        await msg.answer("Поддерживаются только текст, фото или видео.")
        return

    # ---------- «Translating…» ----------------------------------------
    wait_msg = await msg.answer("⏳ Перевожу ...")
    stop_anim = asyncio.Event()
    await bot.send_chat_action(msg.chat.id, ChatAction.TYPING)

    # ---------- Auto-translator EN ------------------------------------
    try:
        if mtype == MediaType.TEXT:
            data["en_text"] = translate_html_preserve_format(data["ru_text"])
            if raw_len(data["en_text"]) > MAX_TEXT_LEN:  # ← raw_len
                raise ValueError("EN-текст вместе с тегами > 4 096 символов")

        else:
            en_cap = translate_html_preserve_format(data["ru_caption"])
            if raw_len(en_cap) > MAX_CAPTION_LEN:  # ← raw_len
                raise ValueError("EN-подпись вместе с тегами > 1 024 символов")
            data["en_caption"] = en_cap

    except ValueError as err:
        stop_anim.set()
        await wait_msg.delete()
        preview = html_lib.escape((data.get("en_text") or data.get("en_caption", ""))[:DEBUG_PREVIEW_LEN])
        await msg.answer(f"⚠️ {err}\n<b>Draft:</b>\n<code>{preview}</code>")
        return

    # ---------- Preview --------------------------------------------
    stop_anim.set()
    await wait_msg.delete()
    data["media_type"] = mtype.value
    preview_msg = await send_preview(msg.from_user.id, mtype, data)

    await state.update_data(**data,
                            preview_id=preview_msg.message_id,
                            preview_type=mtype.value)
    await state.set_state(Draft.waiting_decision)


# ─────────────────── PUBLISH / EDIT / CANCEL ────────────────────────
@dp.callback_query(
    F.data.in_(["draft_publish", "draft_edit", "draft_cancel"]),
    Draft.waiting_decision
)
async def draft_decision(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    mtype = MediaType(data["media_type"])
    prev_id = data["preview_id"]

    async def update_preview(text: str):
        """Изменить текст / caption превью-сообщения и убрать кнопки."""
        if mtype == MediaType.TEXT:
            await bot.edit_message_text(text, cb.from_user.id, prev_id)
        else:
            await bot.edit_message_caption(cb.from_user.id, prev_id, caption=text)

    # ---------- CANCEL --------------------------------------------
    if cb.data == "draft_cancel":
        await update_preview("❌ Черновик отменён")
        await state.clear()
        await cb.answer()
        return

    # ---------- EDIT ----------------------------------------------
    if cb.data == "draft_edit":
        await cb.answer("Пришлите новый EN-вариант…", show_alert=True)
        await state.set_state(Draft.waiting_custom_en)
        return

    # ---------- PUBLISH -------------------------------------------
    try:
        if mtype == MediaType.TEXT:
            sent = await bot.send_message(CHANNEL_ID, data["ru_text"], reply_markup=ru_button(0))
        elif mtype == MediaType.PHOTO:
            sent = await bot.send_photo(CHANNEL_ID, data["ru_file_id"],
                                        caption=data["ru_caption"], reply_markup=ru_button(0))
        else:
            sent = await bot.send_video(CHANNEL_ID, data["ru_file_id"],
                                        caption=data["ru_caption"], reply_markup=ru_button(0))
    except Exception as e:
        await cb.answer(f"Не удалось опубликовать: {e}", show_alert=True)
        await state.clear()
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO posts (channel_msg_id, media_type, ru_text, en_text, "
            "ru_file_id, en_file_id, ru_caption, en_caption, current_lang) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ru')",
            (sent.message_id, mtype.value,
             data.get("ru_text"), data.get("en_text"),
             data.get("ru_file_id"), data.get("ru_file_id"),
             data.get("ru_caption"), data.get("en_caption")),
        )
        pid = cur.lastrowid
        await db.commit()

    await sent.edit_reply_markup(reply_markup=ru_button(pid))
    await update_preview("✅ Пост опубликован!")
    await state.clear()
    await cb.answer()


# ─────────── EN after «Edit» ───────────────────
@dp.message(F.from_user.id.in_(ADMIN_IDS), Draft.waiting_custom_en)
async def custom_en(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    mtype = MediaType(data["media_type"])

    if (mtype == MediaType.TEXT and msg.content_type != ContentType.TEXT) or \
            (mtype == MediaType.PHOTO and msg.content_type != ContentType.PHOTO) or \
            (mtype == MediaType.VIDEO and msg.content_type != ContentType.VIDEO):
        await msg.answer("Тип медиа не совпадает с оригиналом.")
        return

    if mtype == MediaType.TEXT:
        data["en_text"] = msg.html_text or ""
        if raw_len(data["en_text"]) > MAX_TEXT_LEN:
            await msg.answer("⚠️ EN-текст вместе с тегами > 4 096 символов.")
            return
    else:
        if msg.photo:
            data["ru_file_id"] = msg.photo[-1].file_id
        elif msg.video:
            data["ru_file_id"] = msg.video.file_id

        cap = msg.html_text or ""
        if raw_len(cap) > MAX_CAPTION_LEN:
            await msg.answer("⚠️ EN-подпись вместе с тегами > 1 024 символов.")
            return
        data["en_caption"] = cap

    await state.update_data(**data)
    prev_msg = await send_preview(msg.from_user.id, mtype, data)
    await state.update_data(preview_id=prev_msg.message_id)
    await state.set_state(Draft.waiting_decision)


# ─────────────── Switch RU/EN in channel ────────────────────────
@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_lang(cb: CallbackQuery) -> None:
    pid = int(cb.data.split("_", 1)[1])

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM posts WHERE id=?", (pid,)) as cur:
            row = await cur.fetchone()

    if not row:
        await cb.answer("Post not found", show_alert=True)
        return

    (_id, mid, mtype, ru_text, en_text,
     ru_file, en_file, ru_cap, en_cap, cur_lang) = row
    new_lang = "en" if cur_lang == "ru" else "ru"

    try:
        if mtype == MediaType.TEXT.value:
            await bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=mid,
                text=en_text if new_lang == "en" else ru_text,
                reply_markup=en_button(pid) if new_lang == "en" else ru_button(pid)
            )

        elif mtype == MediaType.PHOTO.value:
            await bot.edit_message_media(
                chat_id=CHANNEL_ID,
                message_id=mid,
                media=InputMediaPhoto(
                    media=ru_file,
                    caption=en_cap if new_lang == "en" else ru_cap),
                reply_markup=en_button(pid) if new_lang == "en" else ru_button(pid)
            )

        else:
            await bot.edit_message_media(
                chat_id=CHANNEL_ID,
                message_id=mid,
                media=InputMediaVideo(
                    media=ru_file,
                    caption=en_cap if new_lang == "en" else ru_cap),
                reply_markup=en_button(pid) if new_lang == "en" else ru_button(pid)
            )

    except Exception as e:
        await cb.answer(f"Ошибка: {e}", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE posts SET current_lang=? WHERE id=?", (new_lang, pid))
        await db.commit()


# ─────────────────────────── MAIN ───────────────────────────────────
async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
