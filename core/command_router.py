"""Single deterministic decision point for typed and spoken commands."""
from automation import result
from automation.websites import address_for, google_search, open_url, wikipedia_search
from automation.windows_apps import open_application
from automation.youtube import play, search
from core.intent_parser import parse


class CommandRouter:
    def __init__(self, repository):
        self.repository = repository

    def route(self, text):
        intent, target = parse(text)
        if intent == "chat":
            return None
        if intent == "empty":
            return result(False, "empty", "", "Please say or type a command.")
        if intent == "whatsapp":
            recipient, message = target
            contact = self.repository.resolve_contact(recipient)
            if not contact:
                return result(False, "whatsapp", recipient,
                              f"I couldn't find {recipient} in your contacts. Add them in Settings first.")
            return {"success": True, "action": "whatsapp_confirmation", "target": contact["name"],
                    "message": message, "contact_id": contact["id"]}
        if intent == "youtube_play":
            return play(target)
        if intent == "youtube_search":
            return search(target)
        if intent == "wikipedia_search":
            return wikipedia_search(target)
        if intent == "google_search":
            return google_search(target)
        if intent == "open":
            if target.endswith(" homepage"):
                target = target.removesuffix(" homepage")
            if not target:
                return result(False, "open", "", "What should I open?")
            app = self.repository.resolve("applications", target)
            if app:
                if not app["enabled"]:
                    return result(False, "open_app", app["name"], f"{app['name']} is disabled in Settings.")
                return open_application(app)
            site = self.repository.resolve("websites", target)
            if site:
                if not site["enabled"]:
                    return result(False, "open_website", site["name"], f"{site['name']} is disabled in Settings.")
                return open_url(site["url"], site["name"])
            url = address_for(target)
            if url:
                return open_url(url, target)
            # Preserve the old behavior for requests such as "open Python tutorials".
            if " " in target:
                return google_search(target)
            return result(False, "open", target, "I couldn't find that app or website. Add it in Settings.")
        return None
