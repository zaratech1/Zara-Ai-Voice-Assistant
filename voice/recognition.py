"""SpeechRecognition provider boundary, with bounded microphone capture."""
import time

import speech_recognition as sr


class RecognitionFailure(Exception):
    pass


def listen(stop_event=None, timeout=8, phrase_time_limit=8):
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.9
    recognizer.operation_timeout = 6
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            deadline = time.monotonic() + timeout
            while True:
                if stop_event is not None and stop_event.is_set():
                    return None
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise sr.WaitTimeoutError()
                try:
                    audio = recognizer.listen(source, timeout=min(1, remaining),
                                              phrase_time_limit=phrase_time_limit)
                    break
                except sr.WaitTimeoutError:
                    continue
        if stop_event is not None and stop_event.is_set():
            return None
        return recognizer.recognize_google(audio, language="en-IN")
    except sr.WaitTimeoutError as error:
        raise RecognitionFailure("I didn't hear anything. Please try again.") from error
    except sr.UnknownValueError as error:
        raise RecognitionFailure("I couldn't understand that. Please try again.") from error
    except sr.RequestError as error:
        raise RecognitionFailure("Speech recognition needs an internet connection.") from error
    except (OSError, AttributeError) as error:
        raise RecognitionFailure("Microphone unavailable. Check Windows microphone permissions. You can continue using typed commands.") from error
