# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status: greenfield (spec-only)

This repo currently contains **only documentation** — no code exists yet (no `main.py`, no
`builder/`, no `tests/`, no `requirements.txt`). [ARCHITECTURE.md](ARCHITECTURE.md) is the
authoritative, self-contained build spec: it gives complete implementations or precise
behavioral specs for every module, plus the full test suite, organized as 10 TDD phases
(Phase 0 → Phase 9).

**Build discipline (this is the core workflow):**
- Implement **one phase at a time**, in order. Each phase ends with a named test gate, e.g.
  *"`pytest tests/test_keychain.py` — 5 PASSED"*. Do not start the next phase until the
  current gate passes.
- To find where the build stands, run `pytest tests/ -v` — the highest passing phase is the
  current position. If mid-phase, read the failing test and implement to pass it.
- When ARCHITECTURE.md gives **full code** for a module (keychain, journal, saver, loop,
  main), follow it closely. When it gives only **behavior + the test** (validator, searcher,
  planner, coder), implement to pass the provided test.
- The test code in ARCHITECTURE.md is the spec — write `tests/test_*.py` from it before/with
  the implementation, don't invent your own assertions.

## Commands

```bash
pip install -r requirements.txt          # deps: aiohttp, requests, pytest, pytest-asyncio (created in Phase 0)

pytest tests/ -v                          # run everything; shows current phase position
pytest tests/test_saver.py                # run one phase's gate
pytest tests/test_saver.py::test_slug     # run a single test
python main.py "a pomodoro timer"         # run forever (Ctrl+C to stop)
python main.py "a calculator" --max 2     # stop after N iterations (use this to test end-to-end)
python main.py "a weather app" --dir C:\MyProjects   # custom output root
```

- Async tests use the `@pytest.mark.asyncio` marker, so **pytest-asyncio must be installed**
  (and its async mode active) or those tests error/skip rather than run.
- `tests/test_integration.py` (Phase 8) hits real Ollama at `localhost:11434` and
  **auto-skips if Ollama isn't running** — it is the only test that makes live LLM calls; all
  others mock `keychain.complete`.

## Architecture (the big picture)

A forever-running daemon: take a goal → build an MVP → each iteration, search the web for
inspiration and goldplate a new version → save every version to disk → loop until stopped.

**Executive-loop pattern ("build the room, not the worker"):** `builder/loop.py` owns all
timing, saving, searching, and prompting. The LLM only generates code/ideas — it never
controls flow. Modules are thin and single-purpose:

```
main.py (CLI) → builder/loop.py (orchestrator)
  keychain.py  free-tier provider rotation + quota tracking (the only thing that calls LLMs)
  planner.py   LLM: goal → build-spec JSON
  coder.py     LLM: build_mvp() / improve()  — retries up to 3x on validator rejection
  searcher.py  DuckDuckGo HTML scrape for inspiration (no API key; never raises, returns [])
  validator.py pure-Python sanity check (no LLM, zero token cost)
  saver.py     write D:\Projects\<slug>\v<N>\{index.html, meta.json}
  journal.py   append-only JSONL run log
```

**Atomic iteration** is the central invariant: every cycle is `generate → validate → save →
log`. A failed iteration is logged and skipped — it must never corrupt state or overwrite a
good previous version. Iteration 1 runs `plan → build_mvp`; iterations 2+ run `search →
improve` against the current code.

**Validate-before-save gate:** `validator.py` rejects LLM refusals, truncated output, and
non-interactive HTML *before* anything touches disk — cheaply, with no extra token cost. The
coder retries (max 3) on rejection; the loop sleeps 30s and retries the iteration on
persistent failure.

**Free-tier keychain rotation:** providers are tried in capability order
**Gemini → Groq → Cerebras → Ollama**. On HTTP 429 / daily-quota exhaustion, mark that
provider unavailable and fall through to the next; when all are exhausted, journal a
`quota_sleep`, sleep 120s, `reset_if_new_day()`, and retry. Quota state persists to
`quota_state.json` (gitignored). All four providers speak the same OpenAI-compatible
`/chat/completions` API, so adding/swapping a provider is just a dict in the `PROVIDERS` list.

## Conventions & environment

- **API keys** live as flat files at `D:\AI\<service>.key` — plain text, one line, raw key, no
  quotes/labels. Read at startup, never hardcoded. Present on this machine: `gemini.key`,
  `groq.key`, `cerebras.key`. Ollama needs no key and is always available.
  (Note: README's setup section writes bare names like `D:\AI\gemini`; the `.key` extension
  used in ARCHITECTURE.md and on disk is the correct one.)
- **Output lives outside the repo:** built apps go to `D:\Projects\<goal-slug>\v<N>\`, not into
  this repository. Artifacts are **single-file HTML** (inline CSS+JS) so they open directly in
  a browser with no build step or server.
- **HTTP-call reference implementations** (both verified present on this machine, both
  production-proven — copy the pattern, don't reinvent it):
  - `D:\Projects\growing-spine\keychain\provider.py` — simplest, pure stdlib (`urllib`).
  - `D:\Projects\apex\adapters\gemini_flash.py` — `aiohttp` version with fuller error handling.

  Pick one approach and stay consistent.
- Target runtime: **Python 3.x on Windows 11** (this machine: Python 3.14, pytest 9). Use
  Windows path conventions.
