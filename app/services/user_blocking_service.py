"""
User Blocking Service
Handles all user blocking and unblocking operations.
"""
from datetime import datetime, UTC
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import User, UserBlockingHistory


class UserBlockingService:
    """Service for managing user blocking functionality."""
    
    @staticmethod
    def block_user(
        db: Session,
        user_uid: str,
        reason: str,
        blocked_by: str,
        notes: Optional[str] = None
    ) -> User:
        """
        Block a user with specified reason.
        
        Args:
            db: Database session
            user_uid: Firebase User UID
            reason: Reason for blocking
            blocked_by: Admin or system identifier
            notes: Additional notes (optional)
            
        Returns:
            Updated User object
            
        Raises:
            ValueError: If user not found
            SQLAlchemyError: If database operation fails
        """
        try:
            # Find user
            user = db.query(User).filter(User.uid == user_uid).first()
            if not user:
                raise ValueError(f"User not found: {user_uid}")
            
            # Check if already blocked
            if user.is_blocked:
                raise ValueError(f"User is already blocked: {user_uid}")
            
            # Update user blocking status
            user.is_blocked = True
            user.blocked_reason = reason
            user.blocked_at = datetime.now(UTC)
            user.blocked_by = blocked_by
            
            # Create blocking history record
            history = UserBlockingHistory(
                user_uid=user_uid,
                action="BLOCKED",
                reason=reason,
                blocked_at=datetime.now(UTC),
                blocked_by=blocked_by,
                notes=notes
            )
            db.add(history)
            
            # Commit changes
            db.commit()
            db.refresh(user)
            
            return user
            
        except SQLAlchemyError as e:
            db.rollback()
            raise SQLAlchemyError(f"Database error while blocking user: {str(e)}")
    
    @staticmethod
    def unblock_user(
        db: Session,
        user_uid: str,
        unblocked_by: str,
        notes: Optional[str] = None
    ) -> User:
        """
        Unblock a user.
        
        Args:
            db: Database session
            user_uid: Firebase User UID
            unblocked_by: Admin or system identifier
            notes: Additional notes (optional)
            
        Returns:
            Updated User object
            
        Raises:
            ValueError: If user not found
            SQLAlchemyError: If database operation fails
        """
        try:
            # Find user
            user = db.query(User).filter(User.uid == user_uid).first()
            if not user:
                raise ValueError(f"User not found: {user_uid}")
            
            # Check if user is actually blocked
            if not user.is_blocked:
                raise ValueError(f"User is not blocked: {user_uid}")
            
            # Update user blocking status
            user.is_blocked = False
            user.blocked_reason = None
            user.blocked_at = None
            user.blocked_by = None
            
            # Create unblocking history record
            history = UserBlockingHistory(
                user_uid=user_uid,
                action="UNBLOCKED",
                unblocked_at=datetime.now(UTC),
                blocked_by=unblocked_by,
                notes=notes
            )
            db.add(history)
            
            # Commit changes
            db.commit()
            db.refresh(user)
            
            return user
            
        except SQLAlchemyError as e:
            db.rollback()
            raise SQLAlchemyError(f"Database error while unblocking user: {str(e)}")
    
    @staticmethod
    def is_user_blocked(db: Session, user_uid: str) -> Tuple[bool, str]:
        """
        Check if user is blocked and return reason.
        
        Args:
            db: Database session
            user_uid: Firebase User UID
            
        Returns:
            Tuple of (is_blocked: bool, reason: str)
        """
        try:
            user = db.query(User).filter(User.uid == user_uid).first()
            if not user:
                # User doesn't exist - not blocked
                return False, ""
            
            return user.is_blocked, user.blocked_reason or ""
            
        except SQLAlchemyError as e:
            # On error, allow access (fail open for better UX)
            print(f"Error checking user blocking status: {str(e)}")
            return False, ""
    
    @staticmethod
    def get_blocking_history(
        db: Session,
        user_uid: str,
        limit: int = 10
    ) -> list:
        """
        Get blocking history for a user.
        
        Args:
            db: Database session
            user_uid: Firebase User UID
            limit: Maximum number of records to return
            
        Returns:
            List of UserBlockingHistory objects
        """
        try:
            history = db.query(UserBlockingHistory)\
                .filter(UserBlockingHistory.user_uid == user_uid)\
                .order_by(UserBlockingHistory.blocked_at.desc())\
                .limit(limit)\
                .all()
            
            return history
            
        except SQLAlchemyError as e:
            print(f"Error fetching blocking history: {str(e)}")
            return []
    
    @staticmethod
    def get_all_blocked_users(db: Session, limit: int = 100) -> list:
        """
        Get all currently blocked users.
        
        Args:
            db: Database session
            limit: Maximum number of users to return
            
        Returns:
            List of blocked User objects
        """
        try:
            blocked_users = db.query(User)\
                .filter(User.is_blocked == True)\
                .order_by(User.blocked_at.desc())\
                .limit(limit)\
                .all()
            
            return blocked_users
            
        except SQLAlchemyError as e:
            print(f"Error fetching blocked users: {str(e)}")
            return []
