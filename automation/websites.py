import logging
import webbrowser
from urllib.parse import quote, urlparse

from automation import result

LOG = logging.getLogger(__name__)


def valid_url(url):
    try:
        parsed = urlparse(url)
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and not parsed.username and not parsed.password and not any(char.isspace() for char in url))
    except ValueError:
        return False


def open_url(url, name, action="open_website"):
    if not valid_url(url):
        return result(False, action, name, "That website address is invalid.")
    try:
        if not webbrowser.open(url):
            return result(False, action, name, "I couldn't open the browser.")
        return result(True, action, name, f"Opening {name}.")
    except Exception:
        LOG.exception("Browser open failed")
        return result(False, action, name, f"I couldn't open {name}.")


def address_for(text):
    candidate = text.strip()
    if not candidate or any(char.isspace() for char in candidate):
        return None
    url = candidate if "://" in candidate else "https://" + candidate
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if not valid_url(url) or "." not in (parsed.hostname or ""):
        return None
    return url


def google_search(query):
    return open_url("https://www.google.com/search?q=" + quote(query), f"Google results for {query}", "google_search")


def wikipedia_search(query):
    return open_url("https://en.wikipedia.org/wiki/Special:Search?search=" + quote(query),
                    f"Wikipedia results for {query}", "wikipedia_search")
