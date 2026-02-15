from __future__ import annotations

from fastapi import HTTPException, Query

from app.models.contest import AuthParams


def parse_auth(
    api_key: str | None = Query(None, alias="apiKey"),
    api_secret: str | None = Query(None, alias="apiSecret"),
) -> AuthParams | None:
    if api_key or api_secret:
        if not (api_key and api_secret):
            raise HTTPException(
                status_code=400,
                detail="Both apiKey and apiSecret are required when supplying credentials",
            )
        return AuthParams(api_key=api_key, api_secret=api_secret)
    return None
