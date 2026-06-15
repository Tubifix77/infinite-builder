import pytest
from unittest.mock import AsyncMock
from builder.coder import _strip_fences, _inject, _ensure_marker, INJECT_MARKER

# ---------------------------------------------------------------------------
# planner
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_plan_returns_dict_on_valid_json():
    from builder.planner import plan
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value='{"title":"Test","description":"A test app","core_features":["f1"],"visual_direction":"clean"}')
    result = await plan(fake_kc, "a test app")
    assert isinstance(result, dict)
    assert "core_features" in result
    assert isinstance(result["core_features"], list)

@pytest.mark.asyncio
async def test_plan_fallback_on_bad_json():
    from builder.planner import plan
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="sorry I cannot do that as an AI")
    result = await plan(fake_kc, "a test app")
    assert isinstance(result, dict)
    assert "title" in result
    assert "core_features" in result

# ---------------------------------------------------------------------------
# fence stripping
# ---------------------------------------------------------------------------

def test_strip_fences_html_fence():
    assert _strip_fences("```html\n<html/>\n```") == "<html/>"

def test_strip_fences_uppercase_fence():
    assert _strip_fences("```HTML\n<html/>\n```") == "<html/>"

def test_strip_fences_bare_fence():
    assert _strip_fences("```\n<html/>\n```") == "<html/>"

def test_strip_fences_passthrough():
    assert _strip_fences("<html/>") == "<html/>"

# ---------------------------------------------------------------------------
# inject marker and injection
# ---------------------------------------------------------------------------

def test_ensure_marker_adds_before_body():
    html = "<html><body><p>hi</p></body></html>"
    result = _ensure_marker(html)
    assert INJECT_MARKER in result
    assert result.index(INJECT_MARKER) < result.index("</body>")

def test_ensure_marker_idempotent():
    html = f"<html><body>{INJECT_MARKER}</body></html>"
    assert _ensure_marker(html) == html

def test_inject_before_marker():
    html = f"<html><body><p>hi</p>\n{INJECT_MARKER}\n</body></html>"
    result = _inject("<button>New</button>", html)
    assert "<button>New</button>" in result
    assert INJECT_MARKER in result
    assert result.index("<button>New</button>") < result.index(INJECT_MARKER)

def test_inject_fallback_before_body():
    html = "<html><body><p>hi</p></body></html>"
    result = _inject("<span>x</span>", html)
    assert "<span>x</span>" in result
    assert result.index("<span>x</span>") < result.index("</body>")

# ---------------------------------------------------------------------------
# build_mvp
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_mvp_returns_string():
    from builder.coder import build_mvp
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<!DOCTYPE html><html><head></head><body><script>1</script></body></html>")
    result = await build_mvp(fake_kc, {"title":"T","core_features":["f"],"visual_direction":"v"})
    assert isinstance(result, str)
    assert "html" in result.lower()

@pytest.mark.asyncio
async def test_build_mvp_adds_inject_marker():
    from builder.coder import build_mvp
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<!DOCTYPE html><html><head></head><body><script>1</script></body></html>")
    result = await build_mvp(fake_kc, {"title":"T","core_features":["f"],"visual_direction":"v"})
    assert INJECT_MARKER in result

@pytest.mark.asyncio
async def test_build_mvp_strips_fences():
    from builder.coder import build_mvp
    fenced = "```html\n<!DOCTYPE html><html><head></head><body><script>1</script></body></html>\n```"
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value=fenced)
    result = await build_mvp(fake_kc, {"title":"T","core_features":["f"],"visual_direction":"v"})
    assert not result.startswith("```")
    assert INJECT_MARKER in result

@pytest.mark.asyncio
async def test_coder_retries_on_invalid_html():
    from builder.coder import build_mvp
    call_count = 0
    async def fake_complete(prompt, system=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "oops not html"
        return "<!DOCTYPE html><html><head></head><body><script>ok</script></body></html>"
    fake_kc = AsyncMock()
    fake_kc.complete = fake_complete
    result = await build_mvp(fake_kc, {"title":"T","core_features":["x"],"visual_direction":"y"})
    assert call_count == 2
    assert "html" in result.lower()

# ---------------------------------------------------------------------------
# improve
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_improve_injects_snippet_before_marker():
    from builder.coder import improve
    base = f"<!DOCTYPE html><html><body><p>hi</p>\n{INJECT_MARKER}\n</body></html>"
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<button>Click me</button>")
    result = await improve(fake_kc, base, ["add a button"], 2)
    assert "<button>Click me</button>" in result
    assert INJECT_MARKER in result
    assert result.index("<button>Click me</button>") < result.index(INJECT_MARKER)

@pytest.mark.asyncio
async def test_improve_returns_string():
    from builder.coder import improve
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<div>new feature</div>")
    result = await improve(fake_kc, f"<html><body>{INJECT_MARKER}</body></html>", ["clean UI", "dark mode"], 2)
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_improve_fallback_to_build_mvp_when_no_current_code():
    from builder.coder import improve
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<!DOCTYPE html><html><head></head><body><script>ok</script></body></html>")
    result = await improve(fake_kc, None, ["clean UI"], 2, plan={"title":"T","core_features":["f"],"visual_direction":"v"})
    assert isinstance(result, str)
    assert "html" in result.lower()
