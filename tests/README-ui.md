# Frontend verification

From the repository root, run `./env/Scripts/python.exe -m http.server 8765 --bind 127.0.0.1` and open `http://127.0.0.1:8765/tests/ui-smoke.html`.

The browser harness loads the actual HTML/CSS/JavaScript into an iframe and replaces only the Eel boundary with an in-memory fixture. It never launches applications, records audio, sends WhatsApp messages, or changes the real database/settings. All nine groups should show PASS. This is separate from the real Eel app at port 8000.

Coverage:
- Home, unique element IDs, desktop and mobile overflow (1366×768, 1920×1080, 390×844, 320×568).
- History drawer, focus containment, Escape, new chat, loading, rename and deletion.
- Enter/Send submission, Shift+Enter, duplicate-send detection and chat rendering.
- Mic start/stop handlers; wake, listening, thinking, executing, speaking and error events.
- All nine settings sections, registry/contact loading, setting saves, light theme, AI connection test and voice test handlers.
- Both WhatsApp confirmation decisions against the mock only, and browser runtime errors.

## Verification on 2026-09-25

- All 14 existing Python tests passed (`./env/Scripts/python.exe -m unittest discover -s tests -v`).
- All nine browser smoke-test groups passed.
- Static audit: no original HTML IDs removed, no duplicate IDs, no missing literal ID selectors, no Eel API names or backend event branches removed. JavaScript syntax checks passed.
- Actual Eel session: new chat, history drawer, Enter and Send, settings, AI fields, and application registry worked. Calculator returned a launch success and its process was present. Canva and YouTube commands returned successful backend launch responses; external browser playback was not inspected.
- `hello` reached the real AI route and displayed its offline error correctly. The configured local AI server was unavailable; a successful model response could not be verified.
- Actual mic control entered Listening and returned to Ready. A spoken question, audible TTS and wake-word activation were not verified. Wake word was disabled in existing settings. No voice configuration was changed.
- No errors/warnings in the real page's captured browser console. The Python log showed no new traceback during these checks.

Python backend, database logic, environment configuration, command routing, voice and automation source files are unchanged. Real smoke commands remain in the verification conversation; existing conversations were retained.
