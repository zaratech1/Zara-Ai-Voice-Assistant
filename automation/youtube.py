import logging
import webbrowser
from urllib.parse import quote

from automation import result
from automation.websites import open_url

LOG = logging.getLogger(__name__)


def search(query):
    return open_url("https://www.youtube.com/results?search_query=" + quote(query),
                    f"YouTube results for {query}", "youtube_search")


def play(query):
    try:
        import pywhatkit
        pywhatkit.playonyt(query)
        return result(True, "youtube_play", query, f"Opening a YouTube result for {query}.")
    except Exception:
        LOG.warning("Automatic YouTube playback failed; opening results", exc_info=True)
        fallback = search(query)
        if fallback["success"]:
            fallback["message"] = "Automatic playback was unavailable. I opened YouTube search results instead."
        return fallback
