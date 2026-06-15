def validate(code: str) -> tuple[bool, str]:
    if len(code) <= 50:
        return False, "too short"
    if "<html" not in code.lower():
        return False, "missing <html"
    if "</html>" not in code.lower():
        return False, "truncated: missing </html>"
    if "<script" not in code.lower():
        return False, "no <script block — app must have JavaScript"
    first200 = code[:200].lower()
    for marker in ("i cannot", "i'm sorry", "as an ai"):
        if marker in first200:
            return False, f"LLM refusal detected: '{marker}'"
    return True, "ok"
