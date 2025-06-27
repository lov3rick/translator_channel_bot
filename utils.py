"""
Мелкие утилиты для работы с HTML-текстом.
"""

import html as html_lib
from bs4 import BeautifulSoup


def visible_len(html_text: str | None) -> int:
    """
    Количество «видимых» символов — без HTML-тегов и
    HTML-сущностей (&amp; → &).
    """
    if not html_text:
        return 0
    raw = html_lib.unescape(html_text)
    return len(BeautifulSoup(raw, "html.parser").get_text())


def raw_len(html_text: str | None) -> int:
    """
    Фактическая длина строки, которая уйдёт в Telegram (вместе с тегами).
    Именно она ограничена 1 024 симв. для подписи и 4 096 для текста.
    """
    return len(html_text or "")
