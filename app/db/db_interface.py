from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.models.schemas import MathAttempt

class DatabaseProvider(ABC):
    """Abstract base class for database providers."""
    
    @abstractmethod
    def init_db(self) -> None:
        """Initialize the database and create necessary tables if they don't exist."""
        pass
    
    @abstractmethod
    def save_attempt(self, attempt: MathAttempt) -> None:
        """Save a math attempt to the database."""
        pass
    
    @abstractmethod
    def get_attempts(self, student_id: int) -> List[Dict[str, Any]]:
        """Retrieve attempts for a specific student."""
        pass

    @abstractmethod
    def get_attempts_by_uid(self, uid: str) -> List[Dict[str, Any]]:
        """Retrieve attempts for a specific user by UID."""
        pass

    @abstractmethod
    def get_question_patterns(self) -> List[Dict[str, Any]]:
        """Retrieve all question patterns."""
        pass

    @abstractmethod
    def get_question_patterns_by_level(self, level: int = None) -> List[Dict[str, Any]]:
        """Retrieve question patterns filtered by level."""
        pass