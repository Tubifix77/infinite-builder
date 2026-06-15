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


def _extract_integration_map(code: str) -> dict:
    """Find the key JS identifiers in the existing app so snippets can hook in."""
    # Main state array: let/const/var name = []
    array_match = re.search(r"(?:let|const|var)\s+(\w+)\s*=\s*\[\]", code)
    array_name = array_match.group(1) if array_match else None

    # Render function: function renderXxx() or const renderXxx = (function|arrow)
    render_match = re.search(
        r"function\s+((?:render|display|show|update)\w*)\s*\(", code, re.IGNORECASE
    )
    if not render_match:
        render_match = re.search(
            r"(?:const|let|var)\s+((?:render|display|show|update)\w*)\s*=\s*(?:function|\()",
            code, re.IGNORECASE,
        )
    render_name = render_match.group(1) if render_match else None

    # Add / delete function names
    add_fns = re.findall(
        r"function\s+((?:add|create|new)\w*)\s*\(", code, re.IGNORECASE
    )
    delete_fns = re.findall(
        r"function\s+((?:delete|remove|destroy)\w*)\s*\(", code, re.IGNORECASE
    )

    return {
        "array": array_name,
        "render": render_name,
        "add_fns": add_fns,
        "delete_fns": delete_fns,
    }


def _integration_hint(imap: dict) -> str:
    if not imap["array"] and not imap["render"]:
        return ""
    parts = []
    if imap["array"] and imap["render"]:
        parts.append(
            f"The existing app stores todos in {imap['array']}[] and renders with "
            f"{imap['render']}(). Your snippet MUST use these — do not create new "
            f"parallel state or a separate array."
        )
    elif imap["array"]:
        parts.append(
            f"The existing app stores todos in {imap['array']}[]. "
            f"Your snippet MUST use this — do not create a separate array."
        )
    elif imap["render"]:
        parts.append(
            f"The existing app renders with {imap['render']}(). "
            f"Call it after any state change."
        )
    if imap["add_fns"]:
        parts.append(f"Existing add function(s): {', '.join(imap['add_fns'])}().")
    if imap["delete_fns"]:
        parts.append(f"Existing delete function(s): {', '.join(imap['delete_fns'])}().")
    return "\n".join(parts)


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
    imap = _extract_integration_map(current_code)
    hint = _integration_hint(imap)

    prompt = (
        f"Add one new feature to this app inspired by:\n"
        f"  {top}\n\n"
        + (f"Integration context:\n{hint}\n\n" if hint else "")
        + "Write ONLY the new code snippet, not the whole app. "
        "It will be injected into an existing HTML page."
    )
    for _ in range(_MAX_RETRIES):
        snippet = _strip_fences(await keychain.complete(prompt, system=_SNIPPET_SYSTEM))
        if snippet:
            return _inject(snippet, current_code)
    return current_code
