import json
import os
import re
from datetime import datetime, timezone


def slug(goal: str) -> str:
    s = goal.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:40]


class Saver:
    def __init__(self, base_dir: str = r"D:\Projects", goal: str = ""):
        self.base_dir = base_dir
        self.goal = goal
        self.slug = slug(goal)
        self.project_dir = os.path.join(base_dir, self.slug)

    def next_version(self) -> int:
        if not os.path.exists(self.project_dir):
            return 1
        existing = [
            d for d in os.listdir(self.project_dir)
            if re.fullmatch(r"v\d+", d) and os.path.isdir(os.path.join(self.project_dir, d))
        ]
        if not existing:
            return 1
        return max(int(d[1:]) for d in existing) + 1

    def save(self, code: str, meta: dict) -> str:
        version = self.next_version()
        version_dir = os.path.join(self.project_dir, f"v{version}")
        os.makedirs(version_dir, exist_ok=True)

        with open(os.path.join(version_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(code)

        full_meta = {
            "version": version,
            "goal": self.goal,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            **meta,
        }
        with open(os.path.join(version_dir, "meta.json"), "w") as f:
            json.dump(full_meta, f, indent=2)

        return version_dir
