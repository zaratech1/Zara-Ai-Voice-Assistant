"""Paths and safe defaults for the desktop application."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONT = ROOT / "front"
DATA = ROOT / "data"
DATABASE = DATA / "zara.db"
LOG_FILE = DATA / "zara.log"

DEFAULT_SETTINGS = {
    "voice_enabled": True,
    "speech_rate": 174,
    "speech_volume": 1.0,
    "selected_voice": "",
    "recognition_provider": "google",
    "wake_word_enabled": False,
    "wake_word_provider": "openwakeword",
    "wake_word_model_path": "",
    "wake_word_sensitivity": 0.5,
    "activation_sound": False,
    "activation_response": "none",
    "ai_enabled": True,
    "ai_provider": "llama.cpp",
    "ai_endpoint": "http://127.0.0.1:8080/v1",
    "ai_model": "",
    "ai_temperature": 0.7,
    "ai_max_context": 12,
    "ai_timeout": 35,
    "ai_system_prompt": "",
    "speak_ai_responses": True,
    "ai_speech_max_chars": 500,
    "theme": "dark",
    "sidebar_collapsed": False,
    "launch_behavior": "last_chat",
}
