import asyncio
import random
import time
from typing import Awaitable, Callable, Iterable, Optional, TypeVar

T = TypeVar("T")


def retry(
    func: Callable[[], T],
    retries: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    jitter: float = 0.1,
    retry_on: Iterable[type[BaseException]] = (Exception,),
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
) -> T:
    delay = base_delay
    for attempt in range(retries):
        try:
            return func()
        except retry_on as exc:  # type: ignore[misc]
            if attempt == retries - 1:
                raise
            sleep_for = min(delay, max_delay) + random.uniform(0, delay * jitter)
            if on_retry:
                try:
                    on_retry(attempt + 1, exc, sleep_for)
                except Exception:
                    pass
            time.sleep(sleep_for)
            delay = min(delay * 2, max_delay)
            continue
    # Unreachable
    raise RuntimeError("retry exhausted")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    retries: int = 5,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    jitter: float = 0.1,
    retry_on: Iterable[type[BaseException]] = (Exception,),
    on_retry: Optional[
        Callable[[int, BaseException, float], Awaitable[None] | None]
    ] = None,
) -> T:
    delay = base_delay
    for attempt in range(retries):
        try:
            return await func()
        except retry_on as exc:  # type: ignore[misc]
            if attempt == retries - 1:
                raise
            sleep_for = min(delay, max_delay) + random.uniform(0, delay * jitter)
            if on_retry:
                try:
                    result = on_retry(attempt + 1, exc, sleep_for)
                    if result is not None:
                        await result  # support async callback
                except Exception:
                    pass
            await asyncio.sleep(sleep_for)
            delay = min(delay * 2, max_delay)
            continue
    raise RuntimeError("async retry exhausted")
