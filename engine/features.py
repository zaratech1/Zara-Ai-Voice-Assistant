import os
import re
import webbrowser
import urllib.parse  
from playsound import playsound
from engine.config import ASSITANT_NAME
from engine.command import speak  
import pywhatkit as kit

# Play startup sound
def playAssistantsound():
    music_dir = "front\\assets\\audio\\start_sound.mp3"
    playsound(music_dir)


def openCommand(query):
    # Clean text
    query = query.lower()
    query = query.replace(ASSITANT_NAME.lower(), "")
    query = query.replace("open", "")
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
    apps = {
        "vs code": r'"C:\Users\YourUserName\AppData\Local\Programs\Microsoft VS Code\Code.exe"',
        "vscode": r'"C:\Users\YourUserName\AppData\Local\Programs\Microsoft VS Code\Code.exe"'
        # add only apps that don't open automatically
    }

    for name, path in apps.items():
        if name in query:
            speak(f"opening {name}")
            os.system(f'start "" {path}')
            return

    # ------ 2) Try opening as website (.com) ------
    # e.g. "open youtube" -> https://youtube.com
    sitename = query.split()[-1]   # last word → youtube, instagram etc.
    url = f"https://{sitename}.com"

    speak(f"opening {sitename}")
    webbrowser.open(url)
    return

def playYoutube(query):
    search_term = extract_yt_term(query)
    speak("playing"+search_term+"on youtube")
    kit.playonyt(search_term)

def extract_yt_term(command):
    pattern = r'play\s+(.*?)\s+on\s+youtube'
    match = re.search(pattern, command, re.IGNORECASE)
    return match.group(1) if match else None
