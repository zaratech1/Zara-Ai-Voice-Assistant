"""Local wake-word provider. Releases microphone before command recognition."""
import logging
import threading
from pathlib import Path

LOG = logging.getLogger(__name__)
FRAME_SAMPLES = 1280  # 80 ms of 16 kHz PCM


class WakeWordProvider:
    def start(self): raise NotImplementedError
    def pause(self): raise NotImplementedError
    def resume(self): raise NotImplementedError
    def stop(self): raise NotImplementedError
    def is_running(self): raise NotImplementedError


class OpenWakeWordProvider(WakeWordProvider):
    def __init__(self, on_wake, on_status, settings_callback):
        self.on_wake = on_wake
        self.on_status = on_status
        self.settings_callback = settings_callback
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._model = None
        self._model_path = None
        self._failed = False
        self._status = "off"

    def _publish(self, status, message=""):
        with self._lock:
            self._status = status
        self.on_status(status, message)

    def clear_failure(self):
        with self._lock:
            self._failed = False

    def is_running(self):
        with self._lock:
            return self._status == "active" and self._thread is not None and self._thread.is_alive()

    def start(self):
        with self._lock:
            if self._failed or (self._thread and self._thread.is_alive()):
                return False
            self._stop = threading.Event()
            self._publish("starting", "Loading local wake-word model...")
            self._thread = threading.Thread(target=self._run, args=(self._stop,), name="zara-wakeword", daemon=True)
            self._thread.start()
            return True

    def resume(self):
        return self.start()

    def pause(self):
        with self._lock:
            self._stop.set()
            thread = self._thread
            was_active = self._status in ("starting", "active", "detected")
        if thread and thread is not threading.current_thread():
            thread.join(timeout=15)
            if thread.is_alive():
                return False
        if was_active:
            self._publish("paused")
        return True

    def stop(self):
        released = self.pause()
        if released:
            self._publish("off")
        return released

    def _run(self, stop):
        stream = None
        audio = None
        detected = False
        try:
            settings = self.settings_callback()
            model_path = Path(settings["wake_word_model_path"]).expanduser()
            if not settings["wake_word_model_path"] or not model_path.is_file() or model_path.suffix.lower() != ".onnx":
                raise ValueError("Select a trained Hey Zara .onnx model in Wake word settings.")
            if settings["wake_word_provider"] != "openwakeword":
                raise ValueError("Unsupported wake-word provider.")
            import numpy as np
            import pyaudio
            import openwakeword
            from openwakeword.model import Model

            resources = Path(openwakeword.__file__).parent / "resources" / "models"
            if not all((resources / name).is_file() for name in ("melspectrogram.onnx", "embedding_model.onnx")):
                raise ValueError("openWakeWord feature models are missing. Run: python -m voice.setup_wakeword_assets")

            if self._model is None or self._model_path != str(model_path):
                self._model = Model(wakeword_models=[str(model_path)], inference_framework="onnx")
                self._model_path = str(model_path)
            else:
                self._model.reset()
            if stop.is_set():
                return
            audio = pyaudio.PyAudio()
            stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True,
                                frames_per_buffer=FRAME_SAMPLES)
            self._publish("active")
            threshold = settings["wake_word_sensitivity"]
            while not stop.is_set():
                frame = stream.read(FRAME_SAMPLES, exception_on_overflow=False)
                scores = self._model.predict(np.frombuffer(frame, dtype=np.int16))
                if scores and max(scores.values()) >= threshold:
                    detected = True
                    stop.set()
        except (ImportError, ValueError) as error:
            LOG.warning("Wake-word unavailable: %s", error)
            with self._lock:
                self._failed = True
            self._publish("error", str(error))
        except Exception:
            LOG.exception("Wake-word microphone or model failure")
            with self._lock:
                self._failed = True
            self._publish("error", "Wake-word detection unavailable. Check the microphone and model.")
        finally:
            if stream is not None:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    LOG.exception("Could not close wake-word microphone stream")
            if audio is not None:
                try:
                    audio.terminate()
                except Exception:
                    LOG.exception("Could not terminate wake-word audio device")
            if detected:
                self._publish("detected")
                self.on_wake()
            elif self._status not in ("error", "off", "paused"):
                self._publish("paused")


WakeWordService = OpenWakeWordProvider
