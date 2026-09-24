"""WhatsApp runs only after the controller verifies a pending confirmation token."""
import logging
import threading

from automation import result

LOG = logging.getLogger(__name__)
_send_lock = threading.Lock()


def send(contact, message):
    try:
        import pywhatkit
        from pywhatkit import whats
        # pywhatkit writes the recipient and message to its own log by default.
        with _send_lock:
            original_logger = whats.log.log_message
            whats.log.log_message = lambda **_: None
            try:
                pywhatkit.sendwhatmsg_instantly(contact["phone"], message, wait_time=15, tab_close=False)
            finally:
                whats.log.log_message = original_logger
        return result(True, "whatsapp", contact["name"],
                      "WhatsApp send automation completed. Please check the conversation for delivery.")
    except Exception:
        LOG.exception("WhatsApp automation failed")
        return result(False, "whatsapp", contact["name"], "I couldn't send the WhatsApp message.")
