# Database Migration Guide

This guide explains how to switch between SQLite and Supabase databases, and how to migrate data between them.

## Configuration

The application can use either SQLite or Supabase as the database backend. The choice is controlled by environment variables:

- `DATABASE_PROVIDER`: Set to either `sqlite` or `supabase`
- `DATABASE_URL`: The SQLite connection string (e.g., `sqlite:///math_attempts.db`)
- `SUPABASE_URL`: The Supabase project URL
- `SUPABASE_KEY`: The Supabase API key

These variables can be set in a `.env` file in the project root directory.

Example `.env` file for SQLite:
```
DATABASE_PROVIDER=sqlite
DATABASE_URL=sqlite:///math_attempts.db
```

Example `.env` file for Supabase:
```
DATABASE_PROVIDER=supabase
SUPABASE_URL=https://apifyzsbctxzfwrqkcqb.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFwaWZ5enNiY3R4emZ3cnFrY3FiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY4NzMyNTEsImV4cCI6MjA2MjQ0OTI1MX0.teB3iEL-cAozLxZOyPVMOB7JHOIba7eMTRbUMXAeL0A
```

## Initial Setup

### For Supabase

Before using Supabase, you need to create the necessary tables. You can do this by running SQL directly in the Supabase SQL Editor:

```sql
CREATE TABLE attempts (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    datetime TIMESTAMP NOT NULL,
    question TEXT NOT NULL,
    is_answer_correct BOOLEAN NOT NULL,
    incorrect_answer TEXT,
    correct_answer TEXT NOT NULL
);

-- Set up basic Row Level Security (RLS) policies
ALTER TABLE attempts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anonymous select" ON attempts FOR SELECT USING (true);
CREATE POLICY "Allow anonymous insert" ON attempts FOR INSERT USING (true);
```

## Migrating Data

### SQLite to Supabase

To migrate data from SQLite to Supabase:

1. Ensure both database configurations are set correctly in your environment variables or `.env` file.
2. Run the migration script:

```
python -m app.db.data_migration to_supabase
```

### Supabase to SQLite

To migrate data from Supabase back to SQLite:

1. Ensure both database configurations are set correctly in your environment variables or `.env` file.
2. Run the migration script:

```
python -m app.db.data_migration to_sqlite
```

## Database Schema Management

Database schema is managed using Alembic migrations. The migration files are stored in the `migrations` directory.

### Running Migrations

To apply migrations to your database:

```
alembic upgrade head
```

### Creating New Migrations

If you need to modify the database schema, create a new migration:

```
alembic revision -m "description_of_changes"
```

Then edit the generated file in `migrations/versions/` to define the schema changes.

## Architecture

The application uses a database abstraction layer that allows it to switch between different database backends:

- `app/db/db_interface.py`: Defines the abstract interface for database operations
- `app/db/sqlite_provider.py`: SQLite implementation
- `app/db/supabase_provider.py`: Supabase implementation
- `app/db/db_factory.py`: Factory for creating the appropriate database provider
- `app/repositories/db_service.py`: Repository layer that uses the database provider

This architecture makes it easy to add support for additional database backends in the future.