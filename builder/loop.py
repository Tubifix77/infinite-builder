import asyncio
import os
import time

from builder.keychain import Keychain
from builder.journal import Journal
from builder.saver import Saver
from builder.searcher import Searcher, inspiration_query
from builder.planner import plan
from builder.coder import build_mvp, improve
from builder.validator import validate


def _make_keychain(use_ollama: bool = False) -> Keychain:
    return Keychain(use_ollama=use_ollama)


async def run(goal: str, output_dir: str = r"D:\Projects", max_iterations: int = None, use_ollama: bool = False):
    kc = _make_keychain(use_ollama=use_ollama)
    saver = Saver(base_dir=output_dir, goal=goal)
    searcher = Searcher()
    os.makedirs(saver.project_dir, exist_ok=True)
    journal = Journal(os.path.join(saver.project_dir, "journal.jsonl"))

    journal.append("start", goal, {"goal": goal, "output_dir": output_dir})

    current_code = None
    iteration = 0
    start_time = time.time()

    try:
        while max_iterations is None or iteration < max_iterations:
            iteration += 1
            kc.reset_if_new_day()
            iter_start = time.time()

            if iteration == 1:
                print(f"[v{iteration}] planning...")
                build_plan = await plan(kc, goal)
                journal.append("plan", str(build_plan))

                print(f"[v{iteration}] building MVP...")
                code = None
                for attempt in range(3):
                    try:
                        code = await build_mvp(kc, build_plan)
                        ok, reason = validate(code)
                        if ok:
                            break
                        journal.append("error", f"invalid HTML attempt {attempt+1}: {reason}")
                    except RuntimeError as e:
                        if "exhausted" in str(e):
                            journal.append("quota_sleep", "all providers exhausted, sleeping 120s")
                            print("[quota] all providers exhausted — sleeping 2 min")
                            await asyncio.sleep(120)
                            kc.reset_if_new_day()
                        else:
                            raise
                if code is None or not validate(code)[0]:
                    journal.append("error", "failed to build MVP after 3 attempts, skipping")
                    continue
            else:
                query = inspiration_query(goal, iteration)
                print(f"[v{iteration}] searching for inspiration...")
                inspiration = searcher.search(query)
                journal.append("search", query, {"results": inspiration})

                print(f"[v{iteration}] improving...")
                code = None
                for attempt in range(3):
                    try:
                        code = await improve(kc, current_code, inspiration, iteration)
                        ok, reason = validate(code)
                        if ok:
                            break
                        journal.append("error", f"invalid HTML attempt {attempt+1}: {reason}")
                    except RuntimeError as e:
                        if "exhausted" in str(e):
                            journal.append("quota_sleep", "all providers exhausted, sleeping 120s")
                            print("[quota] all providers exhausted — sleeping 2 min")
                            await asyncio.sleep(120)
                            kc.reset_if_new_day()
                        else:
                            raise
                if code is None or not validate(code)[0]:
                    journal.append("error", "failed to improve after 3 attempts, keeping previous")
                    code = current_code

            iter_time = time.time() - iter_start
            provider = "unknown"
            meta = {
                "provider": provider,
                "inspiration_query": inspiration_query(goal, iteration) if iteration > 1 else None,
                "improvements": [],
                "iteration_time_s": round(iter_time, 2),
            }
            path = saver.save(code, meta)
            current_code = code
            journal.append("save", path, {"version": iteration})
            print(f"[v{iteration}] ✓ saved to {path}")

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        journal.append("stopped", "stopped by user", {"elapsed_s": round(elapsed, 1)})
        versions = iteration if current_code else iteration - 1
        print(f"\n[stopped] {versions} version(s) saved in {elapsed:.0f}s")
