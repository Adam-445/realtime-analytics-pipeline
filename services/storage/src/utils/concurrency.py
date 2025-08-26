import asyncio
from typing import Callable, TypeVar

T = TypeVar("T")


async def run_blocking(func: Callable[..., T], *args, **kwargs) -> T:
    """Run blocking function in default executor.

    Central helper to reduce scattered asyncio.to_thread calls and make future
    switching to a custom ThreadPool simpler.
    """
    return await asyncio.to_thread(func, *args, **kwargs)
