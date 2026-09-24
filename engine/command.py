import pyttsx3
import speech_recognition as sr
import eel



def speak(text):
    eel.DisplayMessage(text)
    try:
        engine = pyttsx3.init('sapi5')
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[min(1, len(voices) - 1)].id)
        engine.setProperty('rate', 174)
        engine.say(text)
        engine.runAndWait()
    except Exception as error:
        print(f"Text-to-speech unavailable: {error}")


def takecommand():
    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print('Listening...')
            eel.DisplayMessage('Listening...')
            r.pause_threshold = 1
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=10, phrase_time_limit=6)

        print('Recognizing')
        eel.DisplayMessage('Recognizing...')
        query = r.recognize_google(audio, language='en-IN')
        print(f"user said: {query}")
        eel.DisplayMessage(query)
    except (sr.WaitTimeoutError, sr.UnknownValueError):
        return ""
    except (sr.RequestError, OSError, AttributeError) as error:
        print(f"Speech recognition unavailable: {error}")
        eel.DisplayMessage("Microphone or speech recognition is unavailable. Type a command instead.")
        return None

    return query.lower()

@eel.expose
def allCommands(command=None):
    try:
        query = command.strip().lower() if isinstance(command, str) else takecommand()
        print("Query:", query)

        if query is None:
            return

        # If nothing was heard / recognized
        if not query:
            print("Empty query, nothing recognized.")
            eel.DisplayMessage("I didn't catch that.")
            return

        if query.startswith("play ") and query.endswith(" on youtube"):
            from engine.features import playYoutube
            playYoutube(query)

        elif query == "open" or query.startswith("open "):
            from engine.features import openCommand
            openCommand(query)

        else:
            # This is your "not run" situation
            print("not run")
            eel.DisplayMessage("I don't know how to handle that yet.")

    except Exception as error:
        print(f"Command failed: {error}")
        eel.DisplayMessage("Sorry, that command failed. Please try again.")

    finally:
        # This will run even if an error happens above
        eel.ShowHood()
