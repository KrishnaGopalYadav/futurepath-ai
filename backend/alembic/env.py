from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Keep Alembic independent from the application import graph. This is
# important during container startup: migrations must be able to run even if
# an application module is not importable yet.
database_url = os.getenv(
    "DATABASE_URL",
    config.get_main_option("sqlalchemy.url"),
)
if not database_url:
    raise RuntimeError("DATABASE_URL or sqlalchemy.url must be configured for Alembic")

config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# The current R1 migrations are explicit schema migrations and do not require
# application model metadata to execute. Keeping target_metadata unset also
# prevents Alembic startup from depending on the runtime app import graph.
target_metadata = None


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
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
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
