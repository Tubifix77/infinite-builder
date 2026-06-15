import pytest
from unittest.mock import AsyncMock

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

@pytest.mark.asyncio
async def test_build_mvp_returns_string():
    from builder.coder import build_mvp
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<!DOCTYPE html><html><head></head><body><script>1</script></body></html>")
    result = await build_mvp(fake_kc, {"title":"T","core_features":["f"],"visual_direction":"v"})
    assert isinstance(result, str)
    assert "html" in result.lower()

@pytest.mark.asyncio
async def test_improve_returns_string():
    from builder.coder import improve
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(return_value="<!DOCTYPE html><html><head></head><body><script>2</script></body></html>")
    result = await improve(fake_kc, "<html/>", ["clean UI", "dark mode"], 2)
    assert isinstance(result, str)

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
