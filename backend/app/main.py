from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.contests import router as contests_router

app = FastAPI(title="Codeforces Contests API", version="0.2.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def configure_routes() -> None:
    app.include_router(contests_router)


configure_routes()
