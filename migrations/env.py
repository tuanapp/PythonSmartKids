from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import os
import sys
import logging

# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Import and configure the database URL
from app.config import DATABASE_URL, DATABASE_PROVIDER, NEON_DBNAME, NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_SSLMODE

# Configure the database URL based on the provider
if DATABASE_PROVIDER == 'neon':
    # Create PostgreSQL connection string for Neon
    neon_url = f"postgresql://{NEON_USER}:{NEON_PASSWORD}@{NEON_HOST}/{NEON_DBNAME}?sslmode={NEON_SSLMODE}"
    config.set_main_option('sqlalchemy.url', neon_url)
else:
    # For SQLite or other direct database connections
    config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the metadata from the models
from app.db.models import Base
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Get the connection URL from config
    configuration = config.get_section(config.config_ini_section)
    
    # For debugging connection issues
    url = configuration.get('sqlalchemy.url')
    logging.info(f"Using database URL: {url}")
    
    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version",
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()