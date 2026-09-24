"""Minimal OpenAI-compatible local HTTP client using the standard library."""
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from ai.prompts import SYSTEM_PROMPT


class AIUnavailable(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class LocalAIClient:
    def __init__(self, endpoint, model="", temperature=0.7, timeout=35, system_prompt=""):
        parsed = urlparse(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("The AI endpoint must be a local HTTP address.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("The AI endpoint must be a local server URL without credentials or query parameters.")
        path = parsed.path.rstrip("/")
        if path.endswith("/chat/completions"):
            self.endpoint = endpoint.rstrip("/")
        elif path.endswith("/v1"):
            self.endpoint = endpoint.rstrip("/") + "/chat/completions"
        else:
            self.endpoint = endpoint.rstrip("/") + "/v1/chat/completions"
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.system_prompt = system_prompt.strip() or SYSTEM_PROMPT

    def generate_response(self, messages, max_tokens=None):
        payload = {"model": self.model or "local", "messages": [{"role": "system", "content": self.system_prompt}, *messages],
                   "temperature": self.temperature, "stream": False}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        request = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect).open(request, timeout=self.timeout) as response:
                body = json.load(response)
            answer = body["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Empty model response")
            return answer.strip()
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, IndexError) as error:
            raise AIUnavailable("Local AI is unavailable. Start your configured AI server and try again.") from error

    def test_connection(self):
        return self.generate_response([{"role": "user", "content": "Reply with OK."}], max_tokens=8)
