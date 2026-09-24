# ZARA

ZARA is a Windows desktop assistant built with Python 3.12, Eel, HTML/CSS/JavaScript, and SQLite. Typed and spoken requests enter one command router. Known commands run controlled automation; other requests go to a configurable local AI server. Commands continue working when AI is offline.

## Setup

Install Python 3.12 and Microsoft Edge. In PowerShell from this folder:

```powershell
py -3.12 -m venv env
.\env\Scripts\python.exe -m pip install -r requirements.txt
.\env\Scripts\python.exe main.py
```

The development startup command remains `.\env\Scripts\python.exe main.py`. ZARA opens through Eel in an Edge app window. Do not open `front/index.html` directly.

The app creates `data/zara.db` and `data/zara.log` on first run. The old root `zara.db` is left untouched; it contained only a legacy command table and is not used by this version. The new database uses a schema version and preserves data on later launches.

## Commands

| Example | Result |
| --- | --- |
| `open calculator`, `launch notepad`, `open vs code` | Launch a registered Windows app |
| `open canva`, `open github`, `open example.org` | Open a website |
| `open google`, `open wikipedia`, `open youtube` | Open a site homepage |
| `search python decorators`, `open python tutorial on google` | Search Google |
| `wikipedia alan turing`, `open india history on wikipedia` | Search Wikipedia |
| `search youtube for django tutorial` | Search YouTube |
| `play music on youtube` | Open a matching YouTube video, with search fallback |
| `send whatsapp message to Rahul saying I'll reach at 8` | Show a confirmation before send automation |
| Any other question | Ask the local AI server |

Use Settings to add custom websites, executable paths, and WhatsApp contacts. Custom application paths must be absolute `.exe` or `.lnk` paths. WhatsApp contacts require international phone numbers such as `+15551234567`. Built-in mappings are protected from editing and deletion.

## Local AI Setup

ZARA sends conversational requests to a local OpenAI-compatible server. Its default server URL is `http://127.0.0.1:8080/v1`; it posts to `/v1/chat/completions`. An existing saved full chat endpoint also works. Start a compatible llama.cpp server with your own GGUF model, then set the server URL, model name (if needed), temperature, context size, timeout, and optional system prompt under **Settings → Local AI**. The **Test connection** button sends a short completion request and shows connected or offline status. No model is bundled, downloaded, or loaded in ZARA's process.

The URL is restricted to local HTTP addresses (`localhost`, `127.0.0.1`, or `::1`); redirects and proxy settings are ignored. Conversation history is saved in SQLite; only the latest configured number of chat messages goes to the model. Commands use the deterministic router first. If the server is offline, chat shows an error and commands continue to work. **Speak AI responses** is separate from general voice output. Long answers remain complete in chat and SQLite; speech reads up to the configured character limit and directs you to the screen for the rest.

## Hey Zara Setup

Wake-word detection uses [openWakeWord](https://github.com/dscripka/openWakeWord) with ONNX inference, locally on this computer. Install `requirements.txt`, which includes openWakeWord and its Windows ONNX dependencies. Then run `.\env\Scripts\python.exe -m voice.setup_wakeword_assets` once while online to download openWakeWord's two official ONNX feature models into the virtual environment. Runtime listening does not download anything. You must separately supply a **custom trained “Hey Zara” `.onnx` classifier**: openWakeWord's included phrases do not contain Hey Zara. Its [model training guide](https://github.com/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb) explains how to create one. Put the model anywhere readable on your computer, then enter its absolute path in **Settings → Wake word** and enable Hey Zara. A working microphone, Windows microphone permission, and a device capable of 16 kHz mono input are required. The default sensitivity is 0.5; raise it to reduce false activations or lower it if your phrase is missed. The optional activation sound and spoken response can be configured there. Disable the checkbox to stop background listening.

Model loading happens in a background thread. The status indicator reports starting, active, paused, or unavailable. If the model or microphone fails, the mic button and typed chat remain usable. Check `data/zara.log` and the model path if the indicator says unavailable. Continuous wake audio stays in memory locally and is not stored or uploaded. The detector closes its microphone stream before the normal speech recognizer opens it, and pauses while ZARA speaks.

## Voice

The microphone button and post-wake command capture use SpeechRecognition with **Google recognition**, so spoken commands are sent to that service and need internet access. Wake detection itself remains local. Microphone capture is bounded and raw audio is not stored. Text input works without a microphone or internet connection when no local AI response is needed.

Speech output uses Windows SAPI through pyttsx3 in a worker thread. Select a Windows voice, speech rate, and volume in Settings. The visualizer reflects wake listening, wake detected, command listening, processing, executing, speaking, and error states. The listening animation indicates activity rather than measured microphone loudness.

## WhatsApp

Add a contact under **Settings → Contacts**. Every WhatsApp command displays its recipient and exact message for explicit confirmation. After confirmation, pywhatkit opens WhatsApp Web and sends through browser automation. You must be signed in to WhatsApp Web, keep the browser available, and verify delivery in the conversation. ZARA reports that automation completed, not that WhatsApp confirmed delivery. The separate automation log redacts WhatsApp content.

## Architecture

- `main.py`: Eel startup and API registration.
- `core/`: assistant state, request coordination, intent parsing, and routing.
- `automation/`: Windows apps, sites, searches, YouTube, and WhatsApp.
- `voice/`: recognition, speech output, and optional wake word service.
- `ai/`: local HTTP AI client and system prompt.
- `database/`: versioned schema and short-lived SQLite connections.
- `front/`: responsive interface and canvas visualizer.

SQLite stores settings, applications, websites, chat sessions, messages, contacts, and automation history. Chat deletion cascades only to messages from that chat. Conversations are sent to AI with a bounded recent context; the complete text history remains local.

## Tests

Run the automated tests with:

```powershell
.\env\Scripts\python.exe -m unittest discover -s tests -v
```

The tests mock browser launches and AI responses. Real microphone, TTS, Windows app launches, YouTube playback, WhatsApp Web, and a running AI server require manual checks on the target machine.
