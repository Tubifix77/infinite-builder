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
