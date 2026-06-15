import asyncio
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

PROVIDERS = [
    {
        "name": "gemini",
        "key_file": r"D:\AI\gemini.key",
        "model": "gemini-2.5-flash",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "rpd_limit": 250,
        "capability": 8,
    },
    {
        "name": "groq",
        "key_file": r"D:\AI\groq.key",
        "model": "llama-3.3-70b-versatile",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "rpd_limit": 1000,
        "capability": 7,
    },
    {
        "name": "cerebras",
        "key_file": r"D:\AI\cerebras.key",
        "model": "gpt-oss-120b",
        "endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "rpd_limit": 1700,
        "capability": 7,
    },
    {
        "name": "ollama",
        "key_file": None,
        "model": "gemma4:e2b",
        "endpoint": "http://localhost:11434/v1/chat/completions",
        "rpd_limit": None,
        "capability": 5,
    },
]

_STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quota_state.json")


class _QuotaError(Exception):
    pass


class Keychain:
    def __init__(self, state_file: str = _STATE_FILE, use_ollama: bool = False):
        self._state_file = state_file
        self._use_ollama = use_ollama
        self._keys: dict[str, str] = {}
        for p in PROVIDERS:
            if p["key_file"] is not None:
                try:
                    with open(p["key_file"]) as f:
                        key = f.read().strip()
                    if key:
                        self._keys[p["name"]] = key
                except FileNotFoundError:
                    pass
        self._state = self._load_state()

    def _load_state(self) -> dict:
        today = datetime.now(timezone.utc).date().isoformat()
        default = {
            "providers": {
                p["name"]: {"available": True, "requests_today": 0, "last_reset_date": today}
                for p in PROVIDERS
            }
        }
        try:
            with open(self._state_file) as f:
                state = json.load(f)
            for p in PROVIDERS:
                if p["name"] not in state.get("providers", {}):
                    state.setdefault("providers", {})[p["name"]] = default["providers"][p["name"]]
            return state
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return default

    def _save_state(self):
        with open(self._state_file, "w") as f:
            json.dump(self._state, f, indent=2)

    def available_providers(self) -> list[str]:
        result = []
        for p in PROVIDERS:
            if p["key_file"] is None:
                if self._use_ollama:
                    result.append(p["name"])
            elif p["name"] in self._keys:
                result.append(p["name"])
        return result

    def reset_if_new_day(self):
        today = datetime.now(timezone.utc).date().isoformat()
        for name, info in self._state["providers"].items():
            if info.get("last_reset_date", "") != today:
                self._state["providers"][name] = {
                    "available": True,
                    "requests_today": 0,
                    "last_reset_date": today,
                }
        self._save_state()

    async def complete(self, prompt: str, system: str = "") -> str:
        candidates = [
            p for p in PROVIDERS
            if self._state["providers"].get(p["name"], {}).get("available", True)
            and (p["key_file"] is None and self._use_ollama or p["name"] in self._keys)
        ]
        if not candidates:
            raise RuntimeError("all providers exhausted")

        for provider in candidates:
            try:
                text = await self._call_provider(provider, prompt, system)
                pstate = self._state["providers"][provider["name"]]
                pstate["requests_today"] = pstate.get("requests_today", 0) + 1
                self._save_state()
                return text
            except _QuotaError:
                self._state["providers"][provider["name"]]["available"] = False
                self._save_state()
            except Exception:
                pass

        raise RuntimeError("all providers exhausted")

    async def _call_provider(self, provider_cfg: dict, prompt: str, system: str) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": provider_cfg["model"],
            "messages": messages,
            "max_tokens": 4096,
        }).encode()

        headers = {"Content-Type": "application/json"}
        key = self._keys.get(provider_cfg["name"])
        if key:
            headers["Authorization"] = f"Bearer {key}"

        req = urllib.request.Request(provider_cfg["endpoint"], data=payload, headers=headers)

        loop = asyncio.get_event_loop()

        def _do():
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())

        try:
            data = await loop.run_in_executor(None, _do)
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise _QuotaError(f"429 from {provider_cfg['name']}")
            raise
