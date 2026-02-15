from __future__ import annotations

import hashlib
import random
import string
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import HTTPException

from app.core.config import CACHE_TTL_SECONDS, CODEFORCES_API_BASE, HTTP_TIMEOUT_SECONDS
from app.models.contest import AuthParams, Contest
from app.services.cache import TTLCache


def _sign_request(method: str, params: Dict[str, Any], api_secret: str) -> str:
    rand = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
    params_items = sorted(params.items(), key=lambda item: (str(item[0]), str(item[1])))
    query = "&".join(f"{k}={v}" for k, v in params_items)
    base = f"{rand}/{method}?{query}#{api_secret}"
    signature = hashlib.sha512(base.encode()).hexdigest()
    return f"{rand}{signature}"


class CodeforcesService:
    def __init__(self) -> None:
        self._base_url = CODEFORCES_API_BASE.rstrip("/")
        self._timeout = HTTP_TIMEOUT_SECONDS
        self._cache = TTLCache[List[Contest]](CACHE_TTL_SECONDS)

    async def get_upcoming_contests(self, auth: AuthParams | None) -> List[Contest]:
        if auth:
            return await self._fetch_upcoming_contests(auth)
        return await self._cache.get(lambda: self._fetch_upcoming_contests(auth=None))

    async def _fetch_upcoming_contests(self, auth: AuthParams | None) -> List[Contest]:
        method = "contest.list"
        params: Dict[str, Any] = {"gym": "false"}

        if auth:
            now_ts = int(datetime.now(timezone.utc).timestamp())
            params.update({"apiKey": auth.api_key, "time": now_ts})
            params["apiSig"] = _sign_request(method, params, auth.api_secret)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/{method}", params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Codeforces API error: {exc}") from exc

        payload: Dict[str, Any] = response.json()
        if payload.get("status") != "OK":
            comment = payload.get("comment", "Codeforces API returned non-OK status")
            raise HTTPException(status_code=502, detail=comment)

        contests_raw = payload.get("result", [])
        upcoming: List[Contest] = []
        now = datetime.now(timezone.utc)

        for contest in contests_raw:
            phase = contest.get("phase")
            if phase != "BEFORE":
                continue

            start_seconds = contest.get("startTimeSeconds")
            duration_seconds = contest.get("durationSeconds")
            start_time = datetime.fromtimestamp(start_seconds, tz=timezone.utc) if start_seconds else None
            relative_time_seconds = contest.get("relativeTimeSeconds")

            if start_time and start_time < now:
                continue

            upcoming.append(
                Contest(
                    id=contest.get("id"),
                    name=contest.get("name", ""),
                    phase=phase,
                    start_time_utc=start_time,
                    duration_seconds=duration_seconds,
                    relative_time_seconds=relative_time_seconds,
                )
            )

        upcoming.sort(key=lambda c: c.start_time_utc or datetime.max.replace(tzinfo=timezone.utc))
        return upcoming
