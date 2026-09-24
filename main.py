import eel
from pathlib import Path

from engine.command import allCommands  # Register the Eel command endpoint.
from engine.features import playAssistantsound

eel.init(str(Path(__file__).resolve().parent / 'front'))

if __name__ == '__main__':
    playAssistantsound()
    eel.start('index.html', mode='edge', host='localhost', block=True)


