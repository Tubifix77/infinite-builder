"""
Integration test — requires Ollama running at localhost:11434 with gemma3:12b.
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
    slug_dirs = [d for d in os.listdir(tmp_path) if os.path.isdir(os.path.join(tmp_path, d))]
    assert len(slug_dirs) == 1
    v1 = os.path.join(tmp_path, slug_dirs[0], "v1")
    assert os.path.exists(os.path.join(v1, "index.html"))
    assert os.path.exists(os.path.join(v1, "meta.json"))
    html = open(os.path.join(v1, "index.html")).read()
    assert "<html" in html.lower()
    assert os.path.exists(os.path.join(tmp_path, slug_dirs[0], "journal.jsonl"))
