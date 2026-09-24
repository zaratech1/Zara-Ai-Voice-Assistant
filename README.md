# ZARA

ZARA is a Windows voice assistant with a Python/Eel backend and an HTML, CSS, and JavaScript interface. It accepts spoken or typed commands to open websites, search Google or Wikipedia, and play videos on YouTube.

## Requirements

- Windows with Microsoft Edge
- Python 3.12
- Internet access for speech recognition, web searches, and YouTube
- A microphone for voice commands

## Run

Open PowerShell in the project folder and run:

```powershell
.\env\Scripts\python.exe main.py
```

ZARA opens in an Edge app window. Click the microphone button to speak, or type a command and press Enter or click the chat button. The gear button shows command examples.

The included `env` virtual environment is configured for the Python installation on this machine. If you move the project to another computer, recreate it with Python 3.12:

```powershell
py -3.12 -m venv env
.\env\Scripts\python.exe -m pip install eel==0.18.2 SpeechRecognition==3.14.4 PyAudio==0.2.14 pyttsx3==2.99 playsound==1.2.2 pywhatkit==5.4
.\env\Scripts\python.exe main.py
```

## Commands

| Example | Action |
| --- | --- |
| `open google` | Opens Google |
| `open python tutorial on google` | Searches Google |
| `open wikipedia` | Opens Wikipedia |
| `open india history on wikipedia` | Searches Wikipedia |
| `open youtube` | Opens YouTube |
| `open example.org` | Opens a website |
| `open vs code` | Opens VS Code if `code` is on PATH |
| `play music on youtube` | Plays a YouTube result, or opens search results if playback fails |

## Troubleshooting

- If the microphone is unavailable, type commands in the input box. Check Windows microphone permissions and the selected input device for voice use.
- If speech recognition or YouTube playback fails, check the internet connection.
- If the virtual environment reports a missing Python executable after moving the project, recreate `env` with the commands above.
- Run `main.py` through Python rather than opening `front/index.html` directly. The page needs Eel's local server to handle commands.
