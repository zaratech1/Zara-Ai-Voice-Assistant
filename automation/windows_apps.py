import logging
import os
import shutil
import subprocess
from pathlib import Path

from automation import result

LOG = logging.getLogger(__name__)


def open_application(item):
    name = item["name"]
    try:
        if os.name != "nt":
            return result(False, "open_app", name, "Windows applications are only available on Windows.")
        if item.get("path"):
            path = Path(item["path"]).expanduser()
            if not path.is_file() or path.suffix.casefold() not in (".exe", ".lnk"):
                return result(False, "open_app", name, "The requested application path no longer exists or is not executable.")
            os.startfile(str(path))
        elif item["command"] == "ms-settings:":
            os.startfile("ms-settings:")
        else:
            command = item.get("command")
            executable = shutil.which(command) if command else None
            if not executable:
                return result(False, "open_app", name, f"I couldn't find {name} on this computer.")
            if Path(executable).suffix.casefold() in (".cmd", ".bat"):
                os.startfile(executable)
            else:
                subprocess.Popen([executable], close_fds=True)
        return result(True, "open_app", name, f"Opening {name}.")
    except Exception:
        LOG.exception("Application launch failed: %s", name)
        return result(False, "open_app", name, f"I couldn't open {name}.")
