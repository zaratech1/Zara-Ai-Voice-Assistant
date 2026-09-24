"""ZARA desktop entry point and Eel API."""
import logging
import threading

import eel

from config import DATA, FRONT, LOG_FILE
from core.assistant import Assistant
from database.db import Database
from database.repositories import Repository

DATA.mkdir(exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
eel.init(str(FRONT))
repository = Repository(Database())


def emit(event, payload):
    try:
        eel.backend_event(event, payload)
    except Exception:
        logging.getLogger(__name__).debug("No frontend connected for %s", event)


assistant = Assistant(repository, emit)


def safe_call(operation):
    try:
        return {"ok": True, "data": operation()}
    except (ValueError, TypeError, KeyError) as error:
        return {"ok": False, "error": str(error)}
    except Exception:
        logging.getLogger(__name__).exception("Eel API request failed")
        return {"ok": False, "error": "The request failed. Please try again."}


@eel.expose
def bootstrap():
    def load():
        assistant.activate()
        return {"chats": repository.chats(), "settings": repository.settings(),
                "voices": assistant.speech.voices()}
    return safe_call(load)


@eel.expose
def send_message(text, chat_id):
    return safe_call(lambda: assistant.send_message(text, chat_id))


@eel.expose
def start_listening(chat_id):
    return safe_call(lambda: assistant.start_listening(chat_id))


@eel.expose
def stop_listening():
    return safe_call(assistant.stop_listening)


@eel.expose
def get_chat_history(chat_id):
    return safe_call(lambda: repository.messages(chat_id))


@eel.expose
def set_active_chat(chat_id):
    return safe_call(lambda: assistant.set_active_chat(chat_id))


@eel.expose
def create_chat():
    return safe_call(repository.create_chat)


@eel.expose
def delete_chat(chat_id):
    return safe_call(lambda: repository.delete_chat(chat_id))


@eel.expose
def rename_chat(chat_id, title):
    return safe_call(lambda: repository.rename_chat(chat_id, title))


@eel.expose
def get_settings():
    return safe_call(repository.settings)


@eel.expose
def update_settings(changes):
    return safe_call(lambda: assistant.update_settings(changes))


@eel.expose
def get_registry(kind):
    return safe_call(lambda: repository.registry(kind))


@eel.expose
def save_mapping(kind, data):
    return safe_call(lambda: repository.save_mapping(kind, data))


@eel.expose
def delete_mapping(kind, identifier):
    return safe_call(lambda: repository.delete_mapping(kind, identifier))


@eel.expose
def get_contacts():
    return safe_call(repository.contacts)


@eel.expose
def save_contact(name, phone, aliases="", identifier=None):
    return safe_call(lambda: repository.save_contact(name, phone, aliases, identifier))


@eel.expose
def delete_contact(identifier):
    return safe_call(lambda: repository.delete_contact(identifier))


@eel.expose
def confirm_whatsapp(token, approved):
    return safe_call(lambda: assistant.confirm_whatsapp(token, approved))


@eel.expose
def send_whatsapp_message(contact, message, chat_id):
    return safe_call(lambda: assistant.send_message(
        f"send whatsapp message to {contact} saying {message}", chat_id))


@eel.expose
def test_ai_connection():
    return safe_call(assistant.test_ai)


@eel.expose
def test_voice():
    return safe_call(lambda: assistant.speech.speak("Hello, I'm ZARA. Your voice is working.", force=True))


@eel.expose
def open_application(name, chat_id):
    return safe_call(lambda: assistant.send_message("open " + name, chat_id))


@eel.expose
def open_website(name, chat_id):
    return safe_call(lambda: assistant.send_message("open " + name, chat_id))


def startup_sound():
    try:
        from playsound import playsound
        playsound(str(FRONT / "assets" / "audio" / "start_sound.mp3"))
    except Exception:
        logging.getLogger(__name__).warning("Startup sound unavailable", exc_info=True)


if __name__ == "__main__":
    threading.Thread(target=startup_sound, name="zara-startup-sound", daemon=True).start()
    try:
        eel.start("index.html", mode="edge", host="localhost", block=True)
    finally:
        assistant.close()


