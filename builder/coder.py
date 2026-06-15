from builder.validator import validate

_BUILD_SYSTEM = (
    "You are an expert web developer. Respond ONLY with the complete HTML code, "
    "nothing else. No markdown. No explanation. Start with <!DOCTYPE html>. "
    "Build a fully functional, interactive single-file HTML app with inline CSS and JS."
)

_IMPROVE_SYSTEM = (
    "You are an expert web developer improving an existing app. "
    "Respond ONLY with the complete improved HTML code, nothing else. "
    "No markdown. No explanation. Start with <!DOCTYPE html>."
)

_MAX_RETRIES = 3


async def build_mvp(keychain, plan: dict) -> str:
    prompt = (
        f"Build a complete single-file HTML app for: {plan.get('title', 'App')}\n"
        f"Description: {plan.get('description', '')}\n"
        f"Features: {', '.join(plan.get('core_features', []))}\n"
        f"Visual direction: {plan.get('visual_direction', 'clean, modern')}"
    )
    for _ in range(_MAX_RETRIES):
        code = await keychain.complete(prompt, system=_BUILD_SYSTEM)
        ok, _ = validate(code)
        if ok:
            return code
    return code


async def improve(keychain, current_code: str, inspiration: list[str], iteration: int) -> str:
    inspo = "\n".join(f"- {s}" for s in inspiration)
    prompt = (
        f"Iteration {iteration}: improve this app based on the following inspiration.\n\n"
        f"Inspiration:\n{inspo}\n\n"
        f"Current code:\n{current_code}"
    )
    for _ in range(_MAX_RETRIES):
        code = await keychain.complete(prompt, system=_IMPROVE_SYSTEM)
        ok, _ = validate(code)
        if ok:
            return code
    return code
