from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._data: Optional[T] = None
        self._fetched_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def get(self, loader: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self._data is not None and self._fetched_at is not None:
                age = (datetime.now(timezone.utc) - self._fetched_at).total_seconds()
                if age < self._ttl_seconds:
                    return self._data

            self._data = await loader()
            self._fetched_at = datetime.now(timezone.utc)
            return self._data
