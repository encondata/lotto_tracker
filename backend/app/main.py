from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, invites, results, tickets


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Lottery Tracker API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(invites.router)
    app.include_router(tickets.router)
    app.include_router(results.router)

    return app


app = create_app()
