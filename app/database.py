from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


# ── Engine ────────────────────────────────────────────────────────────────────
# pool_pre_ping=True: SQLAlchemy will test every connection before using it.
# This prevents "connection reset" errors after Postgres restarts or idle timeouts.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,        # number of persistent connections in pool
    max_overflow=20,     # extra connections allowed beyond pool_size under load
)

# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,   # we manage commits explicitly — critical for atomic ops
    autoflush=False,    # don't auto-flush; we control when SQL is sent to DB
    bind=engine,
)


# ── Declarative Base ──────────────────────────────────────────────────────────
# SQLAlchemy 2.0 style — all models inherit from this.
class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────────────────────
def get_db():
    """
    FastAPI dependency that yields a DB session and guarantees cleanup.
    Use as: db: Session = Depends(get_db)
    The session is closed even if an exception is raised inside the endpoint.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
