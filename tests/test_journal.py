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
