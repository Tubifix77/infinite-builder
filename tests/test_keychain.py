import pytest
from unittest.mock import AsyncMock
from builder.keychain import Keychain

def test_available_providers_returns_list():
    kc = Keychain()
    result = kc.available_providers()
    assert isinstance(result, list)

def test_ollama_always_present():
    # Ollama requires no key file — always in the list
    kc = Keychain()
    assert "ollama" in kc.available_providers()

def test_reset_if_new_day_clears_exhausted():
    kc = Keychain()
    kc._state["providers"]["gemini"] = {
        "available": False,
        "requests_today": 250,
        "last_reset_date": "2020-01-01",
    }
    kc.reset_if_new_day()
    assert kc._state["providers"]["gemini"]["available"] is True

@pytest.mark.asyncio
async def test_complete_raises_when_all_exhausted():
    kc = Keychain()
    for name in ["gemini", "groq", "cerebras", "ollama"]:
        kc._state["providers"][name] = {
            "available": False, "requests_today": 9999, "last_reset_date": "2020-01-01"
        }
    with pytest.raises(RuntimeError, match="exhausted"):
        await kc.complete("hello")

@pytest.mark.asyncio
async def test_complete_returns_string_on_success(monkeypatch):
    kc = Keychain()
    async def fake_call(provider_cfg, prompt, system):
        return "hello world"
    monkeypatch.setattr(kc, "_call_provider", fake_call)
    result = await kc.complete("say hi")
    assert isinstance(result, str)
    assert len(result) > 0
