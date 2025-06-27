# ui.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def ru_button(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇬🇧 Show in English",
                                  callback_data=f"toggle_{post_id}")]
        ]
    )

def en_button(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Показать на русском",
                                  callback_data=f"toggle_{post_id}")]
        ]
    )
