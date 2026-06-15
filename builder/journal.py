import json
import time


class Journal:
    def __init__(self, path: str):
        self.path = path
        open(path, "a").close()

    def append(self, kind: str, content: str, meta: dict = None):
        entry = {"ts": time.time(), "kind": kind, "content": content, "meta": meta}
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def all(self) -> list[dict]:
        with open(self.path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def recent(self, n: int = 20) -> list[dict]:
        return self.all()[-n:]
