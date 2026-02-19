"""
Alembic environment configuration.

This file tells Alembic how to connect to the database and which models to track.

Key points:
  1. We import ALL models via `app.models` so Alembic can detect every table.
     If you add a new model file, import it in app/models/__init__.py.
  2. Database URL comes from our Settings class (same .env as the app).
     Never hardcode credentials here.
  3. We use 'offline' mode for generating SQL scripts and 'online' mode
     for applying migrations directly to the DB.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os, sys

# Make sure the project root is on the Python path
# so `from app.xxx import yyy` works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import settings to get the database URL
from app.config import settings

# Import Base AND all models (the import triggers SQLAlchemy to register them)
from app.database import Base
import app.models  # noqa: F401 — side-effect import to register all models

# Alembic Config object — provides access to values in alembic.ini
config = context.config

# Override the sqlalchemy.url from alembic.ini with our real DB URL from .env
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up loggers as defined in alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The MetaData object for all tables — Alembic uses this for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL script without connecting to the DB.
    Useful for reviewing migrations before applying them.

    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare server defaults so Alembic detects server_default changes
        compare_server_default=True,
        # Compare type changes (e.g., String(50) → String(100))
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Connects directly to the database and applies migrations.

    Usage: alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool: no connection pooling in migration scripts
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
