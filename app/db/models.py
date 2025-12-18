from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, create_engine, ForeignKey, Float, Date, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

# Create a base class for declarative class definitions
Base = declarative_base()

class Attempt(Base):
    """SQLAlchemy model for student math attempts."""
    __tablename__ = "attempts"
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False)
    uid = Column(String, nullable=False)  # From Firebase Users table (User UID)
    datetime = Column(DateTime, nullable=False)
    question = Column(Text, nullable=False)
    is_answer_correct = Column(Boolean, nullable=False)
    incorrect_answer = Column(Text)
    correct_answer = Column(Text, nullable=False)
    qorder = Column(Integer, nullable=True)  # Order of questions in a session
    model_id = Column(Integer, ForeignKey('llm_models.id', ondelete='SET NULL'), nullable=True, index=True)  # FK to llm_models
    
    # Relationships
    model = relationship("LLMModel", back_populates="attempts")

class QuestionPattern(Base):
    """SQLAlchemy model for question patterns."""
    __tablename__ = "question_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)  # e.g., 'algebra', 'fraction'
    pattern_text = Column(Text, nullable=False)  # e.g., 'a + b = _'
    notes = Column(Text, nullable=True)  # Special formatting or requirement notes
    level = Column(Integer, nullable=True)  # Difficulty level (e.g., 1-10)
    created_at = Column(DateTime(timezone=True), nullable=False)

class Prompt(Base):
    """SQLAlchemy model for AI prompt storage with full LLM interaction tracking."""
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True)
    uid = Column(String, ForeignKey('users.uid', ondelete='CASCADE'), nullable=False, index=True)
    
    # Request details
    request_type = Column(String(50), nullable=False, default='question_generation')  # Type of request
    request_text = Column(Text, nullable=False)  # The prompt sent to AI (legacy name for compatibility)
    model_name = Column(String(100), nullable=True)  # AI model used
    
    # Question generation specific fields
    level = Column(Integer, nullable=True)  # Difficulty level (1-6) for question generation
    source = Column(String(50), nullable=True)  # Source of questions: 'api', 'cached', 'fallback'
    
    # Response details
    response_text = Column(Text, nullable=True)  # The response from AI (nullable for errors)
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    
    # Token usage and cost tracking
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)  # Calculated cost
    
    # Success/Error tracking
    status = Column(String(50), nullable=False, default='success')  # 'success', 'error', 'timeout'
    error_message = Column(Text, nullable=True)
    
    # Metadata
    is_live = Column(Integer, default=1, nullable=False)  # 1=live from app, 0=test call
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)  # Index for daily queries
    
    # Relationships
    user = relationship("User", back_populates="prompts")

class User(Base):
    """SQLAlchemy model for users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uid = Column(String, unique=True, nullable=False, index=True)  # Firebase User UID
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    grade_level = Column(Integer, nullable=False)
    subscription = Column(Integer, default=0, nullable=False)  # 0=free, 1=trial, 2+=premium
    credits = Column(Integer, default=10, nullable=False, index=True)  # AI generation credits (10 for new users)
    registration_date = Column(DateTime(timezone=True), nullable=False)
    
    # Blocking fields
    is_blocked = Column(Boolean, default=False, nullable=False, index=True)
    blocked_reason = Column(Text, nullable=True)
    blocked_at = Column(DateTime(timezone=True), nullable=True)
    blocked_by = Column(String, nullable=True)
    
    # Debug mode - when True, enables API debug panel in frontend
    is_debug = Column(Boolean, default=False, nullable=False)
    
    # Timestamps (auto-managed by database)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    prompts = relationship("Prompt", back_populates="user", cascade="all, delete-orphan")

class UserBlockingHistory(Base):
    """SQLAlchemy model for user blocking history."""
    __tablename__ = "user_blocking_history"

    id = Column(Integer, primary_key=True)
    user_uid = Column(String, nullable=False, index=True)  # Firebase User UID
    action = Column(String(50), nullable=False, index=True)  # 'BLOCKED', 'UNBLOCKED'
    reason = Column(Text, nullable=True)
    blocked_at = Column(DateTime(timezone=True), nullable=True)
    blocked_by = Column(String, nullable=True)
    unblocked_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)


class GameScore(Base):
    """SQLAlchemy model for game scores (leaderboard)."""
    __tablename__ = "game_scores"

    id = Column(Integer, primary_key=True)
    uid = Column(String, nullable=False, index=True)  # Firebase User UID
    user_name = Column(String(255), nullable=False)  # Display name for leaderboard
    game_type = Column(String(50), nullable=False, index=True)  # 'multiplication_time' or 'multiplication_range'
    score = Column(Integer, nullable=False)  # Correct answers for time game
    time_seconds = Column(Integer, nullable=True)  # Completion time for range game
    total_questions = Column(Integer, nullable=True)  # Total questions answered
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CreditUsage(Base):
    """SQLAlchemy model for tracking daily credit usage per user, game, and subject."""
    __tablename__ = "credit_usage"

    id = Column(Integer, primary_key=True)
    uid = Column(String, nullable=False, index=True)  # Firebase User UID
    usage_date = Column(Date, nullable=False, index=True)  # Date of usage (for daily tracking)
    game_type = Column(String(50), nullable=False, index=True)  # 'math', 'dictation', 'knowledge', etc.
    subject = Column(String(100), nullable=True, index=True)  # Subject within game (e.g., 'addition', 'spelling')
    sub_section = Column(String(100), nullable=True)  # Future: sub-section within subject
    credits_used = Column(Integer, nullable=False, default=1)  # Number of credits used
    generation_count = Column(Integer, nullable=False, default=1)  # Number of AI generations
    model_id = Column(Integer, ForeignKey('llm_models.id', ondelete='SET NULL'), nullable=True, index=True)  # FK to llm_models
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    model = relationship("LLMModel", back_populates="credit_usages")


class LLMModel(Base):
    """SQLAlchemy model for tracking available AI models across providers."""
    __tablename__ = "llm_models"

    id = Column(Integer, primary_key=True)
    model_name = Column(String(150), unique=True, nullable=False)  # Provider-native name, e.g., 'models/gemini-2.0-flash'
    display_name = Column(String(150), nullable=True)  # Human-readable name
    provider = Column(String(50), nullable=False, index=True)  # 'google', 'groq', 'anthropic', etc.
    model_type = Column(String(50), nullable=True)  # 'flash', 'flash-lite', 'pro', etc.
    version = Column(String(20), nullable=True)  # '2.0', '2.5', etc.
    order_number = Column(Integer, default=0, nullable=False, index=True)  # Display order
    active = Column(Boolean, default=True, nullable=False)  # Only active models returned in API
    deprecated = Column(Boolean, default=False, nullable=False)  # Old models marked deprecated
    manual = Column(Boolean, default=False, nullable=False)  # manual=True: never auto-updated
    last_seen_at = Column(DateTime(timezone=True), nullable=True)  # Last time seen in provider API
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    credit_usages = relationship("CreditUsage", back_populates="model")
    attempts = relationship("Attempt", back_populates="model")
    knowledge_attempts = relationship("KnowledgeQuestionAttempt", back_populates="model")


class KnowledgeQuestionAttempt(Base):
    """SQLAlchemy model for knowledge question attempts."""
    __tablename__ = "knowledge_question_attempts"

    id = Column(Integer, primary_key=True)
    uid = Column(String(128), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False, index=True)
    question = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    evaluation_status = Column(String(20), nullable=False, index=True)  # 'correct', 'incorrect', 'partial'
    ai_feedback = Column(Text, nullable=True)
    best_answer = Column(Text, nullable=True)
    improvement_tips = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    difficulty_level = Column(Integer, nullable=True)
    topic = Column(String(200), nullable=True)
    model_id = Column(Integer, ForeignKey('llm_models.id', ondelete='SET NULL'), nullable=True, index=True)  # FK to llm_models
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    model = relationship("LLMModel", back_populates="knowledge_attempts")


def get_engine():
    """Get a SQLAlchemy engine instance."""
    return create_engine(DATABASE_URL)

def get_session():
    """Get a SQLAlchemy session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db():
    """Initialize the database with tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)