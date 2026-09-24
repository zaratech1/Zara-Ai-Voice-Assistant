"""One-time download of official openWakeWord ONNX feature models.

The Hey Zara classifier is separate and must be trained or supplied by the user.
"""
from pathlib import Path
from urllib.request import urlopen

import openwakeword


def main():
    destination = Path(openwakeword.__file__).parent / "resources" / "models"
    destination.mkdir(parents=True, exist_ok=True)
    for feature in openwakeword.FEATURE_MODELS.values():
        url = feature["download_url"].replace(".tflite", ".onnx")
        target = destination / url.rsplit("/", 1)[-1]
        if target.is_file():
            print(f"Already installed: {target.name}")
            continue
        partial = target.with_suffix(".download")
        try:
            with urlopen(url, timeout=60) as response, partial.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            partial.replace(target)
            print(f"Installed: {target.name}")
        finally:
            partial.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
