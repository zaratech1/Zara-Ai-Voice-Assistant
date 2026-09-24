"""Serial speech worker; pyttsx3 stays on its owning thread."""
import logging
import queue
import threading

LOG = logging.getLogger(__name__)


class SpeechService:
    def __init__(self, state_callback, settings_callback, error_callback=None):
        self._state_callback = state_callback
        self._settings_callback = settings_callback
        self._error_callback = error_callback
        self._queue = queue.Queue(maxsize=1)
        self._closed = threading.Event()
        self._active = threading.Event()
        self._engine = None
        self._thread = threading.Thread(target=self._run, name="zara-speech", daemon=True)
        self._thread.start()

    def speak(self, text, force=False, completion=None, result=None):
        if (not force and not self._settings_callback()["voice_enabled"]) or self._closed.is_set():
            return False
        try:
            self._queue.put_nowait((text, completion, result))
            return True
        except queue.Full:
            LOG.info("Speech already queued; skipping overlapping response")
            return False

    def speak_and_wait(self, text, timeout=8):
        completed = threading.Event()
        result = {"success": False}
        if not self.speak(text, force=True, completion=completed, result=result):
            return False
        return completed.wait(timeout) and result["success"]

    def _run(self):
        engine = None
        com = None
        try:
            import pythoncom
            pythoncom.CoInitialize()
            com = pythoncom
        except Exception:
            LOG.warning("COM initialization unavailable for speech", exc_info=True)
        while not self._closed.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if item is None:
                break
            text, completion, result = item
            try:
                import pyttsx3
                if engine is None:
                    engine = pyttsx3.init("sapi5")
                    self._engine = engine
                settings = self._settings_callback()
                engine.setProperty("rate", settings["speech_rate"])
                engine.setProperty("volume", settings["speech_volume"])
                if settings["selected_voice"]:
                    engine.setProperty("voice", settings["selected_voice"])
                self._active.set()
                self._state_callback("SPEAKING", "Speaking...")
                engine.say(text)
                engine.runAndWait()
                if result is not None:
                    result["success"] = True
            except Exception:
                LOG.exception("Text-to-speech failed")
                if self._error_callback is not None:
                    self._error_callback("Speech output is unavailable. Check your Windows voice settings.")
                engine = None
                self._engine = None
            finally:
                self._active.clear()
                self._state_callback("IDLE", "Ready")
                self._queue.task_done()
                if completion is not None:
                    completion.set()
        if com is not None:
            com.CoUninitialize()

    def voices(self):
        try:
            import pyttsx3
            engine = pyttsx3.init("sapi5")
            return [{"id": voice.id, "name": voice.name} for voice in engine.getProperty("voices")]
        except Exception:
            LOG.exception("Could not enumerate voices")
            return []

    def stop_speaking(self):
        if self._active.is_set() and self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                LOG.warning("Unable to interrupt current speech", exc_info=True)
        while True:
            try:
                item = self._queue.get_nowait()
                self._queue.task_done()
                if item is not None and item[1] is not None:
                    item[1].set()
            except queue.Empty:
                break

    def close(self):
        self._closed.set()
        self.stop_speaking()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self._thread.join(timeout=2)
