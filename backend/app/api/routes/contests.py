from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from app.dependencies.auth import parse_auth
from app.models.contest import AuthParams, Contest
from app.services.codeforces import CodeforcesService

router = APIRouter(prefix="/contests", tags=["contests"])
service = CodeforcesService()


@router.get("", response_model=List[Contest])
async def list_contests(auth: AuthParams | None = Depends(parse_auth)) -> List[Contest]:
    return await service.get_upcoming_contests(auth)
