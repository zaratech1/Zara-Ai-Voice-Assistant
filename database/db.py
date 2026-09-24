"""Versioned, non-destructive SQLite initialization."""
import json
import sqlite3
from contextlib import contextmanager

from config import DATABASE, DEFAULT_SETTINGS

SCHEMA_VERSION = 1

APPLICATIONS = [
    ("Notepad", "notepad", "notepad.exe"),
    ("Calculator", "calculator,calc", "calc.exe"),
    ("Paint", "paint,mspaint", "mspaint.exe"),
    ("Command Prompt", "command prompt,cmd", "cmd.exe"),
    ("PowerShell", "powershell,power shell", "powershell.exe"),
    ("VS Code", "vs code,vscode,visual studio code", "code"),
    ("File Explorer", "file explorer,explorer", "explorer.exe"),
    ("Settings", "settings,windows settings", "ms-settings:"),
    ("Task Manager", "task manager", "taskmgr.exe"),
]
WEBSITES = [
    ("Google", "google", "https://www.google.com/"),
    ("YouTube", "youtube", "https://www.youtube.com/"),
    ("Canva", "canva", "https://www.canva.com/"),
    ("GitHub", "github", "https://github.com/"),
    ("Gmail", "gmail", "https://mail.google.com/"),
    ("LinkedIn", "linkedin", "https://www.linkedin.com/"),
    ("Wikipedia", "wikipedia", "https://en.wikipedia.org/"),
    ("Instagram", "instagram", "https://www.instagram.com/"),
    ("Facebook", "facebook", "https://www.facebook.com/"),
    ("Reddit", "reddit", "https://www.reddit.com/"),
]


class Database:
    def __init__(self, path=DATABASE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError("This database was created by a newer version of ZARA.")
            if version < 1:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY, value TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS applications (
                        id INTEGER PRIMARY KEY, name TEXT NOT NULL, aliases TEXT NOT NULL,
                        command TEXT, path TEXT, enabled INTEGER NOT NULL DEFAULT 1,
                        builtin INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS websites (
                        id INTEGER PRIMARY KEY, name TEXT NOT NULL, aliases TEXT NOT NULL,
                        url TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
                        builtin INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id INTEGER PRIMARY KEY, title TEXT NOT NULL DEFAULT 'New chat',
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                        role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                        content TEXT NOT NULL, message_type TEXT NOT NULL DEFAULT 'chat',
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS messages_session_idx ON chat_messages(session_id,id);
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL,
                        aliases TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS automation_history (
                        id INTEGER PRIMARY KEY, command TEXT NOT NULL, action_type TEXT NOT NULL,
                        target TEXT, status TEXT NOT NULL, error_message TEXT,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                db.execute("PRAGMA user_version=1")
            for key, value in DEFAULT_SETTINGS.items():
                db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (key, json.dumps(value)))
            for name, aliases, command in APPLICATIONS:
                if not db.execute("SELECT 1 FROM applications WHERE name=? AND builtin=1", (name,)).fetchone():
                    db.execute("INSERT INTO applications(name,aliases,command,builtin) VALUES (?,?,?,1)",
                               (name, aliases, command))
            for name, aliases, url in WEBSITES:
                if not db.execute("SELECT 1 FROM websites WHERE name=? AND builtin=1", (name,)).fetchone():
                    db.execute("INSERT INTO websites(name,aliases,url,builtin) VALUES (?,?,?,1)",
                               (name, aliases, url))
