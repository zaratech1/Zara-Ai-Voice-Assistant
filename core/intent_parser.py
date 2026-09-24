"""Pure intent parsing. Preserve original text outside this module."""
import re


def normalize(text):
    value = re.sub(r"\s+", " ", text.strip()).casefold()
    value = re.sub(r"[.!?]+$", "", value)
    return re.sub(r"^(?:hey\s+)?zara[,\s]+", "", value).strip()


def parse(text):
    original = re.sub(r"\s+", " ", text.strip())
    original = re.sub(r"^(?:hey\s+)?zara[,\s]+", "", original, flags=re.IGNORECASE).strip()
    whatsapp = re.fullmatch(r"send (?:a )?whatsapp message to (.+?) saying (.+)", original, re.IGNORECASE)
    if whatsapp:
        return ("whatsapp", (whatsapp.group(1).strip(), whatsapp.group(2).strip()))
    value = normalize(text)
    if not value:
        return ("empty", "")
    patterns = (
        (r"play (.+?) on youtube", "youtube_play"),
        (r"search youtube for (.+)", "youtube_search"),
        (r"search (.+?) on youtube", "youtube_search"),
        (r"(?:search|open) (.+?) on wikipedia", "wikipedia_search"),
        (r"wikipedia (.+)", "wikipedia_search"),
        (r"(?:search|open) (.+?) on google", "google_search"),
        (r"google (.+)", "google_search"),
        (r"search (.+)", "google_search"),
        (r"(?:open|launch|start) (.+)", "open"),
    )
    for pattern, intent in patterns:
        matched = re.fullmatch(pattern, value)
        if matched:
            return intent, matched.group(1).strip()
    return ("chat", value)
