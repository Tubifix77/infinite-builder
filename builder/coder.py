import re
from builder.validator import validate

_BUILD_SYSTEM = (
    "You are an expert web developer. Respond ONLY with the complete HTML code, "
    "nothing else. No markdown. No explanation. Start with <!DOCTYPE html>. "
    "Build a fully functional, interactive single-file HTML app with inline CSS and JS."
)

_SNIPPET_SYSTEM = (
    "You are an expert web developer adding a single feature to an existing app. "
    "Write ONLY the new code snippet, not the whole app. "
    "Output one self-contained addition: a single new feature, JS function, or UI block. "
    "No markdown fences. No explanation. No <!DOCTYPE html>. Just the raw HTML/JS/CSS snippet."
)

_MAX_RETRIES = 3
INJECT_MARKER = "<!-- IB_INJECT -->"


def _strip_fences(code: str) -> str:
    code = code.strip()
    code = re.sub(r"^```[a-zA-Z]*\n?", "", code)
    code = re.sub(r"\n?```\s*$", "", code)
    return code.strip()


def _ensure_marker(code: str) -> str:
    if INJECT_MARKER in code:
        return code
    return re.sub(r"(</body>)", INJECT_MARKER + "\n" + r"\1", code, flags=re.IGNORECASE)


def _inject(snippet: str, current_code: str) -> str:
    if INJECT_MARKER in current_code:
        return current_code.replace(INJECT_MARKER, snippet + "\n" + INJECT_MARKER, 1)
    return re.sub(r"(</body>)", snippet + "\n" + r"\1", current_code, flags=re.IGNORECASE)


async def build_mvp(keychain, plan: dict) -> str:
    prompt = (
        f"Build a complete single-file HTML app for: {plan.get('title', 'App')}\n"
        f"Description: {plan.get('description', '')}\n"
        f"Features: {', '.join(plan.get('core_features', []))}\n"
        f"Visual direction: {plan.get('visual_direction', 'clean, modern')}"
    )
    code = ""
    for _ in range(_MAX_RETRIES):
        code = _strip_fences(await keychain.complete(prompt, system=_BUILD_SYSTEM))
        ok, _ = validate(code)
        if ok:
            return _ensure_marker(code)
    return _ensure_marker(code)


async def improve(keychain, current_code: str, inspiration: list[str], iteration: int, plan: dict = None) -> str:
    if current_code is None:
        if plan is not None:
            return await build_mvp(keychain, plan)
        raise ValueError("current_code is None and no plan provided for fallback")

    top = inspiration[0] if inspiration else "add a useful interactive feature"
    prompt = (
        f"Add one new feature to this app inspired by:\n"
        f"  {top}\n\n"
        f"Write ONLY the new code snippet, not the whole app. "
        f"It will be injected into an existing HTML page."
    )
    for _ in range(_MAX_RETRIES):
        snippet = _strip_fences(await keychain.complete(prompt, system=_SNIPPET_SYSTEM))
        if snippet:
            return _inject(snippet, current_code)
    return current_code
