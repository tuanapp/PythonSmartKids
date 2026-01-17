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
            
            # Check if subjects table exists (knowledge-based questions feature)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'subjects'
                )
            """)
            subjects_exists = cursor.fetchone()[0]
            
            # Check visual limit columns in subjects table
            visual_json_max_exists = False
            visual_svg_max_exists = False
            if subjects_exists:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'subjects' 
                    AND column_name IN ('visual_json_max', 'visual_svg_max')
                """)
                existing_visual_columns = [row[0] for row in cursor.fetchall()]
                visual_json_max_exists = 'visual_json_max' in existing_visual_columns
                visual_svg_max_exists = 'visual_svg_max' in existing_visual_columns
            
            # Check if knowledge_documents table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'knowledge_documents'
                )
            """)
            knowledge_documents_exists = cursor.fetchone()[0]
            
            # Check if game_scores table exists (leaderboard feature)
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'game_scores'
                )
            """)
            game_scores_exists = cursor.fetchone()[0]
            
            # Check if credits column exists on users table
            credits_column_exists = False
            if 'users' in existing_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'credits'
                    )
                """)
                credits_column_exists = cursor.fetchone()[0]
            
            # Check if credit_usage table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'credit_usage'
                )
            """)
            credit_usage_exists = cursor.fetchone()[0]
            
            # Check if llm_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'llm_models'
                )
            """)
            llm_models_exists = cursor.fetchone()[0]
            
            # Check if model_id column exists in credit_usage
            credit_usage_model_id_exists = False
            if credit_usage_exists:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'credit_usage' AND column_name = 'model_id'
                    )
                """)
                credit_usage_model_id_exists = cursor.fetchone()[0]
            
            # Check if knowledge_usage_log table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'knowledge_usage_log'
                )
            """)
            knowledge_usage_log_exists = cursor.fetchone()[0]
            
            # Check new columns in knowledge_usage_log
            request_text_exists = False
            response_text_exists = False
            response_time_ms_exists = False
            model_name_exists = False
            used_fallback_exists = False
            failed_models_exists = False
            knowledge_document_ids_exists = False
            past_incorrect_attempts_count_exists = False
            is_llm_only_exists = False
            level_exists = False
            focus_weak_areas_exists = False
            log_type_exists = False
            
            if knowledge_usage_log_exists:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'knowledge_usage_log' 
                    AND column_name IN ('request_text', 'response_text', 'response_time_ms', 'model_name', 'used_fallback', 'failed_models', 'knowledge_document_ids', 'past_incorrect_attempts_count', 'is_llm_only', 'level', 'focus_weak_areas', 'log_type')
                """)
                existing_columns = [row[0] for row in cursor.fetchall()]
                request_text_exists = 'request_text' in existing_columns
                response_text_exists = 'response_text' in existing_columns
                response_time_ms_exists = 'response_time_ms' in existing_columns
                model_name_exists = 'model_name' in existing_columns
                used_fallback_exists = 'used_fallback' in existing_columns
                failed_models_exists = 'failed_models' in existing_columns
                knowledge_document_ids_exists = 'knowledge_document_ids' in existing_columns
                past_incorrect_attempts_count_exists = 'past_incorrect_attempts_count' in existing_columns
                is_llm_only_exists = 'is_llm_only' in existing_columns
                level_exists = 'level' in existing_columns
                focus_weak_areas_exists = 'focus_weak_areas' in existing_columns
                log_type_exists = 'log_type' in existing_columns
            
            # Check if performance_reports table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'performance_reports'
                )
            """)
            performance_reports_exists = cursor.fetchone()[0]
            
            # Check if promo_code column exists on users table
            promo_code_exists = False
            if 'users' in existing_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'promo_code'
                    )
                """)
                promo_code_exists = cursor.fetchone()[0]
            
            # Check if google_play_purchases table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'google_play_purchases'
                )
            """)
            google_play_purchases_exists = cursor.fetchone()[0]
            
            # Check if subscription_history table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'subscription_history'
                )
            """)
            subscription_history_exists = cursor.fetchone()[0]
            
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
                'subjects_exists': subjects_exists,
                'visual_json_max_exists': visual_json_max_exists,
                'visual_svg_max_exists': visual_svg_max_exists,
                'knowledge_documents_exists': knowledge_documents_exists,
                'game_scores_exists': game_scores_exists,
                'credits_column_exists': credits_column_exists,
                'credit_usage_exists': credit_usage_exists,
                'llm_models_exists': llm_models_exists,
                'credit_usage_model_id_exists': credit_usage_model_id_exists,
                'knowledge_usage_log_exists': knowledge_usage_log_exists,
                'request_text_exists': request_text_exists,
                'response_text_exists': response_text_exists,
                'response_time_ms_exists': response_time_ms_exists,
                'model_name_exists': model_name_exists,
                'used_fallback_exists': used_fallback_exists,
                'failed_models_exists': failed_models_exists,
                'knowledge_document_ids_exists': knowledge_document_ids_exists,
                'past_incorrect_attempts_count_exists': past_incorrect_attempts_count_exists,
                'is_llm_only_exists': is_llm_only_exists,
                'level_exists': level_exists,
                'focus_weak_areas_exists': focus_weak_areas_exists,
                'log_type_exists': log_type_exists,
                'performance_reports_exists': performance_reports_exists,
                'promo_code_exists': promo_code_exists,
                'google_play_purchases_exists': google_play_purchases_exists,
                'subscription_history_exists': subscription_history_exists,
                'needs_migration': (
                    current_version != '020' or  # Updated to latest version
                    not performance_reports_exists or
                    not promo_code_exists or
                    not google_play_purchases_exists or
                    not subscription_history_exists or
                    not notes_column_exists or 
                    not level_column_exists or
                    not prompts_table_exists or
                    not prompts_indexes_exist or
                    not user_blocking_exists or
                    not user_blocking_history_exists or
                    not subjects_exists or
                    not visual_json_max_exists or
                    not visual_svg_max_exists or
                    not knowledge_documents_exists or
                    not game_scores_exists or
                    not credits_column_exists or
                    not credit_usage_exists or
                    not llm_models_exists or
                    not credit_usage_model_id_exists or
                    not knowledge_usage_log_exists or
                    not request_text_exists or
                    not response_text_exists or
                    not response_time_ms_exists or
                    not model_name_exists or
                    not used_fallback_exists or
                    not failed_models_exists or
                    not knowledge_document_ids_exists or
                    not past_incorrect_attempts_count_exists or
                    not is_llm_only_exists or
                    not level_exists or
                    not focus_weak_areas_exists or
                    not log_type_exists
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
            
            # Ensure knowledge-based questions tables exist
            knowledge_result = self.add_knowledge_based_questions_migration()
            logger.info(f"Knowledge-based questions migration result: {knowledge_result['message']}")
            
            # Ensure game_scores table exists (leaderboard feature)
            game_scores_result = self.add_game_scores_migration()
            logger.info(f"Game scores migration result: {game_scores_result['message']}")
            
            # Ensure credits column exists on users table
            credits_result = self.add_credits_column_migration()
            logger.info(f"Credits column migration result: {credits_result['message']}")
            
            # Ensure credit_usage table exists (credit tracking analytics)
            credit_usage_result = self.add_credit_usage_table_migration()
            logger.info(f"Credit usage table migration result: {credit_usage_result['message']}")
            
            # Ensure llm_models table exists (LLM model tracking)
            llm_models_result = self.add_llm_models_migration()
            logger.info(f"LLM models table migration result: {llm_models_result['message']}")
            
            # Ensure model_id references exist on tracking tables
            model_refs_result = self.add_model_references_migration()
            logger.info(f"Model references migration result: {model_refs_result['message']}")
            
            # Add knowledge usage log enhancements
            knowledge_usage_log_enhancement_result = self.add_knowledge_usage_log_enhancement_migration()
            logger.info(f"Knowledge usage log enhancement migration result: {knowledge_usage_log_enhancement_result['message']}")
            
            # Add performance reports table
            performance_reports_result = self.apply_migration_015()
            logger.info(f"Performance reports migration result: {performance_reports_result['message']}")
            
            # Add visual limits to subjects table
            visual_limits_result = self.apply_migration_016()
            logger.info(f"Visual limits migration result: {visual_limits_result['message']}")
            
            # Add attempt_id to knowledge_usage_log table
            attempt_id_result = self.apply_migration_017()
            logger.info(f"Attempt ID migration result: {attempt_id_result['message']}")
            
            # Add quiz_session_id to knowledge_usage_log table
            quiz_session_id_result = self.apply_migration_018()
            logger.info(f"Quiz session ID migration result: {quiz_session_id_result['message']}")
            
            # Migration 017: Add question_number to knowledge_usage_log
            question_number_result = self.apply_migration_017()
            logger.info(f"Question number migration result: {question_number_result['message']}")
            
            # Migration 019: Add promo_code column to users table
            promo_code_result = self.apply_migration_019()
            logger.info(f"Promo code migration result: {promo_code_result['message']}")
            
            # Migration 020: Add Google Play billing tables
            billing_tables_result = self.apply_migration_020()
            logger.info(f"Google Play billing tables migration result: {billing_tables_result['message']}")
            
            # Migration 021: Add credit expiry tracking
            credit_expiry_result = self.apply_migration_021()
            logger.info(f"Credit expiry tracking migration result: {credit_expiry_result['message']}")
            
            # Migration 023: Add performance_reports table
            performance_reports_result = self.apply_migration_023()
            logger.info(f"Performance reports table migration result: {performance_reports_result['message']}")
            
            # Migration 024: Add help_tone_preference column to users table
            help_tone_result = self.apply_migration_024()
            logger.info(f"Help tone preference migration result: {help_tone_result['message']}")
            
            # Migration 025: Add user_devices table for FCM tokens
            user_devices_result = self.apply_migration_025()
            logger.info(f"User devices table migration result: {user_devices_result['message']}")
            
            # Verify the migration was successful
            status = self.check_migration_status()
            
            return {
                'success': True,
                'message': 'All migrations applied successfully (including Google Play billing)',
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
                    'Question generations table (daily limit tracking)',
                    'Subjects table (knowledge-based questions)',
                    'Knowledge documents table',
                    'Game scores table (leaderboard)',
                    'Credits column on users',
                    'Credit usage table (analytics)',
                    'LLM models table',
                    'Model ID references on tracking tables',
                    'Knowledge usage log enhancements',
                    'Performance reports table',
                    'Visual limits on subjects table',
                    'Attempt ID in knowledge usage log',
                    'Quiz session ID in knowledge usage log',
                    'Question number in knowledge usage log',
                    'Promo code column on users table',
                    'Google Play purchases table',
                    'Subscription history table',
                    'Help tone preference column on users table'
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

    def add_knowledge_based_questions_migration(self) -> Dict[str, Any]:
        """
        Migration 009: Add knowledge-based questions feature.
        Creates subjects and knowledge_documents tables for AI-powered educational content.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            logger.info("Starting migration 009: Add knowledge-based questions tables")
            
            # Check if subjects table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'subjects'
                )
            """)
            subjects_exists = cursor.fetchone()[0]
            
            if not subjects_exists:
                # Create the subjects table
                cursor.execute("""
                    CREATE TABLE subjects (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL UNIQUE,
                        display_name VARCHAR(200) NOT NULL,
                        description TEXT,
                        icon VARCHAR(50),
                        color VARCHAR(20),
                        is_active BOOLEAN DEFAULT TRUE NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                messages.append("Created subjects table")
                logger.info("Created subjects table")
                
                # Create index on subjects.name
                cursor.execute("CREATE INDEX idx_subjects_name ON subjects(name)")
                cursor.execute("CREATE INDEX idx_subjects_is_active ON subjects(is_active)")
                messages.append("Created indexes on subjects table")
                
                # Insert default subjects
                cursor.execute("""
                    INSERT INTO subjects (name, display_name, description, icon, color) VALUES
                    ('science', 'Science', 'General science topics including physics, chemistry, and biology', '🔬', '#4CAF50'),
                    ('history', 'History', 'World history and historical events', '📜', '#795548'),
                    ('geography', 'Geography', 'Countries, capitals, and geographical features', '🌍', '#2196F3'),
                    ('nature', 'Nature', 'Animals, plants, and the natural world', '🌿', '#8BC34A'),
                    ('space', 'Space', 'Astronomy, planets, and the universe', '🚀', '#673AB7'),
                    ('technology', 'Technology', 'Computers, inventions, and modern technology', '💻', '#607D8B')
                """)
                messages.append("Inserted default subjects")
                logger.info("Inserted default subjects")
            else:
                # Table exists, check for missing columns and add them
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'subjects'
                """)
                existing_columns = {row[0] for row in cursor.fetchall()}
                
                # Add color column if missing
                if 'color' not in existing_columns:
                    cursor.execute("ALTER TABLE subjects ADD COLUMN color VARCHAR(20)")
                    messages.append("Added color column to subjects table")
                    logger.info("Added color column to subjects table")
                    
                    # Update existing subjects with default colors
                    cursor.execute("""
                        UPDATE subjects SET color = CASE name
                            WHEN 'science' THEN '#4CAF50'
                            WHEN 'history' THEN '#795548'
                            WHEN 'geography' THEN '#2196F3'
                            WHEN 'nature' THEN '#8BC34A'
                            WHEN 'space' THEN '#673AB7'
                            WHEN 'technology' THEN '#607D8B'
                            ELSE '#9E9E9E'
                        END
                        WHERE color IS NULL
                    """)
                    messages.append("Updated existing subjects with default colors")
                else:
                    messages.append("Subjects table already exists with all columns")
            
            # Check if knowledge_documents table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'knowledge_documents'
                )
            """)
            knowledge_documents_exists = cursor.fetchone()[0]
            
            if not knowledge_documents_exists:
                # Create the knowledge_documents table
                cursor.execute("""
                    CREATE TABLE knowledge_documents (
                        id SERIAL PRIMARY KEY,
                        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                        title VARCHAR(300) NOT NULL,
                        content TEXT NOT NULL,
                        grade_level INTEGER,
                        source VARCHAR(500),
                        is_active BOOLEAN DEFAULT TRUE NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                messages.append("Created knowledge_documents table")
                logger.info("Created knowledge_documents table")
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_knowledge_documents_subject_id ON knowledge_documents(subject_id)")
                cursor.execute("CREATE INDEX idx_knowledge_documents_grade_level ON knowledge_documents(grade_level)")
                cursor.execute("CREATE INDEX idx_knowledge_documents_is_active ON knowledge_documents(is_active)")
                messages.append("Created indexes on knowledge_documents table")
                logger.info("Created indexes on knowledge_documents table")
            else:
                messages.append("Knowledge documents table already exists")
            
            # Check if knowledge_question_attempts table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'knowledge_question_attempts'
                )
            """)
            knowledge_attempts_exists = cursor.fetchone()[0]
            
            if not knowledge_attempts_exists:
                # Create the knowledge_question_attempts table
                cursor.execute("""
                    CREATE TABLE knowledge_question_attempts (
                        id SERIAL PRIMARY KEY,
                        uid VARCHAR(128) NOT NULL,
                        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
                        question TEXT NOT NULL,
                        user_answer TEXT NOT NULL,
                        correct_answer TEXT NOT NULL,
                        evaluation_status VARCHAR(20) NOT NULL,
                        ai_feedback TEXT,
                        best_answer TEXT,
                        improvement_tips TEXT,
                        score FLOAT,
                        difficulty_level INTEGER,
                        topic VARCHAR(200),
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                messages.append("Created knowledge_question_attempts table")
                logger.info("Created knowledge_question_attempts table")
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX idx_knowledge_attempts_uid ON knowledge_question_attempts(uid)")
                cursor.execute("CREATE INDEX idx_knowledge_attempts_subject ON knowledge_question_attempts(subject_id)")
                cursor.execute("CREATE INDEX idx_knowledge_attempts_status ON knowledge_question_attempts(evaluation_status)")
                cursor.execute("CREATE INDEX idx_knowledge_attempts_created ON knowledge_question_attempts(created_at DESC)")
                messages.append("Created indexes on knowledge_question_attempts table")
                logger.info("Created indexes on knowledge_question_attempts table")
            else:
                messages.append("Knowledge question attempts table already exists")
            
            # Check if knowledge_usage_log table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'knowledge_usage_log'
                )
            """)
            knowledge_usage_log_exists = cursor.fetchone()[0]
            
            if not knowledge_usage_log_exists:
                # Create the knowledge_usage_log table
                cursor.execute("""
                    CREATE TABLE knowledge_usage_log (
                        id SERIAL PRIMARY KEY,
                        uid VARCHAR(100) NOT NULL,
                        knowledge_doc_id INTEGER REFERENCES knowledge_documents(id),
                        subject_id INTEGER REFERENCES subjects(id),
                        question_count INTEGER,
                        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                messages.append("Created knowledge_usage_log table")
                logger.info("Created knowledge_usage_log table")
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX idx_usage_log_uid ON knowledge_usage_log(uid)")
                cursor.execute("CREATE INDEX idx_usage_log_subject ON knowledge_usage_log(subject_id)")
                messages.append("Created indexes on knowledge_usage_log table")
                logger.info("Created indexes on knowledge_usage_log table")
            else:
                messages.append("Knowledge usage log table already exists")
            
            # Update migration version to 009
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)
            """)
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('009')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 009")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 009 already applied'
            }
            
        except Exception as e:
            logger.error(f"Error in migration 009: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_game_scores_migration(self) -> Dict[str, Any]:
        """
        Apply migration 010: Add game_scores table for leaderboard functionality.
        
        Stores scores for:
        - multiplication_time: highest correct answers in 100s is the best score
        - multiplication_range: lowest time to complete 88 questions is the best score
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if game_scores table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'game_scores'
                )
            """)
            game_scores_exists = cursor.fetchone()[0]
            
            if not game_scores_exists:
                cursor.execute("""
                    CREATE TABLE game_scores (
                        id SERIAL PRIMARY KEY,
                        uid VARCHAR(100) NOT NULL,
                        user_name VARCHAR(255) NOT NULL,
                        game_type VARCHAR(50) NOT NULL,
                        score INTEGER NOT NULL,
                        time_seconds INTEGER,
                        total_questions INTEGER,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        CONSTRAINT valid_game_type CHECK (game_type IN ('multiplication_time', 'multiplication_range'))
                    )
                """)
                messages.append("Created game_scores table")
                logger.info("Created game_scores table")
                
                # Create indexes for efficient leaderboard queries
                cursor.execute("CREATE INDEX idx_game_scores_uid ON game_scores(uid)")
                cursor.execute("CREATE INDEX idx_game_scores_type ON game_scores(game_type)")
                cursor.execute("CREATE INDEX idx_game_scores_type_score ON game_scores(game_type, score DESC)")
                cursor.execute("CREATE INDEX idx_game_scores_type_time ON game_scores(game_type, time_seconds ASC)")
                messages.append("Created indexes on game_scores table")
                logger.info("Created indexes on game_scores table")
            else:
                messages.append("Game scores table already exists")
            
            # Update migration version to 010
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)
            """)
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('010')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 010")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 010 already applied'
            }
            
        except Exception as e:
            logger.error(f"Error in migration 010: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_credits_column_migration(self) -> Dict[str, Any]:
        """
        Apply migration 010b: Add credits column to users table.
        
        New users get 10 credits by default. Credits are used for AI generation
        and work alongside daily limits.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if credits column exists on users table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'credits'
                )
            """)
            credits_exists = cursor.fetchone()[0]
            
            if not credits_exists:
                # Add credits column with default 10
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN credits INTEGER DEFAULT 10 NOT NULL
                """)
                messages.append("Added credits column to users table")
                logger.info("Added credits column to users table")
                
                # Create index for credits queries
                cursor.execute("CREATE INDEX idx_users_credits ON users(credits)")
                messages.append("Created index on users.credits")
                logger.info("Created index on users.credits")
            else:
                messages.append("Credits column already exists on users table")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Credits column already exists'
            }
            
        except Exception as e:
            logger.error(f"Error adding credits column: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_credit_usage_table_migration(self) -> Dict[str, Any]:
        """
        Apply migration 011: Add credit_usage table for tracking daily credit usage.
        
        Tracks usage per user, per day, per game type, per subject.
        Allows for analytics and reporting on credit consumption.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if credit_usage table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'credit_usage'
                )
            """)
            credit_usage_exists = cursor.fetchone()[0]
            
            if not credit_usage_exists:
                # Create credit_usage table
                cursor.execute("""
                    CREATE TABLE credit_usage (
                        id SERIAL PRIMARY KEY,
                        uid VARCHAR(255) NOT NULL,
                        usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
                        game_type VARCHAR(50) NOT NULL,
                        subject VARCHAR(100),
                        sub_section VARCHAR(100),
                        credits_used INTEGER NOT NULL DEFAULT 1,
                        generation_count INTEGER NOT NULL DEFAULT 1,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                messages.append("Created credit_usage table")
                logger.info("Created credit_usage table")
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_credit_usage_uid ON credit_usage(uid)")
                cursor.execute("CREATE INDEX idx_credit_usage_date ON credit_usage(usage_date)")
                cursor.execute("CREATE INDEX idx_credit_usage_game_type ON credit_usage(game_type)")
                cursor.execute("CREATE INDEX idx_credit_usage_subject ON credit_usage(subject)")
                messages.append("Created basic indexes on credit_usage table")
                logger.info("Created basic indexes on credit_usage table")
                
                # Create composite index for efficient daily lookups
                cursor.execute("""
                    CREATE INDEX ix_credit_usage_uid_date_game 
                    ON credit_usage(uid, usage_date, game_type)
                """)
                messages.append("Created composite index for daily lookups")
                logger.info("Created composite index for daily lookups")
                
                # Create unique constraint for upsert operations
                cursor.execute("""
                    CREATE UNIQUE INDEX uq_credit_usage_uid_date_game_subject 
                    ON credit_usage(uid, usage_date, game_type, COALESCE(subject, ''))
                """)
                messages.append("Created unique constraint for upsert")
                logger.info("Created unique constraint for upsert")
            else:
                messages.append("Credit usage table already exists")
            
            # Update migration version to 011
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)
            """)
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('011')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 011")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 011 already applied'
            }
            
        except Exception as e:
            logger.error(f"Error in migration 011: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_llm_models_migration(self) -> Dict[str, Any]:
        """
        Apply migration 012: Add llm_models table for tracking available AI models.
        
        Stores LLM models from various providers (Google, Groq, Anthropic, etc.).
        Supports manual overrides, deprecation tracking, and ordering.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if llm_models table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'llm_models'
                )
            """)
            llm_models_exists = cursor.fetchone()[0]
            
            if not llm_models_exists:
                # Create llm_models table
                cursor.execute("""
                    CREATE TABLE llm_models (
                        id SERIAL PRIMARY KEY,
                        model_name VARCHAR(150) NOT NULL UNIQUE,
                        display_name VARCHAR(150),
                        provider VARCHAR(50) NOT NULL,
                        model_type VARCHAR(50),
                        version VARCHAR(20),
                        order_number INTEGER DEFAULT 0 NOT NULL,
                        active BOOLEAN DEFAULT TRUE NOT NULL,
                        deprecated BOOLEAN DEFAULT FALSE NOT NULL,
                        manual BOOLEAN DEFAULT FALSE NOT NULL,
                        last_seen_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                messages.append("Created llm_models table")
                logger.info("Created llm_models table")
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_llm_models_active ON llm_models(active) WHERE active = TRUE")
                cursor.execute("CREATE INDEX idx_llm_models_provider ON llm_models(provider)")
                cursor.execute("CREATE INDEX idx_llm_models_order ON llm_models(order_number)")
                cursor.execute("CREATE INDEX idx_llm_models_deprecated ON llm_models(deprecated) WHERE deprecated = TRUE")
                messages.append("Created indexes on llm_models table")
                logger.info("Created indexes on llm_models table")
            else:
                messages.append("LLM models table already exists")
            
            # Update migration version to 012
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)
            """)
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('012')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 012")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 012 already applied'
            }
            
        except Exception as e:
            logger.error(f"Error in migration 012: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_model_references_migration(self) -> Dict[str, Any]:
        """
        Apply migration 013: Add model_id foreign key references to tracking tables.
        
        Adds nullable model_id column to:
        - credit_usage (primary tracking table for AI usage)
        - attempts (math question attempts)
        - knowledge_question_attempts (knowledge game attempts)
        
        Existing rows will have NULL for model_id. Only new records will have the FK populated.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Add model_id to credit_usage table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'credit_usage' AND column_name = 'model_id'
                )
            """)
            credit_usage_model_id_exists = cursor.fetchone()[0]
            
            if not credit_usage_model_id_exists:
                cursor.execute("""
                    ALTER TABLE credit_usage 
                    ADD COLUMN model_id INTEGER REFERENCES llm_models(id) ON DELETE SET NULL
                """)
                cursor.execute("CREATE INDEX idx_credit_usage_model_id ON credit_usage(model_id)")
                messages.append("Added model_id column to credit_usage table")
                logger.info("Added model_id column to credit_usage table")
            else:
                messages.append("credit_usage.model_id already exists")
            
            # Add model_id to attempts table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'attempts' AND column_name = 'model_id'
                )
            """)
            attempts_model_id_exists = cursor.fetchone()[0]
            
            if not attempts_model_id_exists:
                cursor.execute("""
                    ALTER TABLE attempts 
                    ADD COLUMN model_id INTEGER REFERENCES llm_models(id) ON DELETE SET NULL
                """)
                cursor.execute("CREATE INDEX idx_attempts_model_id ON attempts(model_id)")
                messages.append("Added model_id column to attempts table")
                logger.info("Added model_id column to attempts table")
            else:
                messages.append("attempts.model_id already exists")
            
            # Add model_id to knowledge_question_attempts table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'knowledge_question_attempts' AND column_name = 'model_id'
                )
            """)
            knowledge_attempts_model_id_exists = cursor.fetchone()[0]
            
            if not knowledge_attempts_model_id_exists:
                cursor.execute("""
                    ALTER TABLE knowledge_question_attempts 
                    ADD COLUMN model_id INTEGER REFERENCES llm_models(id) ON DELETE SET NULL
                """)
                cursor.execute("CREATE INDEX idx_knowledge_attempts_model_id ON knowledge_question_attempts(model_id)")
                messages.append("Added model_id column to knowledge_question_attempts table")
                logger.info("Added model_id column to knowledge_question_attempts table")
            else:
                messages.append("knowledge_question_attempts.model_id already exists")
            
            # Update migration version to 013
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('013', '012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('013')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 013")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 013 already applied'
            }
            
        except Exception as e:
            logger.error(f"Error in migration 013: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def add_knowledge_usage_log_enhancement_migration(self) -> Dict[str, Any]:
        """
        Apply migration 014: Enhance knowledge_usage_log table with additional tracking columns.
        
        Adds the following nullable columns to knowledge_usage_log:
        - request_text (TEXT)
        - response_text (TEXT)
        - response_time_ms (INTEGER)
        - model_name (VARCHAR(100))
        - used_fallback (BOOLEAN)
        - failed_models (TEXT)
        - knowledge_document_ids (TEXT)
        - past_incorrect_attempts_count (INTEGER)
        - is_llm_only (BOOLEAN)
        - level (INTEGER)
        - focus_weak_areas (BOOLEAN)
        - log_type (VARCHAR(50)) - defaults to 'knowledge'
        
        Adds indexes on log_type, model_name, level if they don't exist.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # List of columns to add
            columns_to_add = [
                ("request_text", "TEXT"),
                ("response_text", "TEXT"),
                ("response_time_ms", "INTEGER"),
                ("model_name", "VARCHAR(100)"),
                ("used_fallback", "BOOLEAN"),
                ("failed_models", "TEXT"),
                ("knowledge_document_ids", "TEXT"),
                ("past_incorrect_attempts_count", "INTEGER"),
                ("is_llm_only", "BOOLEAN"),
                ("level", "INTEGER"),
                ("focus_weak_areas", "BOOLEAN"),
                ("log_type", "VARCHAR(50) DEFAULT 'knowledge'"),
                ("is_live", "INTEGER DEFAULT 1"),
            ]
            
            # Check and add each column
            for column_name, column_type in columns_to_add:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'knowledge_usage_log' AND column_name = '{column_name}'
                    )
                """)
                column_exists = cursor.fetchone()[0]
                
                if not column_exists:
                    cursor.execute(f"ALTER TABLE knowledge_usage_log ADD COLUMN {column_name} {column_type}")
                    messages.append(f"Added {column_name} column to knowledge_usage_log table")
                    logger.info(f"Added {column_name} column to knowledge_usage_log table")
                else:
                    messages.append(f"knowledge_usage_log.{column_name} already exists")
            
            # Check and add indexes
            indexes_to_add = [
                ("idx_knowledge_usage_log_log_type", "log_type"),
                ("idx_knowledge_usage_log_model_name", "model_name"),
                ("idx_knowledge_usage_log_level", "level"),
            ]
            
            for index_name, column_name in indexes_to_add:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM pg_indexes 
                        WHERE tablename = 'knowledge_usage_log' AND indexname = '{index_name}'
                    )
                """)
                index_exists = cursor.fetchone()[0]
                
                if not index_exists:
                    cursor.execute(f"CREATE INDEX {index_name} ON knowledge_usage_log({column_name})")
                    messages.append(f"Created index {index_name} on knowledge_usage_log table")
                    logger.info(f"Created index {index_name} on knowledge_usage_log table")
                else:
                    messages.append(f"Index {index_name} already exists")
            
            # Update migration version to 014
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('014', '013', '012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('014')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 014")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 014 already applied'
            }
            
        except Exception as e:
            logger.error(f"Error in migration 014: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def apply_migration_015(self):
        """
        Apply migration 015: Add performance_reports table for persistent storage of student performance reports.

        Creates the performance_reports table with the following columns:
        - id (SERIAL PRIMARY KEY)
        - uid (VARCHAR NOT NULL, REFERENCES users(uid) ON DELETE CASCADE)
        - report_content (TEXT NOT NULL)
        - report_format (VARCHAR(50) DEFAULT 'markdown')
        - agent_statuses (JSONB)
        - execution_log (JSONB)
        - traces (VARCHAR(255))
        - evidence_sufficient (BOOLEAN DEFAULT FALSE)
        - evidence_quality_score (FLOAT)
        - retrieval_attempts (INTEGER DEFAULT 1)
        - errors (JSONB)
        - success (BOOLEAN DEFAULT TRUE)
        - processing_time_ms (INTEGER)
        - model_used (VARCHAR(100))
        - created_at (TIMESTAMPTZ DEFAULT NOW())
        - updated_at (TIMESTAMPTZ DEFAULT NOW())

        Adds indexes on uid, created_at, and success for efficient queries.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []

            # Create alembic_version table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)
            """)

            # Create performance_reports table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_reports (
                    id SERIAL PRIMARY KEY,
                    uid VARCHAR NOT NULL REFERENCES users(uid) ON DELETE CASCADE,
                    report_content TEXT NOT NULL,
                    report_format VARCHAR(50) DEFAULT 'markdown',
                    agent_statuses JSONB,
                    execution_log JSONB,
                    traces VARCHAR(255),
                    evidence_sufficient BOOLEAN DEFAULT FALSE,
                    evidence_quality_score FLOAT,
                    retrieval_attempts INTEGER DEFAULT 1,
                    errors JSONB,
                    success BOOLEAN DEFAULT TRUE,
                    processing_time_ms INTEGER,
                    model_used VARCHAR(100),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            messages.append("Created performance_reports table")

            # Create indexes
            indexes = [
                ("idx_performance_reports_uid", "uid"),
                ("idx_performance_reports_created_at", "created_at"),
                ("idx_performance_reports_success", "success")
            ]

            for index_name, column_name in indexes:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM pg_indexes
                        WHERE tablename = 'performance_reports' AND indexname = '{index_name}'
                    )
                """)
                index_exists = cursor.fetchone()[0]

                if not index_exists:
                    cursor.execute(f"CREATE INDEX {index_name} ON performance_reports({column_name})")
                    messages.append(f"Created index {index_name}")
                    logger.info(f"Created index {index_name} on performance_reports table")
                else:
                    messages.append(f"Index {index_name} already exists")

            # Update migration version to 015
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('015', '014', '013', '012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('015')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 015")

            conn.commit()
            cursor.close()
            conn.close()

            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 015 already applied'
            }

        except Exception as e:
            logger.error(f"Error in migration 015: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def apply_migration_016(self):
        """
        Apply migration 016: Add visual_json_max and visual_svg_max columns to subjects table.
        
        These columns control per-subject visual generation limits:
        - visual_json_max: Max JSON-based visual questions per subject (frontend renders from params)
        - visual_svg_max: Max AI-generated SVG questions per subject (backend sends complete SVG)
        
        Math/Maths subjects default to visual_json_max=3, visual_svg_max=1
        Other subjects default to 0 until configured
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []

            # Create alembic_version table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)
            """)

            # Add visual_json_max column
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'subjects' AND column_name = 'visual_json_max'
                )
            """)
            visual_json_max_exists = cursor.fetchone()[0]

            if not visual_json_max_exists:
                cursor.execute("""
                    ALTER TABLE subjects ADD COLUMN visual_json_max INTEGER DEFAULT 0 NOT NULL
                """)
                messages.append("Added visual_json_max column to subjects table")
                logger.info("Added visual_json_max column to subjects table")
            else:
                messages.append("visual_json_max column already exists")

            # Add visual_svg_max column
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'subjects' AND column_name = 'visual_svg_max'
                )
            """)
            visual_svg_max_exists = cursor.fetchone()[0]

            if not visual_svg_max_exists:
                cursor.execute("""
                    ALTER TABLE subjects ADD COLUMN visual_svg_max INTEGER DEFAULT 0 NOT NULL
                """)
                messages.append("Added visual_svg_max column to subjects table")
                logger.info("Added visual_svg_max column to subjects table")
            else:
                messages.append("visual_svg_max column already exists")

            # Update Math/Maths subjects with default visual limits
            cursor.execute("""
                UPDATE subjects 
                SET visual_json_max = 3, visual_svg_max = 1 
                WHERE LOWER(name) IN ('math', 'maths', 'mathematics')
                  AND (visual_json_max = 0 OR visual_svg_max = 0)
            """)
            updated_rows = cursor.rowcount
            if updated_rows > 0:
                messages.append(f"Updated {updated_rows} Math/Maths subject(s) with visual limits")
                logger.info(f"Updated {updated_rows} Math/Maths subject(s) with visual limits")

            # Create index for subjects with visual capabilities enabled
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes
                    WHERE tablename = 'subjects' AND indexname = 'idx_subjects_visual_enabled'
                )
            """)
            index_exists = cursor.fetchone()[0]

            if not index_exists:
                cursor.execute("""
                    CREATE INDEX idx_subjects_visual_enabled 
                    ON subjects(visual_json_max, visual_svg_max) 
                    WHERE visual_json_max > 0 OR visual_svg_max > 0
                """)
                messages.append("Created index idx_subjects_visual_enabled")
                logger.info("Created index idx_subjects_visual_enabled on subjects table")
            else:
                messages.append("Index idx_subjects_visual_enabled already exists")

            # Update migration version to 016
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('016', '015', '014', '013', '012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('016')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 016")

            conn.commit()
            cursor.close()
            conn.close()

            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 016 already applied'
            }

        except Exception as e:
            logger.error(f"Error in migration 016: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def apply_migration_017(self) -> Dict[str, Any]:
        """
        Apply migration 017: Add attempt_id to knowledge_usage_log table.
        
        Links help requests to specific knowledge question attempts for historical review.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if attempt_id column exists on knowledge_usage_log table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'knowledge_usage_log' AND column_name = 'attempt_id'
                )
            """)
            attempt_id_exists = cursor.fetchone()[0]
            
            if not attempt_id_exists:
                # Add attempt_id column as nullable foreign key
                cursor.execute("""
                    ALTER TABLE knowledge_usage_log 
                    ADD COLUMN attempt_id INTEGER
                """)
                messages.append("Added attempt_id column to knowledge_usage_log table")
                logger.info("Added attempt_id column to knowledge_usage_log table")
                
                # Add foreign key constraint
                cursor.execute("""
                    ALTER TABLE knowledge_usage_log 
                    ADD CONSTRAINT fk_knowledge_usage_log_attempt_id 
                    FOREIGN KEY (attempt_id) 
                    REFERENCES knowledge_question_attempts(id) 
                    ON DELETE SET NULL
                """)
                messages.append("Added foreign key constraint for attempt_id")
                logger.info("Added foreign key constraint for attempt_id")
                
                # Add index for efficient queries
                cursor.execute("""
                    CREATE INDEX idx_usage_log_attempt_id 
                    ON knowledge_usage_log(attempt_id)
                """)
                messages.append("Created index idx_usage_log_attempt_id")
                logger.info("Created index idx_usage_log_attempt_id on knowledge_usage_log table")
            else:
                messages.append("attempt_id column already exists on knowledge_usage_log table")
            
            # Update migration version to 017
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('017', '016', '015', '014', '013', '012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('017')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 017")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 017 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 017: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def apply_migration_018(self) -> Dict[str, Any]:
        """
        Apply migration 018: Add quiz_session_id to knowledge_usage_log and knowledge_question_attempts tables.
        
        Groups quiz activities (questions + help requests + attempts) by session for accurate linking.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Add quiz_session_id to knowledge_usage_log table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'knowledge_usage_log' AND column_name = 'quiz_session_id'
                )
            """)
            usage_log_quiz_session_id_exists = cursor.fetchone()[0]
            
            if not usage_log_quiz_session_id_exists:
                cursor.execute("""
                    ALTER TABLE knowledge_usage_log 
                    ADD COLUMN quiz_session_id VARCHAR(36)
                """)
                messages.append("Added quiz_session_id column to knowledge_usage_log table")
                logger.info("Added quiz_session_id column to knowledge_usage_log table")
                
                cursor.execute("""
                    CREATE INDEX idx_usage_log_quiz_session_id 
                    ON knowledge_usage_log(quiz_session_id)
                """)
                messages.append("Created index idx_usage_log_quiz_session_id")
                logger.info("Created index idx_usage_log_quiz_session_id on knowledge_usage_log table")
            else:
                messages.append("quiz_session_id column already exists on knowledge_usage_log table")
            
            # Add quiz_session_id to knowledge_question_attempts table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'knowledge_question_attempts' AND column_name = 'quiz_session_id'
                )
            """)
            attempts_quiz_session_id_exists = cursor.fetchone()[0]
            
            if not attempts_quiz_session_id_exists:
                cursor.execute("""
                    ALTER TABLE knowledge_question_attempts 
                    ADD COLUMN quiz_session_id VARCHAR(36)
                """)
                messages.append("Added quiz_session_id column to knowledge_question_attempts table")
                logger.info("Added quiz_session_id column to knowledge_question_attempts table")
                
                cursor.execute("""
                    CREATE INDEX idx_attempts_quiz_session_id 
                    ON knowledge_question_attempts(quiz_session_id)
                """)
                messages.append("Created index idx_attempts_quiz_session_id")
                logger.info("Created index idx_attempts_quiz_session_id on knowledge_question_attempts table")
            else:
                messages.append("quiz_session_id column already exists on knowledge_question_attempts table")
            
            # Update migration version to 018
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('018', '017', '016', '015', '014', '013', '012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('018')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 018")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 018 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 018: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def apply_migration_017(self) -> Dict[str, Any]:
        """
        Migration 017: Add question_number column to knowledge_usage_log table.
        This enables tracking which question each help request belongs to.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if question_number column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'knowledge_usage_log' 
                    AND column_name = 'question_number'
                )
            """)
            question_number_exists = cursor.fetchone()[0]
            
            if not question_number_exists:
                # Add question_number column
                cursor.execute("""
                    ALTER TABLE knowledge_usage_log 
                    ADD COLUMN question_number INTEGER
                """)
                messages.append("Added question_number column to knowledge_usage_log table")
                logger.info("Added question_number column to knowledge_usage_log table")
                
                # Add composite index for efficient queries by session + question
                cursor.execute("""
                    CREATE INDEX idx_usage_log_session_question 
                    ON knowledge_usage_log(quiz_session_id, question_number)
                """)
                messages.append("Created index idx_usage_log_session_question")
                logger.info("Created composite index on (quiz_session_id, question_number)")
            else:
                messages.append("question_number column already exists on knowledge_usage_log table")
            
            # Update migration version to 017
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('017')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('017')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 017")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 017 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 017: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def apply_migration_019(self) -> Dict[str, Any]:
        """
        Apply migration 019: Add promo_code column to users table.
        
        Adds optional promo_code field (max 10 characters) to users table.
        This field stores promotional codes or affiliated institute codes.
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if promo_code column exists on users table
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'promo_code'
                )
            """)
            promo_code_exists = cursor.fetchone()[0]
            
            if not promo_code_exists:
                # Add promo_code column
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN promo_code VARCHAR(10)
                """)
                messages.append("Added promo_code column to users table")
                logger.info("Added promo_code column to users table (max 10 characters)")
                
                # Add index for efficient promo code queries (for analytics/reporting)
                cursor.execute("""
                    CREATE INDEX idx_users_promo_code 
                    ON users(promo_code) 
                    WHERE promo_code IS NOT NULL
                """)
                messages.append("Created partial index idx_users_promo_code")
                logger.info("Created index on promo_code for analytics")
            else:
                messages.append("promo_code column already exists on users table")
            
            # Update migration version to 019
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('019', '018', '017', '016', '015', '014', '013', '012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('019')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 019")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 019 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 019: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def apply_migration_020(self) -> Dict[str, Any]:
        """
        Apply migration 020: Add Google Play billing tables.
        
        Creates two tables for Google Play billing integration:
        1. google_play_purchases - Tracks all purchases (subscriptions + one-time products)
        2. subscription_history - Logs subscription status changes and credit grants
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if google_play_purchases table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'google_play_purchases'
                )
            """)
            google_play_purchases_exists = cursor.fetchone()[0]
            
            if not google_play_purchases_exists:
                # Create google_play_purchases table
                cursor.execute("""
                    CREATE TABLE google_play_purchases (
                        id SERIAL PRIMARY KEY,
                        uid VARCHAR NOT NULL,
                        purchase_token TEXT NOT NULL UNIQUE,
                        product_id VARCHAR(100) NOT NULL,
                        order_id VARCHAR(100),
                        purchase_time TIMESTAMPTZ NOT NULL,
                        purchase_state INTEGER NOT NULL DEFAULT 0,
                        acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
                        auto_renewing BOOLEAN,
                        raw_receipt JSONB,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                messages.append("Created google_play_purchases table")
                logger.info("Created google_play_purchases table")
                
                # Create indexes
                cursor.execute("CREATE INDEX ix_google_play_purchases_uid ON google_play_purchases(uid)")
                cursor.execute("CREATE INDEX ix_google_play_purchases_product_id ON google_play_purchases(product_id)")
                cursor.execute("CREATE INDEX ix_google_play_purchases_order_id ON google_play_purchases(order_id)")
                cursor.execute("CREATE INDEX ix_google_play_purchases_purchase_time ON google_play_purchases(purchase_time)")
                messages.append("Created indexes on google_play_purchases table")
                
                # Add foreign key constraint
                cursor.execute("""
                    ALTER TABLE google_play_purchases 
                    ADD CONSTRAINT fk_google_play_purchases_uid 
                    FOREIGN KEY (uid) REFERENCES users(uid) ON DELETE CASCADE
                """)
                messages.append("Added foreign key constraint to google_play_purchases")
            else:
                messages.append("google_play_purchases table already exists")
            
            # Check if subscription_history table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'subscription_history'
                )
            """)
            subscription_history_exists = cursor.fetchone()[0]
            
            if not subscription_history_exists:
                # Create subscription_history table
                cursor.execute("""
                    CREATE TABLE subscription_history (
                        id SERIAL PRIMARY KEY,
                        uid VARCHAR NOT NULL,
                        purchase_id INTEGER,
                        event VARCHAR(50) NOT NULL,
                        old_subscription INTEGER,
                        new_subscription INTEGER,
                        credits_granted INTEGER DEFAULT 0,
                        performed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        notes TEXT
                    )
                """)
                messages.append("Created subscription_history table")
                logger.info("Created subscription_history table")
                
                # Create indexes
                cursor.execute("CREATE INDEX ix_subscription_history_uid ON subscription_history(uid)")
                cursor.execute("CREATE INDEX ix_subscription_history_event ON subscription_history(event)")
                cursor.execute("CREATE INDEX ix_subscription_history_performed_at ON subscription_history(performed_at)")
                messages.append("Created indexes on subscription_history table")
                
                # Add foreign key constraints
                cursor.execute("""
                    ALTER TABLE subscription_history 
                    ADD CONSTRAINT fk_subscription_history_uid 
                    FOREIGN KEY (uid) REFERENCES users(uid) ON DELETE CASCADE
                """)
                cursor.execute("""
                    ALTER TABLE subscription_history 
                    ADD CONSTRAINT fk_subscription_history_purchase_id 
                    FOREIGN KEY (purchase_id) REFERENCES google_play_purchases(id) ON DELETE SET NULL
                """)
                messages.append("Added foreign key constraints to subscription_history")
            else:
                messages.append("subscription_history table already exists")
            
            # Update migration version to 020
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num IN ('020', '019', '018', '017', '016', '015', '014', '013', '012', '011', '010', '009', '008', '007', '2d3eefae954c')
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('020')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 020")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 020 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 020: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def apply_migration_021(self) -> Dict[str, Any]:
        """
        Migration 021: Add credit expiry tracking for premium subscriptions
        - Adds credits_expire_at column to users table
        - Adds expiry_date column to subscription_history table
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if credits_expire_at column exists on users table
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'credits_expire_at'
            """)
            credits_expire_at_exists = cursor.fetchone() is not None
            
            if not credits_expire_at_exists:
                cursor.execute("ALTER TABLE users ADD COLUMN credits_expire_at TIMESTAMP DEFAULT NULL")
                messages.append("Added credits_expire_at column to users table")
                logger.info("Added credits_expire_at column to users table")
                
                # Add index for efficient expiry queries
                cursor.execute("""
                    CREATE INDEX idx_users_credits_expire_at 
                    ON users(credits_expire_at) 
                    WHERE credits_expire_at IS NOT NULL
                """)
                messages.append("Created index on credits_expire_at")
            else:
                messages.append("credits_expire_at column already exists on users table")
            
            # Check if expiry_date column exists on subscription_history table
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'subscription_history' AND column_name = 'expiry_date'
            """)
            expiry_date_exists = cursor.fetchone() is not None
            
            if not expiry_date_exists:
                cursor.execute("ALTER TABLE subscription_history ADD COLUMN expiry_date TIMESTAMP DEFAULT NULL")
                messages.append("Added expiry_date column to subscription_history table")
                logger.info("Added expiry_date column to subscription_history table")
            else:
                messages.append("expiry_date column already exists on subscription_history table")
            
            # Update migration version to 021
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num = '021'
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('021')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 021")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 021 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 021: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def apply_migration_023(self) -> Dict[str, Any]:
        """
        Migration 023: Add performance_reports table for storing generated performance reports
        Reports are generated by Agentic_Python but retrieved via Backend_Python
        """
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            messages = []
            
            # Check if performance_reports table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'performance_reports'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Create performance_reports table
                cursor.execute("""
                    CREATE TABLE performance_reports (
                        id SERIAL PRIMARY KEY,
                        uid VARCHAR(255) NOT NULL,
                        report_content TEXT NOT NULL,
                        report_format VARCHAR(50) DEFAULT 'markdown',
                        agent_statuses JSONB DEFAULT '{}',
                        execution_log JSONB DEFAULT '[]',
                        traces TEXT,
                        trace_id VARCHAR(255),
                        evidence_sufficient BOOLEAN DEFAULT false,
                        evidence_quality_score DECIMAL(3,2) DEFAULT 0.0,
                        retrieval_attempts INTEGER DEFAULT 0,
                        errors JSONB DEFAULT '[]',
                        success BOOLEAN DEFAULT false,
                        processing_time_ms INTEGER,
                        model_used VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                messages.append("Created performance_reports table")
                logger.info("Created performance_reports table")
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX idx_performance_reports_uid ON performance_reports(uid)
                """)
                cursor.execute("""
                    CREATE INDEX idx_performance_reports_created_at ON performance_reports(created_at DESC)
                """)
                messages.append("Created indexes on performance_reports table")
                
                # Add foreign key constraint
                cursor.execute("""
                    ALTER TABLE performance_reports
                    ADD CONSTRAINT fk_performance_reports_user
                    FOREIGN KEY (uid) REFERENCES users(uid) ON DELETE CASCADE
                """)
                messages.append("Added foreign key constraint to users table")
            else:
                messages.append("performance_reports table already exists")
                
                # Check if trace_id column exists, add it if missing
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'performance_reports' AND column_name = 'trace_id'
                """)
                trace_id_exists = cursor.fetchone() is not None
                
                if not trace_id_exists:
                    cursor.execute("""
                        ALTER TABLE performance_reports ADD COLUMN trace_id VARCHAR(255)
                    """)
                    messages.append("Added trace_id column to performance_reports table")
                    logger.info("Added trace_id column to performance_reports table")
                else:
                    messages.append("trace_id column already exists")
            
            # Update migration version to 023
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num = '023'
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('023')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 023")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 023 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 023: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def apply_migration_024(self) -> Dict[str, Any]:
        """
        Migration 024: Add help_tone_preference column to users table
        Allows users to customize the difficulty level of AI-generated help explanations
        """
        messages = []
        
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            # Check if help_tone_preference column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'help_tone_preference'
                )
            """)
            column_exists = cursor.fetchone()[0]
            
            if not column_exists:
                # Add help_tone_preference column
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN help_tone_preference VARCHAR(10) DEFAULT NULL
                """)
                messages.append("Added help_tone_preference column to users table")
                logger.info("Added help_tone_preference column to users table")
                
                # Add comment
                cursor.execute("""
                    COMMENT ON COLUMN users.help_tone_preference IS 
                    'Preferred help explanation tone: NULL/kid=simple, auto=grade-1, or specific grade 1-12'
                """)
                messages.append("Added comment to help_tone_preference column")
                
                # Create index for better query performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_help_tone_preference 
                    ON users(help_tone_preference)
                """)
                messages.append("Created index on help_tone_preference column")
                logger.info("Created index on help_tone_preference")
            else:
                messages.append("help_tone_preference column already exists")
            
            # Update migration version to 024
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num = '024'
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('024')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 024")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 024 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 024: {e}")
            return {
                'success': False,
                'error': str(e)
            }


    def apply_migration_025(self) -> Dict[str, Any]:
        """
        Migration 025: Add user_devices table for FCM push notification tokens
        Supports multi-device per user with device-level token management
        """
        messages = []
        
        try:
            conn = self.db_provider._get_connection()
            cursor = conn.cursor()
            
            # Check if user_devices table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_devices'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Create user_devices table
                cursor.execute("""
                    CREATE TABLE user_devices (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        device_id VARCHAR(255) NOT NULL,
                        platform VARCHAR(50) NOT NULL DEFAULT 'android',
                        fcm_token VARCHAR(500),
                        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_token_sync_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT user_devices_user_device_unique UNIQUE (user_id, device_id),
                        CONSTRAINT fk_user_devices_user_id FOREIGN KEY (user_id) 
                            REFERENCES users(uid) ON DELETE CASCADE
                    )
                """)
                messages.append("Created user_devices table")
                logger.info("Created user_devices table")
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX idx_user_devices_user_id ON user_devices(user_id)
                """)
                cursor.execute("""
                    CREATE INDEX idx_user_devices_fcm_token ON user_devices(fcm_token) 
                    WHERE fcm_token IS NOT NULL
                """)
                cursor.execute("""
                    CREATE INDEX idx_user_devices_last_seen ON user_devices(last_seen_at)
                """)
                cursor.execute("""
                    CREATE INDEX idx_user_devices_enabled ON user_devices(is_enabled) 
                    WHERE is_enabled = TRUE
                """)
                messages.append("Created indexes on user_devices table")
                logger.info("Created indexes on user_devices table")
                
                # Add comments
                cursor.execute("""
                    COMMENT ON TABLE user_devices IS 
                    'FCM device tokens for push notifications - supports multiple devices per user'
                """)
                cursor.execute("""
                    COMMENT ON COLUMN user_devices.device_id IS 
                    'Stable device identifier generated by app (survives logout)'
                """)
                cursor.execute("""
                    COMMENT ON COLUMN user_devices.last_token_sync_at IS 
                    'Last time token was synced to server (used for 7-day safety net refresh)'
                """)
                messages.append("Added comments to user_devices table")
            else:
                messages.append("user_devices table already exists")
            
            # Update migration version to 025
            cursor.execute("""
                DELETE FROM alembic_version WHERE version_num = '025'
            """)
            cursor.execute("""
                INSERT INTO alembic_version (version_num) VALUES ('025')
                ON CONFLICT (version_num) DO NOTHING
            """)
            messages.append("Updated alembic version to 025")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '; '.join(messages) if messages else 'Migration 025 already applied'
            }
        
        except Exception as e:
            logger.error(f"Error in migration 025: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
migration_manager = VercelMigrationManager()


