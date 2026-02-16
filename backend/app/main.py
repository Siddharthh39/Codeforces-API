from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.contests import router as contests_router
from app.api.routes.users import router as users_router
from app.core.database import init_db

app = FastAPI(title="Codeforces Contests API", version="0.2.0")


def configure_cors() -> None:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def configure_routes() -> None:
    app.include_router(contests_router)
    app.include_router(users_router)


configure_routes()
configure_cors()


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
