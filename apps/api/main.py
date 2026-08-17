from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import checkpoints, runs, stream, tasks
from apps.api.settings import settings

app = FastAPI(title="Browser Automation Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(runs.router)
app.include_router(checkpoints.router)
app.include_router(stream.router)


@app.on_event("startup")
async def on_startup() -> None:
    # Best-effort connectivity check; must never crash app boot if DB is unreachable.
    try:
        from packages.db.session import engine

        async with engine.connect():
            pass
    except Exception:
        pass


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
