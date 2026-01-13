"""Create schema and data SQL backups using pg_dump."""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from app.config import DATABASE_URL, NEON_DBNAME, NEON_HOST, NEON_PASSWORD, NEON_SSLMODE, NEON_USER


def _build_database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    if DATABASE_URL:
        return DATABASE_URL
    return f"postgresql://{NEON_USER}:{NEON_PASSWORD}@{NEON_HOST}/{NEON_DBNAME}?sslmode={NEON_SSLMODE}"


def _sanitize_url_and_env(database_url: str) -> tuple[str, dict]:
    parsed = urlparse(database_url)
    env = dict(os.environ)
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
        username = parsed.username or ""
        host = parsed.hostname or ""
        if parsed.port:
            host = f"{host}:{parsed.port}"
        netloc = f"{username}@{host}" if username else host
        sanitized = urlunparse(
            (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
        )
        return sanitized, env
    return database_url, env


def _run_pg_dump(args: list[str], env: dict) -> None:
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "pg_dump failed")


def _verify_connection(database_url: str) -> None:
    try:
        import psycopg2
    except ImportError as exc:
        raise RuntimeError("psycopg2 is required for --verify-connection") from exc

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup PostgreSQL schema and data to SQL files.")
    default_output_dir = Path(__file__).resolve().parents[2] / "docs"
    parser.add_argument(
        "--output-dir",
        default=str(default_output_dir),
        help="Directory for output SQL files (default: <repo>/docs).",
    )
    parser.add_argument(
        "--prefix",
        default="smartboy",
        help="Filename prefix for backup files (default: smartboy).",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL for the backup run.",
    )
    parser.add_argument(
        "--data-inserts",
        action="store_true",
        help="Use INSERT statements instead of COPY for data backup.",
    )
    parser.add_argument(
        "--verify-connection",
        action="store_true",
        help="Check database connectivity before running backups.",
    )

    args = parser.parse_args()

    if not shutil.which("pg_dump"):
        print("pg_dump not found in PATH. Please install PostgreSQL client tools.", file=sys.stderr)
        return 1

    database_url = args.database_url or _build_database_url()
    sanitized_url, env = _sanitize_url_and_env(database_url)

    parsed = urlparse(sanitized_url)
    db_name = parsed.path.lstrip("/") or "(unknown)"
    db_host = parsed.hostname or "(unknown)"
    print(f"Connecting to database: {db_name} on {db_host}")

    if args.verify_connection:
        print("Verifying database connectivity...")
        _verify_connection(database_url)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    schema_path = output_dir / f"{args.prefix}_schema_{timestamp}.sql"
    data_path = output_dir / f"{args.prefix}_data_{timestamp}.sql"

    schema_cmd = [
        "pg_dump",
        "--schema-only",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(schema_path),
        "--dbname",
        sanitized_url,
    ]

    data_cmd = [
        "pg_dump",
        "--data-only",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(data_path),
        "--dbname",
        sanitized_url,
    ]

    if args.data_inserts:
        data_cmd.append("--inserts")

    print("Running schema backup...")
    _run_pg_dump(schema_cmd, env)
    print(f"Schema backup saved: {schema_path}")

    print("Running data backup...")
    _run_pg_dump(data_cmd, env)
    print(f"Data backup saved: {data_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
