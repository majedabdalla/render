"""
Security module for MultiLangTranslator Bot

This module provides spam protection, rate limiting, and other security features.
"""

import time
import logging
import threading
from typing import Dict, List, Set, Tuple, Optional
import re

# Initialize logger
logger = logging.getLogger(__name__)

class SpamProtection:
    """
    Advanced spam protection system with rate limiting, pattern detection,
    and automatic blocking capabilities.
    """
    
    def __init__(self, 
                 rate_limit_window: int = 60,
                 rate_limit_max_messages: int = 20,
                 pattern_threshold: int = 3,
                 block_duration: int = 3600):
        """
        Initialize spam protection.
        
        Args:
            rate_limit_window: Time window for rate limiting in seconds
            rate_limit_max_messages: Maximum messages allowed in window
            pattern_threshold: Number of repeated patterns to trigger warning
            block_duration: Duration of automatic blocks in seconds
        """
        self.rate_limit_window = rate_limit_window
        self.rate_limit_max_messages = rate_limit_max_messages
        self.pattern_threshold = pattern_threshold
        self.block_duration = block_duration
        
        # Message tracking
        self.user_messages = {}  # user_id -> list of (timestamp, message)
        self.blocked_users = {}  # user_id -> unblock_time
        self.warning_counts = {}  # user_id -> warning count
        
        # Blacklisted patterns
        self.blacklisted_words = set()
        self.blacklisted_patterns = []
        
        # Thread lock
        self.lock = threading.RLock()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_data, daemon=True)
        self.cleanup_thread.start()
    
    def add_blacklisted_word(self, word: str):
        """Add a word to the blacklist."""
        with self.lock:
            self.blacklisted_words.add(word.lower())
    
    def add_blacklisted_pattern(self, pattern: str):
        """Add a regex pattern to the blacklist."""
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            with self.lock:
                self.blacklisted_patterns.append(compiled)
        except re.error as e:
            logger.error(f"Invalid regex pattern: {pattern}, error: {e}")
    
    def load_blacklist(self, words: List[str], patterns: List[str]):
        """Load blacklisted words and patterns."""
        with self.lock:
            self.blacklisted_words = set(word.lower() for word in words)
            self.blacklisted_patterns = []
            for pattern in patterns:
                try:
                    self.blacklisted_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.error(f"Invalid regex pattern: {pattern}, error: {e}")
    
    def check_message(self, user_id: str, message_text: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a message is spam.
        
        Args:
            user_id: User ID
            message_text: Message text
            
        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        user_id_str = str(user_id)
        
        with self.lock:
            # Check if user is blocked
            if user_id_str in self.blocked_users:
                unblock_time = self.blocked_users[user_id_str]
                if time.time() < unblock_time:
                    remaining = int(unblock_time - time.time())
                    return False, f"You are temporarily blocked. Try again in {remaining} seconds."
                else:
                    # Unblock if time has passed
                    del self.blocked_users[user_id_str]
            
            # Check for blacklisted words
            lower_text = message_text.lower()
            for word in self.blacklisted_words:
                if word in lower_text:
                    self._add_warning(user_id_str)
                    return False, "Message contains prohibited content."
            
            # Check for blacklisted patterns
            for pattern in self.blacklisted_patterns:
                if pattern.search(message_text):
                    self._add_warning(user_id_str)
                    return False, "Message matches a prohibited pattern."
            
            # Initialize user message history if not exists
            if user_id_str not in self.user_messages:
                self.user_messages[user_id_str] = []
            
            # Add current message
            current_time = time.time()
            self.user_messages[user_id_str].append((current_time, message_text))
            
            # Check rate limiting
            window_start = current_time - self.rate_limit_window
            messages_in_window = [msg for ts, msg in self.user_messages[user_id_str] if ts > window_start]
            
            if len(messages_in_window) > self.rate_limit_max_messages:
                self._add_warning(user_id_str)
                return False, f"Rate limit exceeded. Please wait before sending more messages."
            
            # Check for repeated messages
            if len(messages_in_window) >= 3:
                # Count occurrences of each message
                message_counts = {}
                for msg in messages_in_window:
                    message_counts[msg] = message_counts.get(msg, 0) + 1
                
                # Check if any message is repeated too many times
                for msg, count in message_counts.items():
                    if count >= self.pattern_threshold:
                        self._add_warning(user_id_str)
                        return False, "Repeated message pattern detected."
            
            # Message is allowed
            return True, None
    
    def _add_warning(self, user_id: str):
        """
        Add a warning for a user and block if threshold reached.
        
        Args:
            user_id: User ID
        """
        if user_id not in self.warning_counts:
            self.warning_counts[user_id] = 0
        
        self.warning_counts[user_id] += 1
        
        # Block user if too many warnings
        if self.warning_counts[user_id] >= 3:
            self.block_user(user_id, self.block_duration)
            self.warning_counts[user_id] = 0
    
    def block_user(self, user_id: str, duration: int = None):
        """
        Block a user for a specified duration.
        
        Args:
            user_id: User ID
            duration: Block duration in seconds (default: self.block_duration)
        """
        if duration is None:
            duration = self.block_duration
        
        with self.lock:
            self.blocked_users[str(user_id)] = time.time() + duration
            logger.info(f"Blocked user {user_id} for {duration} seconds")
    
    def unblock_user(self, user_id: str) -> bool:
        """
        Unblock a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user was blocked and now unblocked, False if user wasn't blocked
        """
        user_id_str = str(user_id)
        with self.lock:
            if user_id_str in self.blocked_users:
                del self.blocked_users[user_id_str]
                logger.info(f"Unblocked user {user_id}")
                return True
            return False
    
    def is_user_blocked(self, user_id: str) -> bool:
        """
        Check if a user is currently blocked.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user is blocked, False otherwise
        """
        user_id_str = str(user_id)
        with self.lock:
            if user_id_str in self.blocked_users:
                if time.time() < self.blocked_users[user_id_str]:
                    return True
                else:
                    # Unblock if time has passed
                    del self.blocked_users[user_id_str]
            return False
    
    def get_blocked_users(self) -> Dict[str, int]:
        """
        Get all currently blocked users with remaining block time.
        
        Returns:
            Dictionary of user_id -> remaining block time in seconds
        """
        current_time = time.time()
        blocked = {}
        
        with self.lock:
            for user_id, unblock_time in list(self.blocked_users.items()):
                if current_time < unblock_time:
                    blocked[user_id] = int(unblock_time - current_time)
                else:
                    # Clean up expired blocks
                    del self.blocked_users[user_id]
        
        return blocked
    
    def _cleanup_old_data(self):
        """Background thread to periodically clean up old message data."""
        while True:
            try:
                time.sleep(300)  # Run every 5 minutes
                
                with self.lock:
                    current_time = time.time()
                    cutoff_time = current_time - (self.rate_limit_window * 2)
                    
                    # Clean up old messages
                    for user_id in list(self.user_messages.keys()):
                        self.user_messages[user_id] = [
                            (ts, msg) for ts, msg in self.user_messages[user_id]
                            if ts > cutoff_time
                        ]
                        
                        # Remove empty lists
                        if not self.user_messages[user_id]:
                            del self.user_messages[user_id]
                    
                    # Clean up expired blocks
                    for user_id in list(self.blocked_users.keys()):
                        if current_time > self.blocked_users[user_id]:
                            del self.blocked_users[user_id]
                    
                    # Reset old warning counts
                    for user_id in list(self.warning_counts.keys()):
                        if user_id not in self.user_messages:
                            del self.warning_counts[user_id]
                
            except Exception as e:
                logger.error(f"Error in spam protection cleanup: {e}")

# Create a global spam protection instance
spam_protection = None

def init_spam_protection(
    rate_limit_window: int = 60,
    rate_limit_max_messages: int = 20,
    pattern_threshold: int = 3,
    block_duration: int = 3600
):
    """
    Initialize the global spam protection system.
    
    Args:
        rate_limit_window: Time window for rate limiting in seconds
        rate_limit_max_messages: Maximum messages allowed in window
        pattern_threshold: Number of repeated patterns to trigger warning
        block_duration: Duration of automatic blocks in seconds
    """
    global spam_protection
    spam_protection = SpamProtection(
        rate_limit_window=rate_limit_window,
        rate_limit_max_messages=rate_limit_max_messages,
        pattern_threshold=pattern_threshold,
        block_duration=block_duration
    )
    return spam_protection

def get_spam_protection() -> SpamProtection:
    """
    Get the global spam protection instance.
    
    Returns:
        SpamProtection instance
    """
    global spam_protection
    if spam_protection is None:
        raise RuntimeError("Spam protection not initialized. Call init_spam_protection first.")
    return spam_protection
