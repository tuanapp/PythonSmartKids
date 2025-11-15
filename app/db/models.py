from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, create_engine, ForeignKey, Float, Date
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
    """SQLAlchemy model for AI prompt storage."""
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True)
    uid = Column(String, nullable=False)  # From Firebase Users table (User UID)
    request_text = Column(Text, nullable=False)  # The prompt sent to AI
    response_text = Column(Text, nullable=False)  # The response from AI
    is_live = Column(Integer, default=1, nullable=False)  # 1=live from app, 0=test call
    created_at = Column(DateTime(timezone=True), nullable=False)

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
    registration_date = Column(DateTime(timezone=True), nullable=False)
    
    # Blocking fields
    is_blocked = Column(Boolean, default=False, nullable=False, index=True)
    blocked_reason = Column(Text, nullable=True)
    blocked_at = Column(DateTime(timezone=True), nullable=True)
    blocked_by = Column(String, nullable=True)
    
    # Relationships
    question_generations = relationship("QuestionGeneration", back_populates="user", cascade="all, delete-orphan")
    llm_interactions = relationship("LLMInteraction", back_populates="user", cascade="all, delete-orphan")

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

class QuestionGeneration(Base):
    """SQLAlchemy model for tracking question generation events."""
    __tablename__ = "question_generations"

    id = Column(Integer, primary_key=True)
    uid = Column(String, ForeignKey('users.uid', ondelete='CASCADE'), nullable=False, index=True)  # Firebase User UID
    generation_date = Column(Date, nullable=False, index=True)  # Date only (for daily counting)
    generation_datetime = Column(DateTime(timezone=True), nullable=False)  # Full timestamp
    level = Column(Integer, nullable=True)  # Difficulty level requested (1-6)
    source = Column(String(50), default='api', nullable=False)  # 'api', 'cached', 'fallback'
    llm_interaction_id = Column(Integer, ForeignKey('llm_interactions.id', ondelete='SET NULL'), nullable=True)  # Link to LLM call
    
    # Relationships
    user = relationship("User", back_populates="question_generations")
    llm_interaction = relationship("LLMInteraction", back_populates="question_generation")

class LLMInteraction(Base):
    """SQLAlchemy model for tracking LLM API interactions."""
    __tablename__ = "llm_interactions"

    id = Column(Integer, primary_key=True)
    uid = Column(String, ForeignKey('users.uid', ondelete='CASCADE'), nullable=False, index=True)  # Firebase User UID
    request_datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)  # The full prompt sent to LLM
    response_text = Column(Text, nullable=True)  # The full response from LLM (nullable in case of errors)
    model_name = Column(String(100), nullable=True)  # e.g., 'gpt-4', 'gpt-3.5-turbo'
    prompt_tokens = Column(Integer, nullable=True)  # Token count for prompt
    completion_tokens = Column(Integer, nullable=True)  # Token count for response
    total_tokens = Column(Integer, nullable=True)  # Total tokens used
    estimated_cost_usd = Column(Float, nullable=True)  # Calculated cost in USD
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    status = Column(String(50), default='success', nullable=False)  # 'success', 'error', 'timeout'
    error_message = Column(Text, nullable=True)  # Error details if status != 'success'
    
    # Relationships
    user = relationship("User", back_populates="llm_interactions")
    question_generation = relationship("QuestionGeneration", back_populates="llm_interaction", uselist=False)

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