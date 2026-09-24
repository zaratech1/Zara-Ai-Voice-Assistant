"""Small persistence API; no SQLite connections survive a call."""
import json
from pathlib import Path
from urllib.parse import urlparse

from config import DEFAULT_SETTINGS


def _dict(row):
    return dict(row) if row else None


def _aliases(text):
    return [item.strip().casefold() for item in text.split(",") if item.strip()]


class Repository:
    def __init__(self, database):
        self.database = database

    def settings(self):
        with self.database.connect() as db:
            return {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT key,value FROM settings")}

    def update_settings(self, changes):
        allowed = set(DEFAULT_SETTINGS)
        with self.database.connect() as db:
            for key, value in changes.items():
                if key not in allowed:
                    continue
                if key in ("ai_endpoint", "ai_model", "selected_voice", "theme", "ai_provider", "recognition_provider", "launch_behavior", "wake_word_provider", "wake_word_model_path", "activation_response", "ai_system_prompt"):
                    if not isinstance(value, str) or len(value) > (4000 if key == "ai_system_prompt" else 500):
                        raise ValueError(f"Invalid {key}.")
                elif isinstance(DEFAULT_SETTINGS[key], bool):
                    if not isinstance(value, bool):
                        raise ValueError(f"Invalid {key}.")
                elif isinstance(DEFAULT_SETTINGS[key], (int, float)):
                    if not isinstance(value, (int, float)) or isinstance(value, bool):
                        raise ValueError(f"Invalid {key}.")
                if key == "ai_endpoint":
                    parsed = urlparse(value)
                    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
                            or parsed.username or parsed.password or parsed.query or parsed.fragment):
                        raise ValueError("The AI endpoint must be a local HTTP address.")
                if key == "speech_rate" and not 80 <= value <= 300:
                    raise ValueError("Speech rate must be 80–300.")
                if key in ("speech_volume", "ai_temperature") and not 0 <= value <= 1:
                    raise ValueError(f"Invalid {key}.")
                if key == "wake_word_sensitivity" and not 0.1 <= value <= 0.95:
                    raise ValueError("Wake sensitivity must be 0.1–0.95.")
                if key == "ai_max_context" and not 2 <= value <= 40:
                    raise ValueError("Context must be 2–40 messages.")
                if key == "ai_timeout" and not 5 <= value <= 120:
                    raise ValueError("AI timeout must be 5–120 seconds.")
                if key == "ai_speech_max_chars" and not 100 <= value <= 2000:
                    raise ValueError("AI speech limit must be 100–2000 characters.")
                if key == "wake_word_provider" and value != "openwakeword":
                    raise ValueError("Only openWakeWord is supported currently.")
                if key == "activation_response" and value not in ("none", "yes", "listening"):
                    raise ValueError("Invalid activation response.")
                if key == "recognition_provider" and value != "google":
                    raise ValueError("Only Google recognition is installed.")
                if key == "ai_provider" and value != "llama.cpp":
                    raise ValueError("Only llama.cpp is supported currently.")
                if key == "launch_behavior" and value not in ("last_chat", "new_chat"):
                    raise ValueError("Invalid launch behavior.")
                if key == "theme" and value not in ("dark", "light"):
                    raise ValueError("Invalid theme.")
                db.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                           (key, json.dumps(value)))
        return self.settings()

    def create_chat(self):
        with self.database.connect() as db:
            cursor = db.execute("INSERT INTO chat_sessions DEFAULT VALUES")
            return self.get_chat(cursor.lastrowid, db)

    def get_chat(self, chat_id, db=None):
        if db is None:
            with self.database.connect() as connection:
                return self.get_chat(chat_id, connection)
        return _dict(db.execute("SELECT * FROM chat_sessions WHERE id=?", (chat_id,)).fetchone())

    def chats(self):
        with self.database.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM chat_sessions ORDER BY updated_at DESC,id DESC")]

    def rename_chat(self, chat_id, title):
        title = title.strip()[:80]
        if not title:
            raise ValueError("A chat title is required.")
        with self.database.connect() as db:
            cursor = db.execute("UPDATE chat_sessions SET title=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (title, chat_id))
            if not cursor.rowcount:
                raise ValueError("Chat not found.")
            return self.get_chat(chat_id, db)

    def delete_chat(self, chat_id):
        with self.database.connect() as db:
            return bool(db.execute("DELETE FROM chat_sessions WHERE id=?", (chat_id,)).rowcount)

    def add_message(self, chat_id, role, content, message_type="chat"):
        if role not in ("user", "assistant", "system") or message_type not in ("chat", "command", "automation", "error"):
            raise ValueError("Invalid message type.")
        with self.database.connect() as db:
            if not self.get_chat(chat_id, db):
                raise ValueError("Chat not found.")
            cursor = db.execute("INSERT INTO chat_messages(session_id,role,content,message_type) VALUES (?,?,?,?)",
                                (chat_id, role, content, message_type))
            db.execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (chat_id,))
            if role == "user":
                row = db.execute("SELECT title FROM chat_sessions WHERE id=?", (chat_id,)).fetchone()
                if row["title"] == "New chat":
                    title = " ".join(content.split())[:56]
                    db.execute("UPDATE chat_sessions SET title=? WHERE id=?", (title, chat_id))
            return _dict(db.execute("SELECT * FROM chat_messages WHERE id=?", (cursor.lastrowid,)).fetchone())

    def messages(self, chat_id, limit=None):
        with self.database.connect() as db:
            if not self.get_chat(chat_id, db):
                raise ValueError("Chat not found.")
            if limit:
                rows = db.execute("SELECT * FROM (SELECT * FROM chat_messages WHERE session_id=? ORDER BY id DESC LIMIT ?) ORDER BY id",
                                  (chat_id, limit))
            else:
                rows = db.execute("SELECT * FROM chat_messages WHERE session_id=? ORDER BY id", (chat_id,))
            return [dict(row) for row in rows]

    def registry(self, kind):
        if kind not in ("applications", "websites"):
            raise ValueError("Invalid registry.")
        with self.database.connect() as db:
            return [dict(row) for row in db.execute(f"SELECT * FROM {kind} ORDER BY builtin DESC,name")]

    def resolve(self, kind, name):
        name = name.casefold().strip()
        for item in self.registry(kind):
            if name == item["name"].casefold() or name in _aliases(item["aliases"]):
                return item
        return None

    def save_mapping(self, kind, data):
        if kind not in ("applications", "websites"):
            raise ValueError("Invalid registry.")
        name = str(data.get("name", "")).strip()[:80]
        aliases = str(data.get("aliases", "")).strip()[:300]
        if not name:
            raise ValueError("A name is required.")
        proposed = {name.casefold(), *_aliases(aliases)}
        for item in self.registry(kind):
            if str(item["id"]) != str(data.get("id")) and proposed.intersection(
                    {item["name"].casefold(), *_aliases(item["aliases"])}):
                raise ValueError("That name or alias is already used.")
        if kind == "websites":
            url = str(data.get("url", "")).strip()
            parsed = urlparse(url)
            if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username
                    or parsed.password or any(char.isspace() for char in url)):
                raise ValueError("Enter a valid HTTP or HTTPS URL.")
            field, value = "url", url
        else:
            value = str(data.get("path", "")).strip()
            path = Path(value)
            if len(value) > 500 or not path.is_absolute() or path.suffix.casefold() not in (".exe", ".lnk"):
                raise ValueError("Enter an absolute .exe or .lnk path.")
            field = "path"
        identifier = data.get("id")
        with self.database.connect() as db:
            if identifier:
                row = db.execute(f"SELECT builtin FROM {kind} WHERE id=?", (identifier,)).fetchone()
                if not row or row["builtin"]:
                    raise ValueError("Built-in mappings cannot be edited.")
                db.execute(f"UPDATE {kind} SET name=?,aliases=?,{field}=?,enabled=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                           (name, aliases, value, int(bool(data.get("enabled", True))), identifier))
            else:
                cursor = db.execute(f"INSERT INTO {kind}(name,aliases,{field},enabled) VALUES (?,?,?,?)",
                                    (name, aliases, value, int(bool(data.get("enabled", True)))))
                identifier = cursor.lastrowid
            return _dict(db.execute(f"SELECT * FROM {kind} WHERE id=?", (identifier,)).fetchone())

    def delete_mapping(self, kind, identifier):
        if kind not in ("applications", "websites"):
            raise ValueError("Invalid registry.")
        with self.database.connect() as db:
            return bool(db.execute(f"DELETE FROM {kind} WHERE id=? AND builtin=0", (identifier,)).rowcount)

    def contacts(self):
        with self.database.connect() as db:
            return [dict(row) for row in db.execute("SELECT id,name,aliases FROM contacts ORDER BY name")]

    def resolve_contact(self, name):
        with self.database.connect() as db:
            for row in db.execute("SELECT * FROM contacts"):
                if name.casefold() in [row["name"].casefold(), *_aliases(row["aliases"])]:
                    return dict(row)
        return None

    def save_contact(self, name, phone, aliases="", identifier=None):
        import re
        name, phone = name.strip()[:80], phone.strip()
        if not name or not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
            raise ValueError("Enter a name and an international phone number such as +15551234567.")
        with self.database.connect() as db:
            proposed = {name.casefold(), *_aliases(aliases)}
            for row in db.execute("SELECT id,name,aliases FROM contacts"):
                if str(row["id"]) != str(identifier) and proposed.intersection(
                        {row["name"].casefold(), *_aliases(row["aliases"])}):
                    raise ValueError("That contact name or alias is already used.")
            if identifier:
                db.execute("UPDATE contacts SET name=?,phone=?,aliases=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                           (name, phone, aliases[:300], identifier))
            else:
                identifier = db.execute("INSERT INTO contacts(name,phone,aliases) VALUES (?,?,?)",
                                        (name, phone, aliases[:300])).lastrowid
        return identifier

    def delete_contact(self, identifier):
        with self.database.connect() as db:
            return bool(db.execute("DELETE FROM contacts WHERE id=?", (identifier,)).rowcount)

    def record_automation(self, command, result):
        if result.get("action") == "whatsapp":
            command = "send whatsapp message [redacted]"
        with self.database.connect() as db:
            db.execute("INSERT INTO automation_history(command,action_type,target,status,error_message) VALUES (?,?,?,?,?)",
                       (command, result.get("action", "unknown"), result.get("target"),
                        "success" if result["success"] else "failed", None if result["success"] else result["message"]))
