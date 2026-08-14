import pytest
from app.utils.retry import async_retry_with_backoff


async def test_retries_then_succeeds() -> None:
    attempts = 0

    @async_retry_with_backoff(max_attempts=3, base_delay_seconds=0.0)
    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("transient")
        return "ok"

    assert await flaky() == "ok"
    assert attempts == 3


async def test_raises_after_exhausting_attempts() -> None:
    attempts = 0

    @async_retry_with_backoff(max_attempts=2, base_delay_seconds=0.0)
    async def always_fails() -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        await always_fails()
    assert attempts == 2
