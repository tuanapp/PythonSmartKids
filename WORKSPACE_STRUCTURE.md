# PythonSmartKids Workspace Structure

*Documentation created on May 13, 2025*

This document provides an overview of the PythonSmartKids project workspace structure.

## Root Directory

The root directory contains the following files:

- `create_api_table.py` - Python script for API table creation
- `create_api_table.sql` - SQL script for API table creation
- `create_table.sql` - SQL script for table creation
- `DATABASE_README.md` - Documentation for database setup
- `Dockerfile` - Container definition for the application
- `execute_sql.py` - Python script for SQL execution
- `image.png` - Project image
- `privacy-policy.html` - Privacy policy HTML
- `privacy-policy.md` - Privacy policy markdown
- `pytest.ini` - PyTest configuration
- `PythonSmartKids.code-workspace` - VS Code workspace configuration
- `pyvenv.cfg` - Python virtual environment configuration
- `README.md` - Main project documentation
- `requirements.txt` - Python dependencies
- `server.py` - Main server script
- `setup_neon_schema.py` - Script to set up Neon database schema
- `VERCEL_DEPLOYMENT.md` - Vercel deployment documentation
- `vercel.json` - Vercel configuration file

## Application Structure

The `app` directory contains the core application code:

- `config.py` - Application configuration settings
- `main.py` - Main application entry point

### API

The `app/api` directory contains API-related code:

- `routes.py` - API route definitions

### Database

The `app/db` directory contains database-related code:

- `__init__.py` - Package initialization
- `db_factory.py` - Factory pattern for database connections
- `db_init.py` - Database initialization
- `db_interface.py` - Database interface definitions
- `models.py` - Database models
- `neon_provider.py` - Neon database provider implementation

### Models

The `app/models` directory contains data models:

- `schemas.py` - Schema definitions

### Repositories

The `app/repositories` directory contains repository pattern implementations:

- `db_service.py` - Database service implementation

### Services

The `app/services` directory contains service implementations:

- `ai_service.py` - AI service implementation

### Tests

The `app/tests` directory contains test suites:

- `api/` - API tests
- `db/` - Database tests
- `integration/` - Integration tests
- `real/` - Real-world API call tests
- `unit/` - Unit tests

### Utils

The `app/utils` directory contains utility functionality:

- `logger.py` - Logging utility

## Client

The `client` directory contains frontend code:

- `index.html` - Main client HTML
- `css/` - CSS stylesheets
  - `all.min.css`
  - `common.css`
  - `dict.css`
  - `sb.css`
  - `toastify.min.css`
- `images/` - Image assets
  - `logo.webp`
- `js/` - JavaScript files
  - `emailService.js`
  - `toastify-js.js`

## HTML

The `html` directory contains additional HTML content:

- `index.html` - Main HTML file
- `my_model/` - Model files
  - `metadata.json`
  - `model.json`
  - `weights.bin`

## Dependencies

The project uses a Python virtual environment with various packages installed in the `Lib/site-packages` directory, including:

- FastAPI
- pytest
- aiohttp
- alembic
- SQLAlchemy
- OpenAI
- and many more

## Migrations

The `migrations` directory contains database migration files:

- `alembic.ini` - Alembic configuration
- `env.py` - Alembic environment
- `script.py.mako` - Alembic script template
- `versions/` - Migration version files

## Development Environment

The project is set up with Python 3.13 and includes various scripts for environment management in the `Scripts` directory.

---

*Note: This structure documentation was automatically generated and may be subject to changes as the project evolves.*