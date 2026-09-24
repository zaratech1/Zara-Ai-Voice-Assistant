import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from ai.client import AIUnavailable, LocalAIClient
from core.command_router import CommandRouter
from core.assistant import Assistant
from core.intent_parser import normalize, parse
from database.db import Database
from database.repositories import Repository


class ZaraTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "zara.db"
        self.repo = Repository(Database(self.path))

    def tearDown(self):
        self.folder.cleanup()

    def test_chat_and_settings_persist(self):
        chat = self.repo.create_chat()
        other = self.repo.create_chat()
        self.repo.add_message(other["id"], "user", "Keep this")
        self.repo.add_message(chat["id"], "user", "Explain decorators")
        self.repo.add_message(chat["id"], "assistant", "They wrap functions.")
        self.assertEqual(self.repo.get_chat(chat["id"])["title"], "Explain decorators")
        self.repo.update_settings({"voice_enabled": False, "speech_rate": 190})
        second = Repository(Database(self.path))
        self.assertEqual(len(second.messages(chat["id"])), 2)
        self.assertFalse(second.settings()["voice_enabled"])
        self.assertEqual(second.settings()["speech_rate"], 190)
        second.rename_chat(chat["id"], "Python notes")
        self.assertEqual(second.get_chat(chat["id"])["title"], "Python notes")
        self.assertTrue(second.delete_chat(chat["id"]))
        self.assertIsNone(second.get_chat(chat["id"]))
        self.assertEqual(second.messages(other["id"])[0]["content"], "Keep this")

    def test_registry_resolution_and_disabled_entry(self):
        self.assertEqual(self.repo.resolve("applications", "calc")["name"], "Calculator")
        self.assertEqual(self.repo.resolve("websites", "canva")["name"], "Canva")
        self.assertIsNone(self.repo.resolve("applications", "unknown"))
        self.assertFalse(CommandRouter(self.repo).route("open unknown")["success"])
        custom = self.repo.save_mapping("websites", {"name": "Example", "aliases": "docs, sample", "url": "https://example.org/", "enabled": False})
        self.assertEqual(self.repo.resolve("websites", "docs")["id"], custom["id"])
        with self.assertRaises(ValueError):
            self.repo.save_mapping("websites", {"name": "Another", "aliases": "docs", "url": "https://another.example/"})
        with patch("automation.websites.webbrowser.open") as opener:
            outcome = CommandRouter(self.repo).route("open docs")
        self.assertFalse(outcome["success"])
        opener.assert_not_called()

    def test_old_and_new_command_routing(self):
        cases = {
            "open calculator": "open_app", "open canva": "open_website", "open google": "open_website",
            "search python on google": "google_search", "open python tutorial on google": "google_search",
            "open india history on wikipedia": "wikipedia_search", "open wikipedia": "open_website",
            "open youtube": "open_website", "open example.org": "open_website",
            "play music on youtube": "youtube_play", "search youtube for django": "youtube_search",
        }
        with patch("automation.websites.webbrowser.open", return_value=True), \
             patch("core.command_router.play", return_value={"success": True, "action": "youtube_play", "target": "music", "message": "OK"}), \
             patch("core.command_router.open_application", return_value={"success": True, "action": "open_app", "target": "Calculator", "message": "OK"}):
            router = CommandRouter(self.repo)
            for command, action in cases.items():
                with self.subTest(command=command):
                    self.assertEqual(router.route(command)["action"], action)

    def test_normalization_and_chat_fallback(self):
        self.assertEqual(normalize("  Hey ZARA,   OPEN   Calculator! "), "open calculator")
        self.assertEqual(parse("Who is Nikola Tesla?"), ("chat", "who is nikola tesla"))
        self.assertEqual(parse("send whatsapp message to Rahul saying I'll be late")[0], "whatsapp")
        self.assertEqual(parse("send WhatsApp message to Rahul saying I'll Reach at 8 PM!")[1][1],
                         "I'll Reach at 8 PM!")

    def test_local_ai_contract(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return json.dumps({"choices": [{"message": {"content": "Hello"}}]}).encode()
        with patch("ai.client.urllib.request.build_opener") as builder:
            builder.return_value.open.return_value = Response()
            self.assertEqual(LocalAIClient("http://127.0.0.1:8080/v1/chat/completions").generate_response(
                [{"role": "user", "content": "Hi"}]), "Hello")
            self.assertEqual(builder.return_value.open.call_args.kwargs["timeout"], 35)
        with self.assertRaises(ValueError):
            LocalAIClient("https://example.com/v1/chat/completions")
        with patch("ai.client.urllib.request.build_opener") as builder:
            builder.return_value.open.side_effect = OSError("offline")
            with self.assertRaises(AIUnavailable):
                LocalAIClient("http://localhost:8080/v1/chat/completions").generate_response([])

    def test_assistant_events_and_whatsapp_confirmation(self):
        self.repo.update_settings({"voice_enabled": False})
        chat = self.repo.create_chat()
        self.repo.save_contact("Rahul", "+15551234567")
        with self.assertRaises(ValueError):
            self.repo.save_contact("Another", "+15557654321", "Rahul")
        events = []
        assistant = Assistant(self.repo, lambda name, payload: events.append((name, payload)))
        try:
            with patch("automation.websites.webbrowser.open", return_value=True):
                self.assertTrue(assistant.send_message("open google", chat["id"])["accepted"])
                self._wait_for(lambda: len(self.repo.messages(chat["id"])) == 2)
            self.assertIn("command_completed", [name for name, _ in events])
            self._wait_for(lambda: assistant.state == "IDLE")
            self.assertTrue(assistant.send_message(
                "send whatsapp message to Rahul saying I'll Reach at 8 PM!", chat["id"])["accepted"])
            self._wait_for(lambda: any(name == "whatsapp_confirmation" for name, _ in events))
            preview = next(payload for name, payload in events if name == "whatsapp_confirmation")
            self.assertEqual(preview["message"], "I'll Reach at 8 PM!")
            self.assertTrue(assistant.confirm_whatsapp(preview["token"], False)["accepted"])
            with self.repo.database.connect() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM automation_history WHERE action_type='whatsapp'").fetchone()[0], 0)
        finally:
            assistant.close()

    def _wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("Background worker did not finish")
            time.sleep(.01)


if __name__ == "__main__":
    unittest.main()
