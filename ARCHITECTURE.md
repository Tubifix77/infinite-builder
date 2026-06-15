# Infinite Builder — Architecture Document

**Purpose:** A forever-running daemon that takes a user goal, builds an MVP using free-tier LLMs, then autonomously searches the web for inspiration and goldplates a new version each iteration — saving every version to disk — until manually stopped.

**Runs entirely free.** No paid API tokens. Uses the same flat-file key pattern as your other projects (`D:\AI\<service>`).

**Build target:** Python 3.x, Windows 11. Intended to be built with Claude Code using TDD — each step has a concrete passing test before the next step begins.

---

## Core Design Laws

1. **Build the room, not the worker.** The executive controls timing, saving, searching, and prompting. The LLM only generates code/ideas.
2. **Every iteration is atomic.** Generate → validate → save → log. A failed iteration is logged and skipped, never corrupts state.
3. **Flat keychain.** API keys live in `D:\AI\<service>` (e.g. `D:\AI\gemini`, `D:\AI\groq`). Read at startup, never hardcoded.
4. **Free tier aware.** On 429 or quota exhaustion, rotate to the next available provider. Sleep and retry when all exhausted.
5. **One goal = one folder.** Each run creates `D:\Projects\<goal-slug>\` containing every version as a numbered subfolder.

---

## Architecture Overview

```
main.py  (CLI entry: python main.py "your goal here")
   │
   ▼
builder/
   ├── keychain.py      — load keys from D:\AI\, provider rotation, quota tracking
   ├── planner.py       — LLM call: decompose goal → build plan
   ├── coder.py         — LLM call: generate / improve HTML artifact
   ├── searcher.py      — web search for inspiration (DuckDuckGo scrape, no key needed)
   ├── validator.py     — sanity check generated code (pure Python, no LLM)
   ├── saver.py         — write iteration to D:\Projects\<slug>\v<N>\
   ├── loop.py          — the forever loop: orchestrates plan→build→search→improve→save
   └── journal.py       — append-only JSONL log of every iteration
```

**Output per run:**
```
D:\Projects\todo-app\
   ├── v1\
   │   ├── index.html       ← the built artifact
   │   └── meta.json        ← {iteration, timestamp, provider, inspiration, improvements}
   ├── v2\
   │   ├── index.html
   │   └── meta.json
   ├── ...
   └── journal.jsonl        ← full run log
```

---

## Provider Landscape (free tier, verified June 2026)

| Provider | Key file | Model | Notes |
|---|---|---|---|
| Google Gemini | `D:\AI\gemini` | `gemini-2.0-flash` | Floor. 1500 RPD, 15 RPM |
| Groq | `D:\AI\groq` | `llama-3.3-70b-versatile` | ~1000 RPD, TPM-capped |
| Cerebras | `D:\AI\cerebras` | `llama-3.3-70b` | ~1700 RPD, 60K TPM |
| Ollama (local) | none | configurable | Fallback, no rate limit |

The keychain tries providers in capability order (Gemini → Groq → Cerebras → Ollama). On 429 or daily exhaustion it marks that provider unavailable and tries the next. When all are exhausted it sleeps 2 minutes and retries. This is lifted directly from APEX's `quota_state.py` logic.

---

## Build Phases — Test-Driven Order

Each phase ends with **a passing test**. Do not start the next phase until that test passes.

---

### Phase 0 — Skeleton and smoke test

**Goal:** Project exists, imports work, entry point runs without error.

**Files to create:**
```
infinite-builder/
├── main.py
├── builder/__init__.py
├── builder/keychain.py     (stub: just reads key files, prints what it found)
├── builder/journal.py      (stub: just appends to JSONL)
├── requirements.txt        (aiohttp, requests, pytest)
├── README.md
└── tests/
    └── test_smoke.py
```

**`requirements.txt`:**
```
aiohttp>=3.9
requests>=2.31
pytest>=8.0
pytest-asyncio>=0.23
```

**`main.py` stub:**
```python
import sys
from builder.keychain import Keychain
from builder.journal import Journal

def main():
    goal = " ".join(sys.argv[1:]) or "a todo app"
    print(f"[infinite-builder] goal: {goal}")
    kc = Keychain()
    print(f"[infinite-builder] providers available: {kc.available_providers()}")

if __name__ == "__main__":
    main()
```

**Test `tests/test_smoke.py`:**
```python
def test_import():
    from builder.keychain import Keychain
    from builder.journal import Journal
    assert True

def test_keychain_init():
    from builder.keychain import Keychain
    kc = Keychain()
    # Should not raise even if no keys present
    providers = kc.available_providers()
    assert isinstance(providers, list)
```

**Passing condition:** `pytest tests/test_smoke.py` — 2 PASSED.

---

### Phase 1 — Keychain

**Goal:** Read API keys from `D:\AI\<service>`, track quota, rotate providers on exhaustion.

**`builder/keychain.py` — full implementation:**

Key behaviours:
- `__init__`: scans `D:\AI\` for known key files (`gemini`, `groq`, `cerebras`). Reads content, strips whitespace. Marks Ollama as always-available with no key.
- `available_providers() -> list[str]`: returns provider names with a key present (or Ollama).
- `async complete(prompt, system="") -> str`: tries providers in order. On success returns text. On 429/quota raises are caught, that provider marked exhausted, next tried. Raises `RuntimeError("all exhausted")` when none left.
- `reset_if_new_day()`: checks if UTC date changed since last reset, clears exhausted flags.
- Quota state persisted to `quota_state.json` in the run directory (same schema as APEX: `{providers: {name: {available, requests_today, last_reset_date}}}`).

Provider configs (hardcoded, keys injected at runtime):
```python
PROVIDERS = [
    {
        "name": "gemini",
        "model": "gemini-2.0-flash",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai",
        "rpd_limit": 1500,
        "capability": 8,
    },
    {
        "name": "groq",
        "model": "llama-3.3-70b-versatile",
        "endpoint": "https://api.groq.com/openai/v1",
        "rpd_limit": 1000,
        "capability": 7,
    },
    {
        "name": "cerebras",
        "model": "llama-3.3-70b",
        "endpoint": "https://api.cerebras.ai/v1",
        "rpd_limit": 1700,
        "capability": 7,
    },
    {
        "name": "ollama",
        "model": "gemma3:12b",
        "endpoint": "http://localhost:11434/v1",
        "rpd_limit": None,       # unlimited
        "capability": 5,
    },
]
```

All four use the OpenAI-compatible `/chat/completions` endpoint. Gemini uses the `/v1beta/openai` path that Google exposes.

**Reference implementation:** `D:\Projects\apex\adapters\gemini_flash.py` — proven in production, handles 429, timeouts, and Ollama warm-up. Use it as the model for `_call_provider`.

**Test `tests/test_keychain.py`:**
```python
import pytest
from unittest.mock import AsyncMock
from builder.keychain import Keychain

def test_available_providers_returns_list():
    kc = Keychain()
    result = kc.available_providers()
    assert isinstance(result, list)

def test_no_keys_still_has_ollama():
    kc = Keychain()
    providers = kc.available_providers()
    assert "ollama" in providers

def test_reset_if_new_day_clears_exhausted():
    kc = Keychain()
    kc._state["providers"]["gemini"] = {
        "available": False,
        "requests_today": 1500,
        "last_reset_date": "2020-01-01",
    }
    kc.reset_if_new_day()
    assert kc._state["providers"]["gemini"]["available"] is True

@pytest.mark.asyncio
async def test_complete_raises_when_all_exhausted():
    kc = Keychain()
    for name in ["gemini", "groq", "cerebras", "ollama"]:
        kc._state["providers"][name] = {"available": False, "requests_today": 9999, "last_reset_date": "2020-01-01"}
    with pytest.raises(RuntimeError, match="exhausted"):
        await kc.complete("hello")

@pytest.mark.asyncio
async def test_complete_returns_string_on_success(monkeypatch):
    kc = Keychain()
    async def fake_call(provider_name, prompt, system):
        return "hello world"
    monkeypatch.setattr(kc, "_call_provider", fake_call)
    result = await kc.complete("say hi")
    assert isinstance(result, str)
    assert len(result) > 0
```

**Passing condition:** `pytest tests/test_keychain.py` — 5 PASSED.

---

### Phase 2 — Journal

**Goal:** Append-only JSONL log, readable as a list of dicts.

**`builder/journal.py` — full implementation:**

```python
# Schema per entry:
# {"ts": float, "kind": str, "content": str, "meta": dict}
# Kinds: "start", "plan", "build", "search", "improve", "save", "error", "quota_sleep", "wake"
```

Methods:
- `__init__(path: str)`: creates file if absent.
- `append(kind, content, meta=None)`: write one JSON line.
- `recent(n=20) -> list[dict]`: last N entries.
- `all() -> list[dict]`: full log.

**Test `tests/test_journal.py`:**
```python
import tempfile, os, json
from builder.journal import Journal

def test_append_and_read():
    with tempfile.TemporaryDirectory() as tmp:
        j = Journal(os.path.join(tmp, "journal.jsonl"))
        j.append("start", "beginning run", {"goal": "test"})
        j.append("build", "generated code")
        entries = j.all()
        assert len(entries) == 2
        assert entries[0]["kind"] == "start"
        assert entries[1]["kind"] == "build"

def test_recent():
    with tempfile.TemporaryDirectory() as tmp:
        j = Journal(os.path.join(tmp, "journal.jsonl"))
        for i in range(25):
            j.append("build", f"iteration {i}")
        assert len(j.recent(10)) == 10
        assert len(j.recent(100)) == 25

def test_meta_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        j = Journal(os.path.join(tmp, "journal.jsonl"))
        j.append("save", "saved v1", {"version": 1, "provider": "gemini"})
        entry = j.all()[0]
        assert entry["meta"]["version"] == 1
        assert entry["meta"]["provider"] == "gemini"

def test_survives_existing_file():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "journal.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({"ts": 1.0, "kind": "old", "content": "x"}) + "\n")
        j = Journal(path)
        j.append("new", "new entry")
        entries = j.all()
        assert len(entries) == 2
        assert entries[0]["kind"] == "old"
```

**Passing condition:** `pytest tests/test_journal.py` — 4 PASSED.

---

### Phase 3 — Saver

**Goal:** Write a versioned iteration to disk under `D:\Projects\<slug>\v<N>\`.

**`builder/saver.py` — full implementation:**

- `slug(goal: str) -> str`: lowercase, hyphens, max 40 chars. `"A Todo App"` → `"a-todo-app"`.
- `class Saver`: init with `base_dir` (default `D:\Projects`) and `goal`.
  - `next_version() -> int`: scans existing `v1`, `v2`... subdirs, returns next number.
  - `save(code: str, meta: dict) -> str`: writes `index.html` + `meta.json` to `D:\Projects\<slug>\v<N>\`. Returns the path.
- `meta.json` schema: `{version, goal, timestamp_utc, provider, inspiration_query, improvements, iteration_time_s}`.

**Test `tests/test_saver.py`:**
```python
import tempfile, os, json
from builder.saver import Saver, slug

def test_slug():
    assert slug("A Todo App") == "a-todo-app"
    assert slug("Build me a CALCULATOR!!!") == "build-me-a-calculator"
    assert slug("  spaces  ") == "spaces"
    long = "a" * 100
    assert len(slug(long)) <= 40

def test_first_save():
    with tempfile.TemporaryDirectory() as tmp:
        s = Saver(base_dir=tmp, goal="test app")
        path = s.save("<html>hello</html>", {"provider": "gemini", "version": 1})
        assert os.path.exists(os.path.join(path, "index.html"))
        assert os.path.exists(os.path.join(path, "meta.json"))
        with open(os.path.join(path, "index.html")) as f:
            assert "hello" in f.read()

def test_version_increments():
    with tempfile.TemporaryDirectory() as tmp:
        s = Saver(base_dir=tmp, goal="test app")
        assert s.next_version() == 1
        s.save("<html>v1</html>", {})
        assert s.next_version() == 2
        s.save("<html>v2</html>", {})
        assert s.next_version() == 3

def test_meta_json_contents():
    with tempfile.TemporaryDirectory() as tmp:
        s = Saver(base_dir=tmp, goal="calculator")
        path = s.save("<html/>", {"provider": "groq", "improvements": ["dark mode"]})
        with open(os.path.join(path, "meta.json")) as f:
            meta = json.load(f)
        assert meta["provider"] == "groq"
        assert meta["improvements"] == ["dark mode"]
        assert "timestamp_utc" in meta
```

**Passing condition:** `pytest tests/test_saver.py` — 4 PASSED.

---

### Phase 4 — Validator

**Goal:** Sanity-check generated HTML without any LLM call.

**`builder/validator.py` — full implementation:**

Pure Python checks. Returns `(ok: bool, reason: str)`.

Checks (in order, fail fast):
1. `len(code) > 200` — not a stub/error response.
2. `"<html"` present (case-insensitive).
3. `"</html>"` present — not truncated.
4. `"<script"` present — must have JavaScript (we're building interactive apps).
5. No LLM refusal markers: `"I cannot"`, `"I'm sorry"`, `"As an AI"` (case-insensitive) in the first 200 chars.
6. Balanced `<` / `>` count (within 5% tolerance) — not obviously malformed.

**Test `tests/test_validator.py`:**
```python
from builder.validator import validate

GOOD_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Test</title></head>
<body><h1>Hello</h1>
<script>console.log('hi');</script>
</body></html>"""

def test_good_html_passes():
    ok, reason = validate(GOOD_HTML)
    assert ok, reason

def test_too_short_fails():
    ok, reason = validate("<html><script>x</script></html>")
    assert not ok

def test_missing_script_fails():
    ok, reason = validate("<!DOCTYPE html><html><body><p>hi</p></body></html>")
    assert not ok

def test_truncated_fails():
    ok, reason = validate("<html><script>console.log('hi')</script>")
    assert not ok

def test_refusal_detected():
    ok, reason = validate("I cannot create this application because...")
    assert not ok

def test_empty_fails():
    ok, reason = validate("")
    assert not ok
```

**Passing condition:** `pytest tests/test_validator.py` — 6 PASSED.

---

### Phase 5 — Searcher

**Goal:** DuckDuckGo web search returning inspiration strings. No API key required.

**`builder/searcher.py` — full implementation:**

Uses `requests` to hit `https://html.duckduckgo.com/html/?q=<query>` and extracts result titles + snippets with regex. Returns `list[str]` of up to 5 inspiration strings.

Key behaviours:
- `search(query: str, n=5) -> list[str]`: scrape DDG HTML, return title+snippet pairs as strings. On any network error, return `[]` (never raises).
- `inspiration_query(goal: str, iteration: int) -> str`: generates a focused query rotating through angles — UX patterns (iter 1), visual design (2), features (3), accessibility (4), animation (5), back to UX (6+).
- 2-second timeout. If DDG returns nothing useful, return empty list silently.

**Test `tests/test_searcher.py`:**
```python
from unittest.mock import patch, MagicMock
from builder.searcher import Searcher, inspiration_query
import requests

def test_inspiration_query_varies():
    q1 = inspiration_query("todo app", 1)
    q2 = inspiration_query("todo app", 2)
    q3 = inspiration_query("todo app", 3)
    assert q1 != q2
    assert q2 != q3
    assert "todo" in q1.lower()

def test_inspiration_query_returns_string():
    q = inspiration_query("calculator", 1)
    assert isinstance(q, str)
    assert len(q) > 5

def test_search_returns_list_on_network_error():
    s = Searcher()
    with patch("requests.get", side_effect=Exception("network error")):
        result = s.search("anything")
    assert result == []

def test_search_returns_list_on_timeout():
    s = Searcher()
    with patch("requests.get", side_effect=requests.Timeout()):
        result = s.search("anything")
    assert result == []

def test_search_parses_mock_response():
    s = Searcher()
    fake_html = """<html><body>
    <div class="result__body">
      <a class="result__a">Best todo apps 2025</a>
      <a class="result__snippet">Clean minimal design with drag-and-drop.</a>
    </div>
    </body></html>"""
    mock_resp = MagicMock()
    mock_resp.text = fake_html
    mock_resp.status_code = 200
    with patch("requests.get", return_value=mock_resp):
        result = s.search("todo app design")
    assert isinstance(result, list)
```

**Passing condition:** `pytest tests/test_searcher.py` — 5 PASSED.

---

### Phase 6 — Planner and Coder

**Goal:** Two LLM-backed modules. Planner decomposes a goal into a build spec. Coder generates/improves HTML.

Both use `keychain.complete()` and parse responses defensively — if JSON parsing fails, return a safe fallback rather than crashing.

#### `builder/planner.py`

- `async plan(keychain, goal) -> dict`: one LLM call. Returns:
```json
{
  "title": "short title",
  "description": "one sentence",
  "core_features": ["feature 1", "feature 2", "feature 3"],
  "visual_direction": "clean, dark, minimalist"
}
```
System prompt instructs the model to respond with ONLY valid JSON, no markdown fences.

#### `builder/coder.py`

- `async build_mvp(keychain, plan: dict) -> str`: one LLM call. Returns complete single-file HTML. System prompt: "Respond ONLY with the complete HTML code, nothing else. No markdown. No explanation. Start with <!DOCTYPE html>."
- `async improve(keychain, current_code: str, inspiration: list[str], iteration: int) -> str`: passes current code + inspiration snippets, returns improved HTML.
- Both retry up to 3 times if `validate()` rejects the output.

**Test `tests/test_planner_coder.py`:**
```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_plan_returns_dict_on_valid_json():
    from builder.planner import plan
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value='{"title":"Test","description":"A test app","core_features":["feature 1"],"visual_direction":"clean"}')
    result = await plan(fake_kc, "a test app")
    assert isinstance(result, dict)
    assert "core_features" in result
    assert isinstance(result["core_features"], list)

@pytest.mark.asyncio
async def test_plan_fallback_on_bad_json():
    from builder.planner import plan
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="sorry I cannot do that as an AI")
    result = await plan(fake_kc, "a test app")
    assert isinstance(result, dict)
    assert "title" in result
    assert "core_features" in result

@pytest.mark.asyncio
async def test_build_mvp_returns_string():
    from builder.coder import build_mvp
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<!DOCTYPE html><html><head></head><body><script>1</script></body></html>")
    plan_dict = {"title": "Todo", "core_features": ["add items"], "visual_direction": "clean"}
    result = await build_mvp(fake_kc, plan_dict)
    assert isinstance(result, str)
    assert "html" in result.lower()

@pytest.mark.asyncio
async def test_improve_returns_string():
    from builder.coder import improve
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<!DOCTYPE html><html><head></head><body><script>2</script></body></html>")
    result = await improve(fake_kc, "<html/>", ["clean UI", "dark mode"], 2)
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_coder_retries_on_invalid_html():
    from builder.coder import build_mvp
    call_count = 0
    async def fake_complete(prompt, system=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "oops not html"
        return "<!DOCTYPE html><html><head></head><body><script>ok</script></body></html>"
    fake_kc = AsyncMock()
    fake_kc.complete = fake_complete
    plan_dict = {"title": "Test", "core_features": ["x"], "visual_direction": "y"}
    result = await build_mvp(fake_kc, plan_dict)
    assert call_count == 2
    assert "html" in result.lower()
```

**Passing condition:** `pytest tests/test_planner_coder.py` — 5 PASSED.

---

### Phase 7 — Loop

**Goal:** Wire all modules into the forever loop.

**`builder/loop.py` — full implementation:**

```python
async def run(goal: str, output_dir: str = r"D:\Projects", max_iterations: int = None):
    """
    The forever loop. Runs until KeyboardInterrupt, SIGTERM, or max_iterations reached.

    Cycle structure:
      Iteration 1:
        plan()  →  build_mvp()  →  validate()  →  save()  →  journal()
      Iteration N (N > 1):
        search(inspiration_query(goal, N))
        →  improve(current_code, inspiration)
        →  validate()
        →  save()
        →  journal()
      On validate() failure:
        log error, sleep 30s, retry same iteration (max 3 attempts)
      On RuntimeError("exhausted") from keychain:
        journal("quota_sleep"), sleep 120s, reset_if_new_day(), retry
    """
```

Print format: `[v1] building MVP...` / `[v2] searching for inspiration...` / `[v2] improving...` / `[v2] ✓ saved to D:\Projects\...`

On KeyboardInterrupt: log "stopped by user", print summary (N versions saved, elapsed time), exit cleanly.

**Test `tests/test_loop.py`:**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_loop_runs_one_iteration(tmp_path):
    from builder import loop as loop_mod
    fake_kc = AsyncMock()
    # First call = planner (returns JSON), subsequent = coder (returns HTML)
    fake_kc.complete = AsyncMock(side_effect=[
        '{"title":"T","description":"d","core_features":["f"],"visual_direction":"v"}',
        "<!DOCTYPE html><html><head></head><body><script>1</script></body></html>",
    ])
    fake_kc.reset_if_new_day = MagicMock()

    with patch_makers(loop_mod, fake_kc):
        await loop_mod.run(goal="test app", output_dir=str(tmp_path), max_iterations=1)

    v1 = tmp_path / "test-app" / "v1"
    assert v1.exists()
    assert (v1 / "index.html").exists()

@pytest.mark.asyncio
async def test_loop_skips_invalid_and_continues(tmp_path):
    from builder import loop as loop_mod
    call_count = 0
    async def fake_complete(prompt, system=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '{"title":"T","description":"d","core_features":["f"],"visual_direction":"v"}'
        if call_count in (2, 3):
            return "bad output"  # will fail validate, up to 3 retries
        return "<!DOCTYPE html><html><head></head><body><script>1</script></body></html>"
    fake_kc = AsyncMock()
    fake_kc.complete = fake_complete
    fake_kc.reset_if_new_day = MagicMock()
    with patch_makers(loop_mod, fake_kc):
        await loop_mod.run(goal="test app", output_dir=str(tmp_path), max_iterations=1)
    # Should still have saved v1 after retrying
    assert (tmp_path / "test-app" / "v1" / "index.html").exists()

# Helper — patch _make_keychain and _make_saver
from contextlib import contextmanager
from unittest.mock import patch
@contextmanager
def patch_makers(loop_mod, fake_kc):
    with patch.object(loop_mod, "_make_keychain", return_value=fake_kc):
        yield
```

**Passing condition:** `pytest tests/test_loop.py` — 2 PASSED.

---

### Phase 8 — Integration test (no mocks)

**Goal:** Full end-to-end run against Ollama. Builds 1 real MVP.

**Test `tests/test_integration.py`:**
```python
"""
Integration test — requires Ollama running at localhost:11434.
Skipped automatically if Ollama is not reachable.
"""
import pytest, os, requests

def ollama_available():
    try:
        return requests.get("http://localhost:11434/", timeout=2).status_code == 200
    except Exception:
        return False

@pytest.mark.skipif(not ollama_available(), reason="Ollama not running")
@pytest.mark.asyncio
async def test_full_mvp_build(tmp_path):
    from builder.loop import run
    await run(goal="a simple counter app", output_dir=str(tmp_path), max_iterations=1)

    slug_dirs = [d for d in os.listdir(tmp_path) if os.path.isdir(tmp_path / d)]
    assert len(slug_dirs) == 1
    v1 = tmp_path / slug_dirs[0] / "v1"
    assert (v1 / "index.html").exists()
    assert (v1 / "meta.json").exists()
    html = (v1 / "index.html").read_text()
    assert "<html" in html.lower()
    assert (tmp_path / slug_dirs[0] / "journal.jsonl").exists()
```

**Passing condition:** `pytest tests/test_integration.py -v` — 1 PASSED (or SKIPPED).

---

### Phase 9 — CLI polish

**`main.py` — final:**
```python
"""
Infinite Builder — autonomous LLM goldplating loop.
Usage: python main.py "your goal here"
       python main.py "your goal here" --dir D:\Projects
       python main.py "your goal here" --max 10
"""
import sys, argparse, asyncio
from builder.loop import run

def main():
    parser = argparse.ArgumentParser(description="Infinite Builder")
    parser.add_argument("goal", nargs="+", help="What to build")
    parser.add_argument("--dir", default=r"D:\Projects", help="Output directory")
    parser.add_argument("--max", type=int, default=None, help="Max iterations (default: forever)")
    args = parser.parse_args()
    goal = " ".join(args.goal)
    print(f"\n∞  Infinite Builder")
    print(f"   Goal:   {goal}")
    print(f"   Output: {args.dir}")
    print(f"   Ctrl+C to stop\n")
    try:
        asyncio.run(run(goal=goal, output_dir=args.dir, max_iterations=args.max))
    except KeyboardInterrupt:
        print("\n[stopped]")

if __name__ == "__main__":
    main()
```

**Passing condition (manual):** `python main.py "a pomodoro timer" --max 2` — produces `v1\index.html` and `v2\index.html`, both open in a browser.

---

## File Structure (final)

```
infinite-builder/
├── main.py
├── requirements.txt
├── README.md
├── ARCHITECTURE.md          ← this file
├── quota_state.json          ← runtime, gitignored
├── builder/
│   ├── __init__.py
│   ├── keychain.py
│   ├── planner.py
│   ├── coder.py
│   ├── searcher.py
│   ├── validator.py
│   ├── saver.py
│   ├── loop.py
│   └── journal.py
└── tests/
    ├── test_smoke.py
    ├── test_keychain.py
    ├── test_journal.py
    ├── test_saver.py
    ├── test_validator.py
    ├── test_searcher.py
    ├── test_planner_coder.py
    ├── test_loop.py
    └── test_integration.py
```

---

## Key Design Decisions

**Why single-file HTML?** Opens directly in a browser, no build step, no server. The creature produces a complete runnable artifact every iteration.

**Why DuckDuckGo with no key?** The webproxy MCP is Claude Desktop only — not available in Claude Code. DDG's HTML endpoint works without auth for lightweight scraping.

**Why Gemini Flash as the floor?** Same reason APEX uses it: 1500 RPD, permanently free, 1M context window fits large HTML + the full improvement prompt in one call.

**Why validate before saving?** Follows the done-gate principle from Growing Spine: completion must be real, not just asserted. A pure-Python validator catches LLM refusals and truncated code at zero token cost.

**Why max 3 retries per iteration?** Enough to recover from a single bad generation; not enough to spin. On 3 failures: log, skip, keep the previous `current_code`, move on.

**Why `max_iterations` parameter?** Makes the system testable without running forever. Production: omit or `--max None`. Tests: `--max 1`.

---

## Session Resume for Claude Code

When picking this up in a new session:

1. Read this document.
2. Run `pytest tests/ -v` — the highest passing phase is where you are.
3. If mid-phase: read the failing test, implement to pass it.
4. Never skip a phase's test gate.
5. For LLM API implementation details: `D:\Projects\apex\adapters\gemini_flash.py` is the reference — proven in production, handles 429, timeouts, and Ollama warm-up correctly.

