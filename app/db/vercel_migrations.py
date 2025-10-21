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
                'needs_migration': (
                    current_version != '007' or 
                    not notes_column_exists or 
                    not level_column_exists or
                    not prompts_table_exists or
                    not prompts_indexes_exist
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
        Includes: base tables, notes column, level column, prompts table.
        """
        try:
            # Use the enhanced init_db method which handles all migrations
            # This will create all base tables (attempts, question_patterns, users, prompts)
            self.db_provider.init_db()
            
            # Explicitly ensure prompts table and indexes exist
            # (init_db should handle this, but we verify here for Vercel deployments)
            prompts_result = self.add_prompts_table_migration()
            logger.info(f"Prompts table migration result: {prompts_result['message']}")
            
            # Verify the migration was successful
            status = self.check_migration_status()
            
            return {
                'success': True,
                'message': 'All migrations applied successfully (including prompts table)',
                'final_status': status,
                'migrations_applied': [
                    'Base tables (attempts, question_patterns, users)',
                    'Notes column on question_patterns',
                    'Level column on question_patterns',
                    'Prompts table with indexes',
                    'Subscription column on users'
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

# Global instance
migration_manager = VercelMigrationManager()
