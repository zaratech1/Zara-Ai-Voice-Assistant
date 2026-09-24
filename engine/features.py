import os
import re
import shutil
import webbrowser
import urllib.parse  
from pathlib import Path
from playsound import playsound
from engine.config import ASSITANT_NAME
from engine.command import speak

# Play startup sound
def playAssistantsound():
    music_dir = Path(__file__).resolve().parent.parent / "front" / "assets" / "audio" / "start_sound.mp3"
    try:
        playsound(str(music_dir))
    except Exception as error:
        print(f"Could not play startup sound: {error}")


def openCommand(query):
    # Clean text
    query = query.lower()
    query = query.replace(ASSITANT_NAME.lower(), "")
    query = re.sub(r"^open\s+", "", query)
    query = query.strip()

    if query == "":
        speak("what should I open?")
        return

    # ------ 0) GOOGLE / WIKIPEDIA SEARCH HANDLING ------

    # Example: "open python tutorial on google"
    if " on google" in query:
        topic = query.replace("on google", "").strip()

        if topic == "" or topic == "google":
            speak("opening google")
            webbrowser.open("https://www.google.com")
        else:
            speak(f"searching {topic} on google")
            q = urllib.parse.quote(topic)
            webbrowser.open(f"https://www.google.com/search?q={q}")
        return

    # Example: "open india history on wikipedia" or "open wikipedia"
    if " on wikipedia" in query or "wikipedia" in query:
        topic = (query
                 .replace("on wikipedia", "")
                 .replace("wikipedia", "")
                 .strip())

        if topic == "":
            speak("opening wikipedia")
            webbrowser.open("https://en.wikipedia.org")
        else:
            speak(f"searching {topic} on wikipedia")
            q = urllib.parse.quote(topic)
            # use search page instead of direct article for better results
            webbrowser.open(f"https://en.wikipedia.org/wiki/Special:Search?search={q}")
        return

    # ------ 1) SPECIAL APPS (only few apps manual) ------
    if query in ("vs code", "vscode", "visual studio code"):
        code = shutil.which("code") or shutil.which("Code.exe")
        if code:
            speak("opening VS Code")
            os.startfile(code)
        else:
            speak("VS Code is not installed or is not on your PATH")
        return

    # ------ 2) Try opening as website (.com) ------
    # e.g. "open youtube" -> https://youtube.com
    sitename = query.strip()
    if " " in sitename:
        speak(f"searching {sitename}")
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(sitename)}")
        return
    url = sitename if sitename.startswith(("https://", "http://")) else f"https://{sitename if '.' in sitename else sitename + '.com'}"

    speak(f"opening {sitename}")
    webbrowser.open(url)
    return

def playYoutube(query):
    search_term = extract_yt_term(query)
    if not search_term:
        speak("What should I play on YouTube?")
        return
    speak(f"playing {search_term} on youtube")
    try:
        import pywhatkit as kit
        kit.playonyt(search_term)
    except Exception as error:
        print(f"YouTube playback unavailable: {error}")
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(search_term)}")

def extract_yt_term(command):
    pattern = r'play\s+(.*?)\s+on\s+youtube'
    match = re.search(pattern, command, re.IGNORECASE)
    return match.group(1) if match else None
