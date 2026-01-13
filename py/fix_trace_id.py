#!/usr/bin/env python
"""Apply migration 023 to add trace_id column if missing"""
import sys
import os

# Set environment
os.environ['ENVIRONMENT'] = 'production'

# Load production env vars
with open('.env.production', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

# Add app to path
sys.path.insert(0, '.')

from app.db.vercel_migrations import migration_manager

print("Applying migration 023...")
result = migration_manager.apply_migration_023()
print(f"\nResult: {result}")
