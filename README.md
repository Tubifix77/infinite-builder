# Infinite Builder ∞

An autonomous LLM goldplating loop. Give it a goal — it builds an MVP, then searches the web for inspiration and improves the app every iteration, forever, saving each version to disk.

**Runs entirely free.** Uses free-tier LLM APIs (Gemini Flash, Groq, Cerebras, Ollama) — no paid tokens.

## What it does

1. Takes a goal: `python main.py "a pomodoro timer"`
2. Builds a working single-file HTML app (MVP)
3. Searches DuckDuckGo for UI/UX inspiration relevant to the goal
4. Uses that inspiration to goldplate the app — better features, better design
5. Saves every version to `D:\Projects\<goal-slug>\v1\`, `v2\`, etc.
6. Loops forever until you press Ctrl+C

## Setup

```bash
pip install -r requirements.txt
```

Add your API keys as plain text files in `D:\AI\`:
- `D:\AI\gemini` — [Google AI Studio](https://aistudio.google.com) (free, 1500 req/day)
- `D:\AI\groq` — [Groq](https://console.groq.com) (free tier)
- `D:\AI\cerebras` — [Cerebras](https://cloud.cerebras.ai) (free tier)

Ollama works automatically if running locally (no key needed).

## Usage

```bash
# Run forever
python main.py "a todo app"

# Run for N iterations then stop
python main.py "a calculator" --max 5

# Custom output directory
python main.py "a weather app" --dir C:\MyProjects
```

## Output

```
D:\Projects\a-todo-app\
  v1\index.html    ← MVP
  v1\meta.json     ← build metadata
  v2\index.html    ← first goldplate (web-inspired)
  v2\meta.json
  ...
  journal.jsonl     ← full run log
```

Open any `index.html` directly in a browser — no server needed.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full TDD build spec (9 phases, test gate after each).

**Key design:** APEX's free-tier keychain + Growing Spine's executive loop pattern. Validator catches bad/truncated LLM output before saving. DuckDuckGo search requires no API key.

## License

MIT
