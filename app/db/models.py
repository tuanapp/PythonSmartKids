from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID
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
    created_at = Column(DateTime(timezone=True), nullable=False)

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