# Database Migration Guide

This guide explains how to use the Neon PostgreSQL database and manage schema migrations.

## Configuration

The application uses Neon PostgreSQL as the database backend. The configuration is controlled by environment variables:

- `DATABASE_PROVIDER`: Should be set to `neon`
- `DATABASE_URL`: The PostgreSQL connection string
- `NEON_DBNAME`, `NEON_USER`, `NEON_PASSWORD`, `NEON_HOST`, `NEON_SSLMODE`: Neon PostgreSQL connection details

These variables can be set in a `.env` file in the project root directory.

Example `.env` file for Neon PostgreSQL:
```
DATABASE_PROVIDER=neon
DATABASE_URL=postgresql://<user>:<password>@<host>/<dbname>?sslmode=require
NEON_DBNAME=smartboydb
NEON_USER=tuanapp
NEON_PASSWORD=HdzrNIKh5mM1
NEON_HOST=ep-sparkling-butterfly-33773987-pooler.ap-southeast-1.aws.neon.tech
NEON_SSLMODE=require
```

## Initial Setup

Before using Neon PostgreSQL, you need to create the necessary tables. You can do this by running SQL directly in your PostgreSQL client or using Alembic migrations.

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

The application uses a database abstraction layer:

- `app/db/db_interface.py`: Defines the abstract interface for database operations
- `app/db/neon_provider.py`: Neon PostgreSQL implementation
- `app/db/db_factory.py`: Factory for creating the database provider
- `app/repositories/db_service.py`: Repository layer that uses the database provider

This architecture makes it easy to add support for additional database backends in the future.