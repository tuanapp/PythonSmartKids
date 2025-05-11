from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
import os
import sys

# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Import and configure the database URL
from app.config import DATABASE_URL, DATABASE_PROVIDER, SUPABASE_URL, SUPABASE_KEY, POSTGRES_CONNECTION_STRING

# Configure the database URL based on the provider
if DATABASE_PROVIDER == 'supabase' and POSTGRES_CONNECTION_STRING:
    # If direct Postgres connection string is available, use it for migrations
    config.set_main_option('sqlalchemy.url', POSTGRES_CONNECTION_STRING)
elif DATABASE_PROVIDER == 'supabase':
    from postgrest import APIResponse
    from supabase import create_client
    import urllib.parse
    
    # For Supabase without direct connection, use placeholder connection string
    # This will be replaced by custom connection handling in run_migrations_online
    pg_url = f"postgresql://postgres:placeholder@localhost:5432/postgres"
    config.set_main_option('sqlalchemy.url', pg_url)
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

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # For Supabase without direct Postgres connection string
    if DATABASE_PROVIDER == 'supabase' and not POSTGRES_CONNECTION_STRING:
        try:
            from app.db.supabase_provider import execute_supabase_sql
            
            # Initialize Supabase client
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Use a custom implementation to execute the migrations via REST API
            class SupabaseConnection:
                def execute(self, sql, *args, **kwargs):
                    return execute_supabase_sql(supabase, sql)
                
                def commit(self):
                    pass
                
                def close(self):
                    pass
            
            class SupabaseExecutionContext:
                def __init__(self):
                    self.connection = SupabaseConnection()
                
                def begin_transaction(self):
                    return self
                
                def __enter__(self):
                    return self
                
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
                
                def execute(self, sql, *args, **kwargs):
                    return self.connection.execute(sql)
                
                def run_migrations(self):
                    # Each migration will be executed separately via the REST API
                    for migration in context.get_revision_map().iterate_revisions('base', 'head'):
                        context._migrations_fn(migration, context)
            
            # Configure the context with our custom connection
            supabase_context = SupabaseExecutionContext()
            context.configure(
                connection=supabase_context.connection,
                target_metadata=target_metadata,
                version_table="alembic_version",
            )
            
            # Run migrations
            with supabase_context:
                supabase_context.run_migrations()
                
            return
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            # Continue with standard approach as fallback
            
    # Standard SQLAlchemy approach for direct database connections
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()