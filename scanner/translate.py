"""Перевод заголовков на русский через бесплатные сервисы. Не получилось — возвращаем оригинал."""
import logging
import re

import requests

log = logging.getLogger(__name__)

_CYRILLIC = re.compile(r"[а-яё]", re.IGNORECASE)
_LATIN = re.compile(r"[a-z]", re.IGNORECASE)


def needs_translation(text: str) -> bool:
    return bool(_LATIN.search(text)) and not _CYRILLIC.search(text)


def _google(text: str, session: requests.Session) -> str | None:
    resp = session.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "auto", "tl": "ru", "dt": "t", "q": text},
        timeout=10,
    )
    if resp.status_code != 200 or "json" not in resp.headers.get("Content-Type", ""):
        return None
    # Ответ: [[["перевод", "оригинал", ...], ...], ...] — перевод может быть разбит на куски.
    return "".join(part[0] for part in resp.json()[0] if part and part[0])


def _mymemory(text: str, session: requests.Session) -> str | None:
    resp = session.get(
        "https://api.mymemory.translated.net/get",
        params={"q": text, "langpair": "en|ru"},
        timeout=10,
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    result = data.get("responseData", {}).get("translatedText") or ""
    # При исчерпанном лимите сервис возвращает предупреждение вместо перевода.
    if data.get("responseStatus") != 200 or "MYMEMORY WARNING" in result:
        return None
    return result


class Translator:
    def __init__(self):
        self.session = requests.Session()
        self.cache: dict[str, str] = {}

    def __call__(self, text: str) -> str:
        if not needs_translation(text):
            return text
        if text in self.cache:
            return self.cache[text]
        for service in (_google, _mymemory):
            try:
                result = service(text, self.session)
            except (requests.RequestException, ValueError, LookupError, TypeError) as e:
                log.debug("%s: %s", service.__name__, e)
                continue
            if result and _CYRILLIC.search(result):
                self.cache[text] = result
                return result
        log.warning("Не удалось перевести: %s", text)
        return text
