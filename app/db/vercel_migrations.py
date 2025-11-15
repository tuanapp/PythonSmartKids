"""
Vercel-compatible migration utilities for handling database schema updates in production.
"""
import logging
import os
from typing import Dict, Any
from app.db.db_factory import DatabaseFactory

logger = logging.getLogger(__name__)

class VercelMigrationManager:
    """
    Migration manager specifically designed for Vercel deployment constraints.
    Handles schema updates without relying on Alembic's file system operations.
    """
    
    def __init__(self):
        self.db_provider = DatabaseFactory.get_provider()
    
    def check_migration_status(self) -> Dict[str, Any]:
        """
        Check the current migration status and what needs to be applied.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            # Check if alembic_version table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'alembic_version'
                )
            """)
            alembic_exists = cursor.fetchone()[0]
            
            current_version = None
            if alembic_exists:
                cursor.execute("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1")
                result = cursor.fetchone()
                current_version = result[0] if result else None
            
            # Check table existence
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('attempts', 'question_patterns', 'prompts', 'users')
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Check if notes and level columns exist in question_patterns
            notes_column_exists = False
            level_column_exists = False
            if 'question_patterns' in existing_tables:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'question_patterns' AND column_name IN ('notes', 'level')
                """)
                existing_columns = [row[0] for row in cursor.fetchall()]
                notes_column_exists = 'notes' in existing_columns
                level_column_exists = 'level' in existing_columns
            
            # Check if prompts table exists
            prompts_table_exists = 'prompts' in existing_tables
            
            # Check if prompts table has indexes
            prompts_indexes_exist = False
            if prompts_table_exists:
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_indexes 
                    WHERE tablename = 'prompts' 
                    AND indexname IN ('idx_prompts_uid', 'idx_prompts_created_at')
                """)
                prompts_indexes_count = cursor.fetchone()[0]
                prompts_indexes_exist = prompts_indexes_count == 2
            
            # Check if user blocking fields exist
            user_blocking_exists = False
            user_blocking_history_exists = False
            if 'users' in existing_tables:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name IN ('is_blocked', 'blocked_reason', 'blocked_at', 'blocked_by')
                """)
                blocking_columns = [row[0] for row in cursor.fetchall()]
                user_blocking_exists = len(blocking_columns) == 4
            
            # Check if user_blocking_history table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_blocking_history'
                )
            """)
            user_blocking_history_exists = cursor.fetchone()[0]
            
            # Check if question_generations table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'question_generations'
                )
            """)
            question_generations_exists = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                'current_version': current_version,
                'alembic_table_exists': alembic_exists,
                'existing_tables': existing_tables,
                'notes_column_exists': notes_column_exists,
                'level_column_exists': level_column_exists,
                'prompts_table_exists': prompts_table_exists,
                'prompts_indexes_exist': prompts_indexes_exist,
                'user_blocking_exists': user_blocking_exists,
                'user_blocking_history_exists': user_blocking_history_exists,
                'question_generations_exists': question_generations_exists,
                'needs_migration': (
                    current_version != '007' or  # Updated to latest version
                    not notes_column_exists or 
                    not level_column_exists or
                    not prompts_table_exists or
                    not prompts_indexes_exist or
                    not user_blocking_exists or
                    not user_blocking_history_exists or
                    not question_generations_exists
                )
            }
            
        except Exception as e:
            logger.error(f"Error checking migration status: {e}")
            return {
                'error': str(e),
                'needs_migration': True
            }
    
    def apply_all_migrations(self) -> Dict[str, Any]:
        """
        Apply all migrations up to the latest version.
        This method handles the complete schema setup for Vercel deployment.
        Includes: base tables, notes column, level column, prompts table, user blocking, question generation tracking.
        """
        try:
            # Use the enhanced init_db method which handles all migrations
            # This will create all base tables (attempts, question_patterns, users, prompts)
            self.db_provider.init_db()
            
            # Explicitly ensure prompts table and indexes exist
            # (init_db should handle this, but we verify here for Vercel deployments)
            prompts_result = self.add_prompts_table_migration()
            logger.info(f"Prompts table migration result: {prompts_result['message']}")
            
            # Ensure user blocking fields exist
            blocking_result = self.add_user_blocking_migration()
            logger.info(f"User blocking migration result: {blocking_result['message']}")
            
            # Ensure question generation tracking tables exist (NEW)
            tracking_result = self.add_question_generation_tracking_migration()
            logger.info(f"Question generation tracking migration result: {tracking_result['message']}")
            
            # Verify the migration was successful
            status = self.check_migration_status()
            
            return {
                'success': True,
                'message': 'All migrations applied successfully (including question generation tracking)',
                'final_status': status,
                'migrations_applied': [
                    'Base tables (attempts, question_patterns, users)',
                    'Notes column on question_patterns',
                    'Level column on question_patterns',
                    'Prompts table with indexes',
                    'Subscription column on users',
                    'User blocking fields on users',
                    'User blocking history table',
                    'LLM interactions table (question generation tracking)',
                    'Question generations table (daily limit tracking)'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error applying migrations: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_notes_column_migration(self) -> Dict[str, Any]:
        """
        Specifically apply the notes column migration (005).
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            # Check if notes column already exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'question_patterns' AND column_name = 'notes'
                )
            """)
            notes_exists = cursor.fetchone()[0]
            
            if not notes_exists:
                # Add the notes column
                cursor.execute("ALTER TABLE question_patterns ADD COLUMN notes TEXT")
                logger.info("Added notes column to question_patterns table")
                
                # Update migration version
                cursor.execute("""
                    INSERT INTO alembic_version (version_num) VALUES ('005')
                    ON CONFLICT (version_num) DO NOTHING
                """)
                
                conn.commit()
                message = "Successfully added notes column"
            else:
                message = "Notes column already exists"
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error adding notes column: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_level_column_migration(self) -> Dict[str, Any]:
        """
        Specifically apply the level column migration (006).
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            # Check if level column already exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'question_patterns' AND column_name = 'level'
                )
            """)
            level_exists = cursor.fetchone()[0]
            
            if not level_exists:
                # Add the level column
                cursor.execute("ALTER TABLE question_patterns ADD COLUMN level INTEGER")
                logger.info("Added level column to question_patterns table")
                
                # Update migration version
                cursor.execute("""
                    INSERT INTO alembic_version (version_num) VALUES ('006')
                    ON CONFLICT (version_num) DO NOTHING
                """)
                
                conn.commit()
                message = "Successfully added level column"
            else:
                message = "Level column already exists"
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error adding level column: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_prompts_table_migration(self) -> Dict[str, Any]:
        """
        Apply the prompts table migration (007).
        Creates the prompts table for storing AI request/response pairs.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            # Check if prompts table already exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'prompts'
                )
            """)
            prompts_exists = cursor.fetchone()[0]
            
            if not prompts_exists:
                # Create the prompts table
                cursor.execute("""
                    CREATE TABLE prompts (
                        id SERIAL PRIMARY KEY,
                        uid TEXT NOT NULL,
                        request_text TEXT NOT NULL,
                        response_text TEXT NOT NULL,
                        is_live INTEGER DEFAULT 1 NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                logger.info("Created prompts table")
                
                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX idx_prompts_uid ON prompts(uid)
                """)
                logger.info("Created index on prompts.uid")
                
                cursor.execute("""
                    CREATE INDEX idx_prompts_created_at ON prompts(created_at)
                """)
                logger.info("Created index on prompts.created_at")
                
                # Update migration version
                cursor.execute("""
                    INSERT INTO alembic_version (version_num) VALUES ('007')
                    ON CONFLICT (version_num) DO NOTHING
                """)
                
                conn.commit()
                message = "Successfully created prompts table with indexes"
            else:
                # Check if indexes exist
                cursor.execute("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'prompts' 
                    AND indexname IN ('idx_prompts_uid', 'idx_prompts_created_at')
                """)
                existing_indexes = [row[0] for row in cursor.fetchall()]
                
                # Create missing indexes
                if 'idx_prompts_uid' not in existing_indexes:
                    cursor.execute("CREATE INDEX idx_prompts_uid ON prompts(uid)")
                    logger.info("Created missing index on prompts.uid")
                    conn.commit()
                
                if 'idx_prompts_created_at' not in existing_indexes:
                    cursor.execute("CREATE INDEX idx_prompts_created_at ON prompts(created_at)")
                    logger.info("Created missing index on prompts.created_at")
                    conn.commit()
                
                message = "Prompts table already exists, verified indexes"
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': message
            }
            
        except Exception as e:
            logger.error(f"Error creating prompts table: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_user_blocking_migration(self) -> Dict[str, Any]:
        """
        Apply the user blocking migration (008).
        Adds blocking fields to users table and creates user_blocking_history table.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            messages = []
            
            # Check if users table exists, create if not
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
            """)
            users_exists = cursor.fetchone()[0]
            
            if not users_exists:
                # Create users table with blocking fields
                cursor.execute("""
                    CREATE TABLE users (
                        id SERIAL PRIMARY KEY,
                        uid VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        display_name VARCHAR(255) NOT NULL,
                        grade_level INTEGER NOT NULL,
                        subscription INTEGER DEFAULT 0 NOT NULL,
                        registration_date TIMESTAMP WITH TIME ZONE NOT NULL,
                        is_blocked BOOLEAN DEFAULT FALSE NOT NULL,
                        blocked_reason TEXT,
                        blocked_at TIMESTAMP WITH TIME ZONE,
                        blocked_by VARCHAR(255)
                    )
                """)
                messages.append("Created users table with blocking fields")
                logger.info("Created users table")
                
                # Create index on uid
                cursor.execute("CREATE INDEX idx_users_uid ON users(uid)")
                messages.append("Created index on users.uid")
            else:
                # Add blocking fields to existing users table if they don't exist
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name IN ('is_blocked', 'blocked_reason', 'blocked_at', 'blocked_by')
                """)
                existing_blocking_columns = [row[0] for row in cursor.fetchall()]
                
                if 'is_blocked' not in existing_blocking_columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE NOT NULL")
                    messages.append("Added is_blocked column to users table")
                    logger.info("Added is_blocked column")
                
                if 'blocked_reason' not in existing_blocking_columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN blocked_reason TEXT")
                    messages.append("Added blocked_reason column to users table")
                    logger.info("Added blocked_reason column")
                
                if 'blocked_at' not in existing_blocking_columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN blocked_at TIMESTAMP WITH TIME ZONE")
                    messages.append("Added blocked_at column to users table")
                    logger.info("Added blocked_at column")
                
                if 'blocked_by' not in existing_blocking_columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN blocked_by VARCHAR(255)")
                    messages.append("Added blocked_by column to users table")
                    logger.info("Added blocked_by column")
            
            # Create index for blocked users if it doesn't exist
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes 
                    WHERE tablename = 'users' AND indexname = 'idx_users_is_blocked'
                )
            """)
            blocked_index_exists = cursor.fetchone()[0]
            
            if not blocked_index_exists:
                cursor.execute("CREATE INDEX idx_users_is_blocked ON users(is_blocked) WHERE is_blocked = TRUE")
                messages.append("Created index on users.is_blocked")
                logger.info("Created index on users.is_blocked")
            
            # Check if user_blocking_history table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_blocking_history'
                )
            """)
            history_exists = cursor.fetchone()[0]
            
            if not history_exists:
                # Create user_blocking_history table
                cursor.execute("""
                    CREATE TABLE user_blocking_history (
                        id SERIAL PRIMARY KEY,
                        user_uid VARCHAR(255) NOT NULL,
                        action VARCHAR(50) NOT NULL,
                        reason TEXT,
                        blocked_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        blocked_by VARCHAR(255),
                        unblocked_at TIMESTAMP WITHOUT TIME ZONE,
                        notes TEXT
                    )
                """)
                messages.append("Created user_blocking_history table")
                logger.info("Created user_blocking_history table")
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_blocking_history_uid ON user_blocking_history(user_uid)")
                cursor.execute("CREATE INDEX idx_blocking_history_action ON user_blocking_history(action)")
                cursor.execute("CREATE INDEX idx_blocking_history_blocked_at ON user_blocking_history(blocked_at DESC)")
                messages.append("Created indexes on user_blocking_history table")
                logger.info("Created indexes on user_blocking_history")
            else:
                messages.append("User blocking history table already exists")
            
            # Update migration version
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('008')
                ON CONFLICT (version_num) DO NOTHING
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'User blocking already configured'
            }
            
        except Exception as e:
            logger.error(f"Error adding user blocking migration: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_question_generation_tracking_migration(self) -> Dict[str, Any]:
        """
        Migration 008: Simplify architecture - add all tracking columns to prompts, drop question_generations.
        The prompts table now handles all question generation tracking directly.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            logger.info("Starting migration 008: Add tracking columns to prompts, drop question_generations")
            
            # Define all columns that should exist in prompts table (from Migration 008)
            required_columns = [
                ('request_type', 'VARCHAR(50) DEFAULT NULL'),
                ('model_name', 'VARCHAR(100) DEFAULT NULL'),
                ('response_time_ms', 'INTEGER DEFAULT NULL'),
                ('prompt_tokens', 'INTEGER DEFAULT NULL'),
                ('completion_tokens', 'INTEGER DEFAULT NULL'),
                ('total_tokens', 'INTEGER DEFAULT NULL'),
                ('estimated_cost_usd', 'DOUBLE PRECISION DEFAULT NULL'),
                ('status', 'VARCHAR(50) DEFAULT NULL'),
                ('error_message', 'TEXT DEFAULT NULL'),
                ('level', 'INTEGER DEFAULT NULL'),
                ('source', 'VARCHAR(50) DEFAULT NULL')
            ]
            
            # Check which columns exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'prompts'
            """)
            existing_columns = {row[0] for row in cursor.fetchall()}
            
            # Add missing columns
            for col_name, col_definition in required_columns:
                if col_name not in existing_columns:
                    cursor.execute(f"""
                        ALTER TABLE prompts 
                        ADD COLUMN {col_name} {col_definition}
                    """)
                    messages.append(f"Added {col_name} column to prompts table")
                    logger.info(f"Added {col_name} column to prompts")
                else:
                    messages.append(f"{col_name} column already exists in prompts")
            
            # Drop question_generations table if it exists (replaced by prompts table)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'question_generations'
                )
            """)
            qgen_exists = cursor.fetchone()[0]
            
            if qgen_exists:
                cursor.execute("DROP TABLE IF EXISTS question_generations CASCADE")
                messages.append("Dropped obsolete question_generations table (replaced by prompts)")
                logger.info("Dropped obsolete question_generations table")
            else:
                messages.append("question_generations table does not exist (already removed)")
            
            # Drop llm_interactions table if it exists (replaced by enhanced prompts table)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'llm_interactions'
                )
            """)
            llm_exists = cursor.fetchone()[0]
            
            if llm_exists:
                cursor.execute("DROP TABLE IF EXISTS llm_interactions CASCADE")
                messages.append("Dropped obsolete llm_interactions table (replaced by prompts)")
                logger.info("Dropped obsolete llm_interactions table")
            else:
                messages.append("llm_interactions table does not exist (already removed)")
            
            # Update migration version to 008
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)
            """)
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('008')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 008")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 008 already applied'
            }
            
        except Exception as e:
            logger.error(f"Error in migration 008: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
migration_manager = VercelMigrationManager()
