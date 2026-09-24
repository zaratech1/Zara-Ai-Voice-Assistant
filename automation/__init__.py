"""Allowlisted desktop and browser operations."""


def result(success, action, target, message):
    return {"success": bool(success), "action": action, "target": target, "message": message}
