import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ai.client import AIUnavailable, LocalAIClient
from core.assistant import Assistant
from database.db import Database
from database.repositories import Repository
from voice.wakeword import OpenWakeWordProvider
from voice.speech import SpeechService


class Response:
    def __init__(self, body):
        self.body = body
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.body


class Phase2Tests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.repo = Repository(Database(Path(self.folder.name) / "zara.db"))

    def tearDown(self):
        self.folder.cleanup()

    def wait(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("Worker timed out")
            time.sleep(.01)

    def test_ai_request_configuration_and_failures(self):
        client = LocalAIClient("http://127.0.0.1:8081/v1", "my-model", .2, 9, "Custom prompt")
        self.assertEqual(client.endpoint, "http://127.0.0.1:8081/v1/chat/completions")
        with patch("ai.client.urllib.request.build_opener") as builder:
            builder.return_value.open.return_value = Response(b'{"choices":[{"message":{"content":"Hello"}}]}')
            self.assertEqual(client.generate_response([{"role": "user", "content": "Hi"}]), "Hello")
            request = builder.return_value.open.call_args.args[0]
            payload = json.loads(request.data)
            self.assertEqual(request.full_url, client.endpoint)
            self.assertEqual(payload["model"], "my-model")
            self.assertEqual(payload["messages"], [{"role": "system", "content": "Custom prompt"},
                                                  {"role": "user", "content": "Hi"}])
            self.assertEqual(builder.return_value.open.call_args.kwargs["timeout"], 9)
            client.test_connection()
            self.assertEqual(json.loads(builder.return_value.open.call_args.args[0].data)["max_tokens"], 8)
        for failure in (TimeoutError("slow"), OSError("offline")):
            with self.subTest(failure=failure), patch("ai.client.urllib.request.build_opener") as builder:
                builder.return_value.open.side_effect = failure
                with self.assertRaises(AIUnavailable):
                    client.generate_response([])
        with patch("ai.client.urllib.request.build_opener") as builder:
            builder.return_value.open.return_value = Response(b'{"choices": []}')
            with self.assertRaises(AIUnavailable):
                client.generate_response([])

    def test_phase2_settings_persist_and_validate(self):
        self.repo.update_settings({"ai_timeout": 18, "ai_system_prompt": "Custom", "speak_ai_responses": False,
                                   "wake_word_sensitivity": .65, "activation_response": "yes"})
        reopened = Repository(Database(Path(self.folder.name) / "zara.db"))
        settings = reopened.settings()
        self.assertEqual(settings["ai_timeout"], 18)
        self.assertEqual(settings["ai_system_prompt"], "Custom")
        self.assertFalse(settings["speak_ai_responses"])
        self.assertEqual(settings["wake_word_sensitivity"], .65)
        self.assertEqual(settings["activation_response"], "yes")
        for changes in ({"wake_word_sensitivity": 0}, {"ai_timeout": 0},
                        {"wake_word_provider": "remote"}, {"ai_endpoint": "https://example.com"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                reopened.update_settings(changes)

    def test_long_ai_answer_only_shortened_for_speech(self):
        answer = "First sentence. " + "Additional detail. " * 60
        excerpt = Assistant._spoken_excerpt(answer, 100)
        self.assertLess(len(excerpt), len(answer))
        self.assertIn("read the rest on screen", excerpt)
        self.assertEqual(Assistant._spoken_excerpt("Short answer.", 100), "Short answer.")

    def test_speech_completion_and_failure_reporting(self):
        states, errors = [], []
        engine = Mock()
        engine.runAndWait.side_effect = [None, RuntimeError("SAPI unavailable")]
        speech = SpeechService(lambda state, _: states.append(state), self.repo.settings, errors.append)
        try:
            with patch("pyttsx3.init", return_value=engine), patch("voice.speech.LOG.exception"):
                self.assertTrue(speech.speak_and_wait("Yes?"))
                self.assertFalse(speech.speak_and_wait("Listening."))
            self.assertIn("SPEAKING", states)
            self.assertEqual(len(errors), 1)
        finally:
            speech.close()

    def test_ai_context_and_command_first(self):
        self.repo.update_settings({"voice_enabled": False, "ai_max_context": 2,
                                   "ai_system_prompt": "Custom", "ai_timeout": 12})
        chat = self.repo.create_chat()["id"]
        events = []
        assistant = Assistant(self.repo, lambda name, data: events.append((name, data)))
        calls = []
        try:
            with patch("core.assistant.LocalAIClient") as provider, \
                 patch("automation.websites.webbrowser.open", return_value=True):
                provider.return_value.generate_response.side_effect = lambda messages: calls.append(messages) or "AI answer"
                self.assertTrue(assistant.send_message("What is Flask?", chat)["accepted"])
                self.wait(lambda: len(self.repo.messages(chat)) == 2 and not assistant._busy)
                self.assertTrue(assistant.send_message("Give an example", chat)["accepted"])
                self.wait(lambda: len(self.repo.messages(chat)) == 4 and not assistant._busy)
                self.assertEqual([item["content"] for item in calls[-1]], ["AI answer", "Give an example"])
                self.assertEqual(provider.call_args.args[3:], (12, "Custom"))
                self.assertTrue(assistant.send_message("open google", chat)["accepted"])
                self.wait(lambda: len(self.repo.messages(chat)) == 6 and not assistant._busy)
                self.assertEqual(len(calls), 2)
        finally:
            assistant.close()

    def test_wake_provider_handoff_pause_resume_and_shutdown(self):
        model_path = Path(self.folder.name) / "hey_zara.onnx"
        model_path.write_bytes(b"mock")
        detections = []
        statuses = []
        streams = []
        class Stream:
            closed = False
            def read(self, *_args, **_kwargs):
                time.sleep(.005)
                return b"\0" * 2560
            def stop_stream(self): pass
            def close(self): self.closed = True
        class Audio:
            def open(self, **_kwargs):
                stream = Stream()
                streams.append(stream)
                return stream
            def terminate(self): pass
        class Model:
            wake = False
            def __init__(self, **_kwargs): pass
            def reset(self): pass
            def predict(self, _frame): return {"hey_zara": .9 if self.wake else .1}
        fake_openwakeword = types.ModuleType("openwakeword")
        fake_openwakeword.__file__ = str(Path(self.folder.name) / "__init__.py")
        resources = Path(self.folder.name) / "resources" / "models"
        resources.mkdir(parents=True)
        for name in ("melspectrogram.onnx", "embedding_model.onnx"):
            (resources / name).write_bytes(b"mock")
        fake_model = types.ModuleType("openwakeword.model")
        fake_model.Model = Model
        fake_audio = types.ModuleType("pyaudio")
        fake_audio.PyAudio = Audio
        fake_audio.paInt16 = 8
        fake_numpy = types.ModuleType("numpy")
        fake_numpy.int16 = "int16"
        fake_numpy.frombuffer = lambda frame, dtype: frame
        modules = {"openwakeword": fake_openwakeword, "openwakeword.model": fake_model,
                   "pyaudio": fake_audio, "numpy": fake_numpy}
        def on_wake():
            detections.append(all(stream.closed for stream in streams))
        provider = OpenWakeWordProvider(on_wake, lambda status, _: statuses.append(status),
                                        lambda: {"wake_word_model_path": str(model_path),
                                                 "wake_word_provider": "openwakeword", "wake_word_sensitivity": .5})
        with patch.dict(sys.modules, modules):
            self.assertTrue(provider.start())
            self.wait(provider.is_running)
            self.assertTrue(provider.pause())
            self.assertFalse(provider.is_running())
            self.assertTrue(streams[0].closed)
            Model.wake = True
            self.assertTrue(provider.resume())
            self.wait(lambda: bool(detections))
            self.assertEqual(detections, [True])
            self.assertIn("detected", statuses)
            self.assertTrue(provider.stop())

    def test_manual_mic_releases_wake_first(self):
        self.repo.update_settings({"voice_enabled": False})
        chat = self.repo.create_chat()["id"]
        assistant = Assistant(self.repo, lambda *_: None)
        order = []
        try:
            with patch.object(assistant.wakeword, "pause", side_effect=lambda: order.append("pause") or True), \
                 patch("core.assistant.listen", side_effect=lambda *_: order.append("listen") or None):
                self.assertTrue(assistant.start_listening(chat)["accepted"])
                self.wait(lambda: len(order) == 2)
                self.assertEqual(order, ["pause", "listen"])
        finally:
            assistant.close()

    def test_missing_model_preserves_typed_commands_and_tts_pauses_wake(self):
        self.repo.update_settings({"voice_enabled": False})
        chat = self.repo.create_chat()["id"]
        events = []
        assistant = Assistant(self.repo, lambda name, data: events.append((name, data)))
        try:
            assistant.activate()
            assistant.update_settings({"wake_word_enabled": True,
                                       "wake_word_model_path": str(Path(self.folder.name) / "missing.onnx")})
            self.wait(lambda: any(name == "wake_status" and data["status"] == "error"
                                  for name, data in events))
            with patch("automation.websites.webbrowser.open", return_value=True):
                self.assertTrue(assistant.send_message("open google", chat)["accepted"])
                self.wait(lambda: len(self.repo.messages(chat)) == 2 and not assistant._busy)
            self.repo.update_settings({"voice_enabled": True})
            with patch.object(assistant.wakeword, "pause", return_value=True) as pause, \
                 patch.object(assistant.speech, "speak", return_value=True) as speak:
                assistant._queue_speech("Done")
                pause.assert_called_once()
                speak.assert_called_once_with("Done")
        finally:
            assistant.close()


if __name__ == "__main__":
    unittest.main()
