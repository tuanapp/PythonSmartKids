"""Add subjects and knowledge documents tables for Knowledge-Based Question Game

Revision ID: 007
Revises: 006
Create Date: 2025-12-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    """Create tables for Knowledge-Based Question Game feature."""
    
    # Create subjects table
    op.create_table(
        'subjects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create knowledge_documents table
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('grade_level', sa.Integer(), nullable=True),
        sa.Column('difficulty_level', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.CheckConstraint('grade_level IS NULL OR (grade_level >= 4 AND grade_level <= 7)', name='valid_grade_level'),
        sa.CheckConstraint('difficulty_level IS NULL OR (difficulty_level >= 1 AND difficulty_level <= 6)', name='valid_difficulty'),
    )
    
    # Create indexes for knowledge_documents
    op.create_index('idx_knowledge_docs_subject', 'knowledge_documents', ['subject_id'])
    op.create_index('idx_knowledge_docs_grade', 'knowledge_documents', ['grade_level'])
    op.create_index('idx_knowledge_docs_difficulty', 'knowledge_documents', ['difficulty_level'])
    
    # Create knowledge_usage_log table for analytics
    op.create_table(
        'knowledge_usage_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uid', sa.String(100), nullable=False),
        sa.Column('knowledge_doc_id', sa.Integer(), sa.ForeignKey('knowledge_documents.id'), nullable=True),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id'), nullable=True),
        sa.Column('question_count', sa.Integer(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for knowledge_usage_log
    op.create_index('idx_usage_log_uid', 'knowledge_usage_log', ['uid'])
    op.create_index('idx_usage_log_subject', 'knowledge_usage_log', ['subject_id'])
    
    # Create knowledge_question_attempts table for storing knowledge question attempts
    op.create_table(
        'knowledge_question_attempts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uid', sa.String(100), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id'), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('user_answer', sa.Text(), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.Column('evaluation_status', sa.String(20), nullable=True),  # 'correct', 'incorrect', 'partial'
        sa.Column('ai_feedback', sa.Text(), nullable=True),
        sa.Column('best_answer', sa.Text(), nullable=True),
        sa.Column('improvement_tips', sa.Text(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),  # 0.0 - 1.0
        sa.Column('difficulty_level', sa.Integer(), nullable=True),
        sa.Column('topic', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for knowledge_question_attempts
    op.create_index('idx_knowledge_attempts_uid', 'knowledge_question_attempts', ['uid'])
    op.create_index('idx_knowledge_attempts_subject', 'knowledge_question_attempts', ['subject_id'])
    
    # Seed initial subjects
    op.execute("""
        INSERT INTO subjects (name, display_name, description, icon, color, is_active) VALUES
        ('science', 'Science', 'General science questions covering biology, chemistry, physics', '🔬', '#4CAF50', true),
        ('history', 'History', 'World history and historical events', '📜', '#795548', true),
        ('geography', 'Geography', 'Countries, capitals, and geographical features', '🌍', '#2196F3', true),
        ('nature', 'Nature', 'Animals, plants, and the natural world', '🌿', '#8BC34A', true),
        ('space', 'Space', 'Astronomy, planets, and the universe', '🚀', '#673AB7', true),
        ('technology', 'Technology', 'Computers, inventions, and modern technology', '💻', '#607D8B', true)
    """)


def downgrade():
    """Remove Knowledge-Based Question Game tables."""
    # Drop indexes
    op.drop_index('idx_knowledge_attempts_subject', table_name='knowledge_question_attempts')
    op.drop_index('idx_knowledge_attempts_uid', table_name='knowledge_question_attempts')
    op.drop_index('idx_usage_log_subject', table_name='knowledge_usage_log')
    op.drop_index('idx_usage_log_uid', table_name='knowledge_usage_log')
    op.drop_index('idx_knowledge_docs_difficulty', table_name='knowledge_documents')
    op.drop_index('idx_knowledge_docs_grade', table_name='knowledge_documents')
    op.drop_index('idx_knowledge_docs_subject', table_name='knowledge_documents')
    
    # Drop tables
    op.drop_table('knowledge_question_attempts')
    op.drop_table('knowledge_usage_log')
    op.drop_table('knowledge_documents')
    op.drop_table('subjects')
