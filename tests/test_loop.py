import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import contextmanager

@contextmanager
def patch_makers(loop_mod, fake_kc):
    with patch.object(loop_mod, "_make_keychain", return_value=fake_kc):
        yield

@pytest.mark.asyncio
async def test_loop_runs_one_iteration(tmp_path):
    from builder import loop as loop_mod
    fake_kc = AsyncMock()
    fake_kc.complete = AsyncMock(side_effect=[
        '{"title":"T","description":"d","core_features":["f"],"visual_direction":"v"}',
        "<!DOCTYPE html><html><head></head><body><script>1</script></body></html>",
    ])
    fake_kc.reset_if_new_day = MagicMock()
    with patch_makers(loop_mod, fake_kc):
        await loop_mod.run(goal="test app", output_dir=str(tmp_path), max_iterations=1)
    v1 = tmp_path / "test-app" / "v1"
    assert v1.exists()
    assert (v1 / "index.html").exists()

@pytest.mark.asyncio
async def test_loop_retries_on_invalid_html(tmp_path):
    from builder import loop as loop_mod
    call_count = 0
    async def fake_complete(prompt, system=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '{"title":"T","description":"d","core_features":["f"],"visual_direction":"v"}'
        if call_count in (2, 3):
            return "bad output"
        return "<!DOCTYPE html><html><head></head><body><script>1</script></body></html>"
    fake_kc = AsyncMock()
    fake_kc.complete = fake_complete
    fake_kc.reset_if_new_day = MagicMock()
    with patch_makers(loop_mod, fake_kc):
        await loop_mod.run(goal="test app", output_dir=str(tmp_path), max_iterations=1)
    assert (tmp_path / "test-app" / "v1" / "index.html").exists()
