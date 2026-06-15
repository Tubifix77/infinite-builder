import json

_SYSTEM = (
    "You are a software planner. Respond ONLY with valid JSON, no markdown fences, "
    "no explanation. Output a single JSON object with keys: title, description, "
    "core_features (list of strings), visual_direction (string)."
)

_FALLBACK = {
    "title": "App",
    "description": "A web application",
    "core_features": ["core functionality"],
    "visual_direction": "clean, modern",
}


async def plan(keychain, goal: str) -> dict:
    prompt = f"Decompose this goal into a build plan: {goal}"
    raw = await keychain.complete(prompt, system=_SYSTEM)
    try:
        result = json.loads(raw)
        if not isinstance(result.get("core_features"), list):
            raise ValueError
        return result
    except Exception:
        fallback = dict(_FALLBACK)
        fallback["title"] = goal.title()
        fallback["description"] = f"A {goal}"
        return fallback
