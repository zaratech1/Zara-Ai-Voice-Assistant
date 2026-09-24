"""Coordinates Eel events, persistence, routing, voice, and local AI."""
import logging
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from ai.client import AIUnavailable, LocalAIClient
from automation import result
from automation.whatsapp import send as send_whatsapp
from core.command_router import CommandRouter
from core.intent_parser import parse
from voice.recognition import RecognitionFailure, listen
from voice.speech import SpeechService
from voice.wakeword import WakeWordService

LOG = logging.getLogger(__name__)


class Assistant:
    def __init__(self, repository, emit):
        self.repository = repository
        self.emit = emit
        self.router = CommandRouter(repository)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="zara-work")
        self._lock = threading.RLock()
        self._busy = False
        self._listening = False
        self._speaking = False
        self._listen_stop = threading.Event()
        self._pending = {}
        self._closed = False
        self._ui_ready = False
        self.state = "IDLE"
        self.active_chat = None
        self.speech = SpeechService(self._speech_state, self.repository.settings,
                                    lambda message: self.emit("error", {"message": message}))
        self.wakeword = WakeWordService(self._on_wake, self._wake_status, self.repository.settings)
        self._wake_triggered = False

    def activate(self):
        self._ui_ready = True
        self._restart_wakeword()

    def set_state(self, state, label):
        with self._lock:
            if self._closed:
                return
            if state == "IDLE" and (self._busy or self._listening or self._speaking):
                return
            self.state = state
        if state == "SPEAKING":
            self.wakeword.pause()
        self.emit("state", {"state": state, "label": label})
        if state == "IDLE":
            self._restart_wakeword()

    def _speech_state(self, state, label):
        with self._lock:
            self._speaking = state == "SPEAKING"
        self.set_state(state, label)

    def _wake_status(self, status, message):
        self.emit("wake_status", {"status": status, "message": message})
        if status == "active":
            with self._lock:
                idle = not (self._busy or self._listening or self._speaking)
            if idle:
                self.set_state("WAKE_LISTENING", "Waiting for Hey Zara...")
        elif status == "error":
            self.emit("error", {"message": message})
            self.set_state("ERROR", "Wake word unavailable")
            self.set_state("IDLE", "Ready")

    def _queue_speech(self, text):
        if not self.repository.settings()["voice_enabled"]:
            return
        with self._lock:
            self._speaking = True
        if not self.wakeword.pause():
            with self._lock:
                self._speaking = False
            self.emit("error", {"message": "Speech paused because the wake microphone is still busy."})
            return
        if not self.speech.speak(text):
            with self._lock:
                self._speaking = False
            self._restart_wakeword()

    @staticmethod
    def _spoken_excerpt(text, limit):
        if len(text) <= limit:
            return text
        sentences = re.split(r"(?<=[.!?])\s+", text)
        spoken = ""
        for sentence in sentences:
            if len(spoken) + len(sentence) + 1 > limit:
                break
            spoken = (spoken + " " + sentence).strip()
        return (spoken or text[:limit].rsplit(" ", 1)[0]) + " You can read the rest on screen."

    def _reserve(self):
        with self._lock:
            if self._closed or self._busy or self._speaking:
                return False
            self._busy = True
            return True

    def send_message(self, text, chat_id, source="text"):
        if not isinstance(text, str) or not text.strip() or len(text) > 8000:
            return {"accepted": False, "message": "Enter a message up to 8,000 characters."}
        if not self.repository.get_chat(chat_id):
            return {"accepted": False, "message": "Chat not found."}
        if not self._reserve():
            return {"accepted": False, "message": "ZARA is busy. Please wait a moment."}
        self.executor.submit(self._process, text.strip(), chat_id, source)
        return {"accepted": True}

    def _process(self, text, chat_id, source):
        try:
            kind = "chat" if parse(text)[0] == "chat" else "command"
            user = self.repository.add_message(chat_id, "user", text, kind)
            self.emit("message", user)
            self.emit("history_updated", {"chats": self.repository.chats()})
            self.set_state("PROCESSING" if kind == "chat" else "EXECUTING",
                           "Thinking..." if kind == "chat" else "Running command...")
            parsed = self.router.route(text)
            if parsed is None:
                settings = self.repository.settings()
                if not settings["ai_enabled"]:
                    reply = "AI chat is disabled in Settings. Commands are still available."
                    message_type = "error"
                else:
                    context = [{"role": row["role"], "content": row["content"]}
                               for row in self.repository.messages(chat_id, settings["ai_max_context"] + 1)
                               if row["message_type"] == "chat"]
                    try:
                        reply = LocalAIClient(settings["ai_endpoint"], settings["ai_model"],
                                              settings["ai_temperature"], settings["ai_timeout"],
                                              settings["ai_system_prompt"]).generate_response(context[-settings["ai_max_context"]:])
                        message_type = "chat"
                        self.emit("ai_status", {"status": "connected"})
                    except (AIUnavailable, ValueError):
                        reply = "Local AI is unavailable. Start your configured AI server and try again."
                        message_type = "error"
                        self.emit("ai_status", {"status": "offline"})
                response = self.repository.add_message(chat_id, "assistant", reply, message_type)
                self.emit("message", response)
                if message_type == "chat" and settings["speak_ai_responses"]:
                    self._queue_speech(self._spoken_excerpt(reply, settings["ai_speech_max_chars"]))
            elif parsed["action"] == "whatsapp_confirmation" and parsed["success"]:
                token = uuid.uuid4().hex
                with self._lock:
                    now = time.monotonic()
                    self._pending = {key: item for key, item in self._pending.items() if item["expires"] > now}
                    self._pending[token] = {"chat_id": chat_id, "contact_id": parsed["contact_id"],
                                            "message": parsed["message"], "command": text, "expires": now + 180}
                self.emit("whatsapp_confirmation", {"token": token, "to": parsed["target"],
                                                    "message": parsed["message"]})
            else:
                self.repository.record_automation(text, parsed)
                response = self.repository.add_message(chat_id, "assistant", parsed["message"],
                                                       "automation" if parsed["success"] else "error")
                self.emit("message", response)
                self.emit("command_completed" if parsed["success"] else "command_failed", parsed)
                if parsed["success"]:
                    self._queue_speech(parsed["message"])
        except Exception:
            LOG.exception("Request failed")
            self.emit("error", {"message": "Sorry, that request failed. Please try again."})
        finally:
            with self._lock:
                self._busy = False
            self.set_state("IDLE", "Ready")
            self._restart_wakeword()

    def confirm_whatsapp(self, token, approved):
        with self._lock:
            pending = self._pending.pop(token, None)
        if not pending or pending["expires"] < time.monotonic():
            return {"accepted": False, "message": "The confirmation expired. Please request it again."}
        if not self.repository.get_chat(pending["chat_id"]):
            return {"accepted": False, "message": "That conversation was deleted. Please request the message again."}
        if not approved:
            self.emit("status", {"message": "WhatsApp message cancelled."})
            return {"accepted": True}
        if not self._reserve():
            with self._lock:
                self._pending[token] = pending
            return {"accepted": False, "message": "ZARA is busy. Try again in a moment."}
        self.executor.submit(self._send_whatsapp, pending)
        return {"accepted": True}

    def _send_whatsapp(self, pending):
        try:
            self.set_state("EXECUTING", "Sending message...")
            # Fetch only the confirmed contact; never accept a phone number from the frontend.
            with self.repository.database.connect() as db:
                row = db.execute("SELECT * FROM contacts WHERE id=?", (pending["contact_id"],)).fetchone()
                contact = dict(row) if row else None
            outcome = send_whatsapp(contact, pending["message"]) if contact else result(
                False, "whatsapp", "contact", "The contact no longer exists.")
            self.repository.record_automation(pending["command"], outcome)
            response = self.repository.add_message(pending["chat_id"], "assistant", outcome["message"],
                                                   "automation" if outcome["success"] else "error")
            self.emit("message", response)
            self.emit("command_completed" if outcome["success"] else "command_failed", outcome)
        except Exception:
            LOG.exception("WhatsApp request failed")
            self.emit("error", {"message": "I couldn't send the WhatsApp message."})
        finally:
            with self._lock:
                self._busy = False
            self.set_state("IDLE", "Ready")
            self._restart_wakeword()

    def start_listening(self, chat_id):
        if not self.repository.get_chat(chat_id):
            return {"accepted": False, "message": "Chat not found."}
        with self._lock:
            if self._closed or self._listening or self._busy or self._speaking:
                return {"accepted": False, "message": "ZARA is busy. Please wait a moment."}
            self._listening = True
            self._listen_stop.clear()
        self.executor.submit(self._capture, chat_id)
        return {"accepted": True}

    def _capture(self, chat_id):
        try:
            if not self.wakeword.pause():
                raise RecognitionFailure("The microphone is still busy. Please try again.")
            self.speech.stop_speaking()
            with self._lock:
                triggered = self._wake_triggered
                self._wake_triggered = False
            if triggered:
                settings = self.repository.settings()
                if settings["activation_sound"]:
                    try:
                        import winsound
                        winsound.MessageBeep(winsound.MB_OK)
                    except Exception:
                        LOG.warning("Activation sound failed", exc_info=True)
                response = {"yes": "Yes?", "listening": "Listening."}.get(settings["activation_response"])
                if response and not self.speech.speak_and_wait(response, timeout=15):
                    raise RecognitionFailure("Activation response did not finish. Please use the mic button.")
            self.set_state("LISTENING", "Listening...")
            self.emit("listening_started", {})
            text = listen(self._listen_stop)
            if text and not self._listen_stop.is_set():
                self.emit("recognized", {"text": text})
        except RecognitionFailure as error:
            if not self._listen_stop.is_set():
                self.emit("error", {"message": str(error)})
            text = None
        except Exception:
            LOG.exception("Microphone capture failed")
            self.emit("error", {"message": "Microphone unavailable. You can continue using typed commands."})
            text = None
        finally:
            with self._lock:
                self._listening = False
            self.emit("listening_stopped", {})
        if text and not self._listen_stop.is_set():
            if not self.send_message(text, chat_id, "voice")["accepted"]:
                self.set_state("IDLE", "Ready")
        else:
            self.set_state("IDLE", "Ready")
            self._restart_wakeword()

    def stop_listening(self):
        self._listen_stop.set()
        return {"accepted": True}

    def _on_wake(self):
        with self._lock:
            if self._closed or self._busy or self._listening or self._speaking:
                self._restart_wakeword()
                return
            self._wake_triggered = True
        self.set_state("WAKE_DETECTED", "Hey Zara detected")
        self.emit("wake_detected", {})
        chats = self.repository.chats()
        chat_id = self.active_chat if self.repository.get_chat(self.active_chat) else (
            chats[0]["id"] if chats else self.repository.create_chat()["id"])
        accepted = self.start_listening(chat_id)
        if not accepted["accepted"]:
            with self._lock:
                self._wake_triggered = False
            self._restart_wakeword()

    def set_active_chat(self, chat_id):
        if not self.repository.get_chat(chat_id):
            raise ValueError("Chat not found.")
        with self._lock:
            self.active_chat = chat_id
        return True

    def _restart_wakeword(self):
        if self._ui_ready and self.repository.settings()["wake_word_enabled"] and not self._closed:
            with self._lock:
                idle = not self._busy and not self._listening and not self._speaking
            if idle:
                self.wakeword.resume()

    def update_settings(self, changes):
        previous = self.repository.settings()
        settings = self.repository.update_settings(changes)
        if any(previous[key] != settings[key] for key in ("wake_word_enabled", "wake_word_model_path", "wake_word_provider", "wake_word_sensitivity")):
            self.wakeword.stop()
            self.wakeword.clear_failure()
        if settings["wake_word_enabled"]:
            self._restart_wakeword()
        elif self.wakeword.is_running():
            self.wakeword.stop()
        return settings

    def test_ai(self):
        def worker():
            try:
                settings = self.repository.settings()
                LocalAIClient(settings["ai_endpoint"], settings["ai_model"],
                              settings["ai_temperature"], settings["ai_timeout"],
                              settings["ai_system_prompt"]).test_connection()
                self.emit("ai_test", {"success": True, "message": "Local AI connection is working."})
            except Exception:
                self.emit("ai_test", {"success": False, "message": "Local AI is unavailable. Check the server, endpoint, and model."})
        self.executor.submit(worker)
        return {"accepted": True}

    def close(self):
        with self._lock:
            self._closed = True
        self._listen_stop.set()
        self.wakeword.stop()
        self.speech.close()
        self.executor.shutdown(wait=False, cancel_futures=True)
