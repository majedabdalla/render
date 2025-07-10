"""
Advanced Session Management System for MultiLangTranslator Bot
This module provides robust session management capabilities including:
- Secure user state tracking
- Session persistence and recovery
- Support for conversation resumption
- Multi-session handling per user
- Session timeout and cleanup
"""

import json
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Tuple
import os

# Initialize logger
logger = logging.getLogger(__name__)

class SessionManager:
    """
    Advanced session manager for handling user conversations and states.
    
    Features:
    - Persistent session storage
    - Automatic session recovery
    - Session timeout management
    - Support for multiple concurrent conversations
    - Thread-safe operations
    """
    
    def __init__(self, session_file_path: str, timeout: int = 3600):
        """
        Initialize the session manager.
        
        Args:
            session_file_path: Path to store session data
            timeout: Session timeout in seconds (default: 1 hour)
        """
        self.session_file_path = session_file_path
        self.timeout = timeout
        self.sessions = {}
        self.lock = threading.RLock()
        self._load_sessions()
        
        # Start background cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self.cleanup_thread.start()
    
    def _ensure_directory_exists(self):
        """Ensure the directory for the session file exists."""
        directory = os.path.dirname(self.session_file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    def _load_sessions(self):
        """Load sessions from the persistent storage."""
        try:
            self._ensure_directory_exists()
            if os.path.exists(self.session_file_path):
                with open(self.session_file_path, 'r', encoding='utf-8') as f:
                    loaded_sessions = json.load(f)
                    with self.lock:
                        self.sessions = loaded_sessions
                logger.info(f"Loaded {len(self.sessions)} sessions from {self.session_file_path}")
            else:
                logger.info(f"No session file found at {self.session_file_path}, starting with empty sessions")
                self.sessions = {}
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            self.sessions = {}
    
    def _save_sessions(self):
        """Save sessions to persistent storage."""
        try:
            self._ensure_directory_exists()
            with self.lock:
                with open(self.session_file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.sessions, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(self.sessions)} sessions to {self.session_file_path}")
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")
    
    def get_session(self, user_id: str, conversation_type: str = "default") -> Dict[str, Any]:
        """
        Get a user's session for a specific conversation type.
        Creates a new session if none exists.
        
        Args:
            user_id: Telegram user ID
            conversation_type: Type of conversation (default, search, payment, etc.)
            
        Returns:
            Session data dictionary
        """
        with self.lock:
            # Convert user_id to string for JSON compatibility
            user_id_str = str(user_id)
            
            # Initialize user's sessions if not exist
            if user_id_str not in self.sessions:
                self.sessions[user_id_str] = {}
            
            # Initialize conversation session if not exist
            if conversation_type not in self.sessions[user_id_str]:
                self.sessions[user_id_str][conversation_type] = {
                    "state": None,
                    "data": {},
                    "last_activity": time.time()
                }
            else:
                # Update last activity time
                self.sessions[user_id_str][conversation_type]["last_activity"] = time.time()
            
            return self.sessions[user_id_str][conversation_type]
    
    def update_session(self, user_id: str, conversation_type: str, 
                      state: Optional[Any] = None, data: Optional[Dict[str, Any]] = None):
        """
        Update a user's session state and/or data.
        
        Args:
            user_id: Telegram user ID
            conversation_type: Type of conversation
            state: New conversation state (if None, state remains unchanged)
            data: New data to update (if None, data remains unchanged)
        """
        with self.lock:
            session = self.get_session(user_id, conversation_type)
            
            if state is not None:
                session["state"] = state
            
            if data is not None:
                session["data"].update(data)
            
            session["last_activity"] = time.time()
            
            # Save after each update for persistence
            self._save_sessions()
    
    def clear_session(self, user_id: str, conversation_type: str = "default"):
        """
        Clear a user's session for a specific conversation type.
        
        Args:
            user_id: Telegram user ID
            conversation_type: Type of conversation to clear
        """
        with self.lock:
            user_id_str = str(user_id)
            if user_id_str in self.sessions and conversation_type in self.sessions[user_id_str]:
                self.sessions[user_id_str][conversation_type] = {
                    "state": None,
                    "data": {},
                    "last_activity": time.time()
                }
                self._save_sessions()
    
    def clear_all_user_sessions(self, user_id: str):
        """
        Clear all sessions for a specific user.
        
        Args:
            user_id: Telegram user ID
        """
        with self.lock:
            user_id_str = str(user_id)
            if user_id_str in self.sessions:
                del self.sessions[user_id_str]
                self._save_sessions()
    
    def get_active_users(self, max_idle_time: int = 3600) -> List[str]:
        """
        Get a list of active users who have interacted within the specified time.
        
        Args:
            max_idle_time: Maximum idle time in seconds to consider a user active
            
        Returns:
            List of active user IDs
        """
        active_users = set()
        current_time = time.time()
        
        with self.lock:
            for user_id, conversations in self.sessions.items():
                for conv_type, session in conversations.items():
                    if current_time - session["last_activity"] <= max_idle_time:
                        active_users.add(user_id)
                        break
        
        return list(active_users)
    
    def get_session_count(self) -> Tuple[int, int]:
        """
        Get the count of active users and total sessions.
        
        Returns:
            Tuple of (user_count, session_count)
        """
        user_count = 0
        session_count = 0
        
        with self.lock:
            user_count = len(self.sessions)
            for user_id, conversations in self.sessions.items():
                session_count += len(conversations)
        
        return user_count, session_count
    
    def _cleanup_expired_sessions(self):
        """Background thread to periodically clean up expired sessions."""
        while True:
            try:
                time.sleep(300)  # Check every 5 minutes
                
                current_time = time.time()
                users_to_remove = []
                
                with self.lock:
                    for user_id, conversations in self.sessions.items():
                        conv_to_remove = []
                        
                        for conv_type, session in conversations.items():
                            if current_time - session["last_activity"] > self.timeout:
                                conv_to_remove.append(conv_type)
                        
                        # Remove expired conversations
                        for conv_type in conv_to_remove:
                            del conversations[conv_type]
                        
                        # If user has no conversations left, mark for removal
                        if not conversations:
                            users_to_remove.append(user_id)
                    
                    # Remove users with no conversations
                    for user_id in users_to_remove:
                        del self.sessions[user_id]
                    
                    # Save changes if any sessions were removed
                    if users_to_remove or any(user_id for user_id, convs in self.sessions.items() 
                                             if len(convs) < len(self.sessions[user_id])):
                        self._save_sessions()
                        
                        logger.info(f"Cleaned up {len(users_to_remove)} expired users and their sessions")
            
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")


# Decorator for requiring completed profile
def require_profile(func):
    """
    Decorator to ensure user has a completed profile before accessing a feature.
    
    Args:
        func: The handler function to decorate
        
    Returns:
        Wrapped function that checks for profile completion
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(update, context, *args, **kwargs):
        from data_handler import get_user_data
        from localization import get_text
        
        user_id = str(update.effective_user.id)
        user_data = get_user_data(user_id)
        
        # Check if profile is complete
        required_fields = ["language", "gender", "region", "country"]
        if not all(field in user_data for field in required_fields):
            update.message.reply_text(get_text(user_id, "profile_incomplete"))
            return
        
        return func(update, context, *args, **kwargs)
    
    return wrapper


# Decorator for premium features
def require_premium(func):
    """
    Decorator to ensure user has premium access before using a feature.
    
    Args:
        func: The handler function to decorate
        
    Returns:
        Wrapped function that checks for premium access
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(update, context, *args, **kwargs):
        from data_handler import get_user_data
        from localization import get_text
        
        user_id = str(update.effective_user.id)
        user_data = get_user_data(user_id)
        
        # Check if user has premium access
        if not user_data.get("premium", False):
            # Offer payment option
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = [
                [InlineKeyboardButton(get_text(user_id, "payment_verify_button"), 
                                     callback_data="verify_payment")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                get_text(user_id, "payment_prompt", 
                        payeer_account=context.bot_data.get("payeer_account", "N/A"),
                        bitcoin_address=context.bot_data.get("bitcoin_address", "N/A")),
                reply_markup=reply_markup
            )
            return
        
        return func(update, context, *args, **kwargs)
    
    return wrapper

# ========== Chat Matching ==========

def set_chat_partner(user_id: str, partner_id: str) -> None:
    """Set a chat session between two users."""
    sm = get_session_manager()
    sm.update_session(user_id, "chat", data={"partner_id": partner_id})
    sm.update_session(partner_id, "chat", data={"partner_id": user_id})

def get_chat_partner(user_id: str) -> Optional[str]:
    """Get the current chat partner of the user."""
    sm = get_session_manager()
    session = sm.get_session(user_id, "chat")
    return session["data"].get("partner_id")

def clear_chat_partner(user_id: str) -> None:
    """Clear the chat session of a user and their partner."""
    sm = get_session_manager()
    partner_id = get_chat_partner(user_id)
    sm.clear_session(user_id, "chat")
    if partner_id:
        sm.clear_session(partner_id, "chat")

# Create a global session manager instance
session_manager = None

def init_session_manager(session_file_path: str, timeout: int = 3600):
    """
    Initialize the global session manager.
    
    Args:
        session_file_path: Path to store session data
        timeout: Session timeout in seconds
    """
    global session_manager
    session_manager = SessionManager(session_file_path, timeout)
    return session_manager

def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.
    
    Returns:
        SessionManager instance
    """
    global session_manager
    if session_manager is None:
        raise RuntimeError("Session manager not initialized. Call init_session_manager first.")
    return session_manager
