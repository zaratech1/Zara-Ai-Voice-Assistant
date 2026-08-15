import pyttsx3
import speech_recognition as sr
import eel
import time



def speak(text):
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id)
    engine.setProperty('rate', 174) 
    eel.DisplayMessage(text)
    engine.say(text)
    engine.runAndWait()


def takecommand():
    r = sr.Recognizer()

    with sr.Microphone() as source:
        print('Listening...')
        eel.DisplayMessage('Listening...')
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source)

        audio = r.listen(source, 10, 6)
    
    try:
        print('Recognizing')
        eel.DisplayMessage('Recognizing...')
        query = r.recognize_google(audio, language= 'en-in')
        print(f"user said: {query}")
        eel.DisplayMessage(query)
        time.sleep(1)
       
        
    except Exception as e:
        return ""

    return query.lower()

@eel.expose
def allCommands():
    try:
        query = takecommand()
        print("Query:", query)

        # If nothing was heard / recognized
        if not query:
            print("Empty query, nothing recognized.")
            eel.DisplayMessage("I didn't catch that.")
            return

        if "open" in query:
            from engine.features import openCommand
            openCommand(query)

        elif "on youtube" in query:
            from engine.features import playYoutube
            playYoutube(query)

        else:
            # This is your "not run" situation
            print("not run")
            eel.DisplayMessage("I don't know how to handle that yet.")

    finally:
        # This will run even if an error happens above
        eel.ShowHood()