"""
Alembic environment configuration for FreeFire Esports backend.

What this file does:
  1. Pulls the real database URL from our Settings class (reads .env)
     so credentials are never hardcoded here.
  2. Imports ALL SQLAlchemy models so Alembic knows every table.
     If you add a new model file, import it in app/models/__init__.py
     and it will automatically be picked up here.
  3. Sets compare_type=True so Alembic detects column type changes
     (e.g. String(50) -> String(100)).
  4. Sets compare_server_default=True so Alembic detects changes to
     server-side defaults (e.g. server_default=text('now()')).

Running migrations:
  Generate:  alembic revision --autogenerate -m "describe_change"
  Apply:     alembic upgrade head
  Rollback:  alembic downgrade -1
  History:   alembic history --verbose
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Path setup ────────────────────────────────────────────────────────────────
# Ensure the project root (where the `app` package lives) is on sys.path.
# This makes `from app.xxx import yyy` work when Alembic runs from any directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Import Settings and override the DB URL ───────────────────────────────────
# Must happen BEFORE context.config is used for the URL.
from app.config import settings

# ── Import Base and ALL models ────────────────────────────────────────────────
# Importing Base gives us the MetaData object that tracks all tables.
# Importing app.models triggers the __init__.py which imports every model class,
# registering them all with Base.metadata. Without this, autogenerate sees nothing.
from app.database import Base
import app.models  # noqa: F401 — side-effect import, registers all ORM models

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url from alembic.ini with the real URL from .env.
# This means credentials live only in .env and are never committed.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up Python logging as defined in alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The MetaData that Alembic uses for autogenerate comparison
target_metadata = Base.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL without connecting to DB.
    Useful for reviewing what SQL will be executed before running it.

    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ───────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to the DB and applies migrations.

    Usage: alembic upgrade head

    NullPool is used here intentionally: migration scripts should open and
    close their own connection cleanly, not borrow from the app's connection pool.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
