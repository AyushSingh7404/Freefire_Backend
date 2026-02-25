"""
Application entry point.

Run locally:
    uvicorn app.main:app --reload --port 8000

In Docker:
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

API docs available at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.rate_limiter import limiter
from app.routers import auth, users, leagues, rooms, wallet, leaderboard, matches, admin, websocket, coin_packages


def create_app() -> FastAPI:
    app = FastAPI(
        title="FreeFire Esports API",
        description=(
            "Backend for a Free Fire fantasy esports platform. "
            "Supports leagues, rooms, wallets, leaderboards, real-time WebSocket updates, "
            "Razorpay payments, and a full admin panel."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        # Disable docs in production by setting these to None via env
        # docs_url=None if settings.environment == "production" else "/docs",
    )

    # ── Rate Limiter ──────────────────────────────────────────────────────────
    # Attach limiter to app state (required by slowapi)
    # Register the 429 handler so exceeded limits return proper JSON
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In production, CORS_ORIGINS in .env should only list your frontend domain
    # e.g., CORS_ORIGINS=https://yourdomain.com
    # During dev it can be http://localhost:4200 (Angular dev server)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    # Order doesn't affect routing but keeping them grouped by domain is clean.

    # Auth (public — no auth dependency inside the router itself)
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])

    # User profile management
    app.include_router(users.router, prefix="/users", tags=["Users"])

    # Leagues and rooms
    app.include_router(leagues.router, prefix="/leagues", tags=["Leagues"])
    app.include_router(rooms.router, prefix="/rooms", tags=["Rooms"])

    # Wallet & payments
    app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])

    # Coin packages — public pricing endpoint (no auth required)
    app.include_router(coin_packages.router, prefix="/coin-packages", tags=["Coin Packages"])

    # Leaderboard
    app.include_router(leaderboard.router, prefix="/leaderboard", tags=["Leaderboard"])

    # Match history
    app.include_router(matches.router, prefix="/matches", tags=["Matches"])

    # Admin panel (all endpoints gated by get_current_admin dependency inside the router)
    app.include_router(admin.router, prefix="/admin", tags=["Admin"])

    # WebSocket (no prefix — ws:// connections use the full path /ws/rooms/{id})
    app.include_router(websocket.router, tags=["WebSocket"])

    # ── Health Check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    def health_check():
        """
        Simple health check endpoint for load balancers and Docker health checks.
        Returns 200 if the application is running.
        """
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
