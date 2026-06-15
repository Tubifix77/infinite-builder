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
    opens = code.count("<")
    closes = code.count(">")
    if opens == 0 or abs(opens - closes) / opens > 0.05:
        return False, f"unbalanced tags: {opens} '<' vs {closes} '>'"
    return True, "ok"
