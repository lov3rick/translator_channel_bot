from bs4 import BeautifulSoup, NavigableString
from deep_translator import GoogleTranslator

_ru2en = GoogleTranslator(source="ru", target="en")


def translate_html_preserve_format(html_text: str,
                                   source: str = "ru",
                                   target: str = "en") -> str:
    if not html_text:
        return ""

    translator = _ru2en if source == "ru" and target == "en" \
        else GoogleTranslator(source=source, target=target)

    soup = BeautifulSoup(html_text, "html.parser")

    for node in soup.find_all(string=True):
        text = str(node)
        if not text.strip():
            continue

        try:
            translated = translator.translate(text)
        except Exception:
            translated = None

        if translated:
            leading  = len(text) - len(text.lstrip())
            trailing = len(text) - len(text.rstrip())
            node.replace_with(NavigableString(f"{' '*leading}{translated}{' '*trailing}"))

    return str(soup)
