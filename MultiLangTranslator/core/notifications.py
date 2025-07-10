"""
Notifications module for MultiLangTranslator Bot

This module provides advanced notification capabilities including:
- Language-specific notifications
- Admin notifications for important activities
- User payment status notifications
- System update notifications
- Scheduled notifications
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable
from telegram import Bot, ParseMode
from telegram.error import TelegramError

# Initialize logger
logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Advanced notification system for sending messages to users and admins.
    
    Features:
    - Multi-language support
    - Scheduled notifications
    - Batch sending with rate limiting
    - Error handling and retry logic
    """
    
    def __init__(self, bot: Bot, admin_ids: List[str], 
                 rate_limit: int = 30, max_retries: int = 3):
        """
        Initialize the notification manager.
        
        Args:
            bot: Telegram bot instance
            admin_ids: List of admin user IDs
            rate_limit: Maximum messages per minute
            max_retries: Maximum retry attempts for failed messages
        """
        self.bot = bot
        self.admin_ids = [str(admin_id) for admin_id in admin_ids]
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        
        # Message queue and processing
        self.message_queue = []
        self.queue_lock = threading.RLock()
        self.last_sent_time = 0
        
        # Scheduled notifications
        self.scheduled_notifications = []
        self.schedule_lock = threading.RLock()
        
        # Start worker threads
        self.queue_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.queue_thread.start()
        
        self.schedule_thread = threading.Thread(target=self._process_scheduled, daemon=True)
        self.schedule_thread.start()
    
    def notify_user(self, user_id: str, message: str, 
                   parse_mode: str = ParseMode.HTML,
                   reply_markup: Any = None) -> bool:
        """
        Send notification to a user.
        
        Args:
            user_id: Telegram user ID
            message: Message text
            parse_mode: Message parse mode
            reply_markup: Optional reply markup
            
        Returns:
            True if message was queued, False otherwise
        """
        with self.queue_lock:
            self.message_queue.append({
                "user_id": str(user_id),
                "message": message,
                "parse_mode": parse_mode,
                "reply_markup": reply_markup,
                "retries": 0
            })
            return True
    
    def notify_admins(self, message: str, 
                     parse_mode: str = ParseMode.HTML,
                     reply_markup: Any = None) -> bool:
        """
        Send notification to all admins.
        
        Args:
            message: Message text
            parse_mode: Message parse mode
            reply_markup: Optional reply markup
            
        Returns:
            True if messages were queued, False otherwise
        """
        success = True
        for admin_id in self.admin_ids:
            success = success and self.notify_user(
                admin_id, message, parse_mode, reply_markup
            )
        return success
    
    def notify_users(self, user_ids: List[str], message: str,
                    parse_mode: str = ParseMode.HTML,
                    reply_markup: Any = None) -> bool:
        """
        Send notification to multiple users.
        
        Args:
            user_ids: List of Telegram user IDs
            message: Message text
            parse_mode: Message parse mode
            reply_markup: Optional reply markup
            
        Returns:
            True if all messages were queued, False otherwise
        """
        success = True
        for user_id in user_ids:
            success = success and self.notify_user(
                user_id, message, parse_mode, reply_markup
            )
        return success
    
    def schedule_notification(self, timestamp: int, user_id: str, message: str,
                             parse_mode: str = ParseMode.HTML,
                             reply_markup: Any = None) -> int:
        """
        Schedule a notification for future delivery.
        
        Args:
            timestamp: Unix timestamp for delivery
            user_id: Telegram user ID
            message: Message text
            parse_mode: Message parse mode
            reply_markup: Optional reply markup
            
        Returns:
            Notification ID
        """
        notification_id = int(time.time() * 1000)  # Unique ID based on current time
        
        with self.schedule_lock:
            self.scheduled_notifications.append({
                "id": notification_id,
                "timestamp": timestamp,
                "user_id": str(user_id),
                "message": message,
                "parse_mode": parse_mode,
                "reply_markup": reply_markup
            })
            # Sort by timestamp
            self.scheduled_notifications.sort(key=lambda x: x["timestamp"])
        
        return notification_id
    
    def cancel_scheduled_notification(self, notification_id: int) -> bool:
        """
        Cancel a scheduled notification.
        
        Args:
            notification_id: ID of the notification to cancel
            
        Returns:
            True if notification was found and canceled, False otherwise
        """
        with self.schedule_lock:
            for i, notification in enumerate(self.scheduled_notifications):
                if notification["id"] == notification_id:
                    del self.scheduled_notifications[i]
                    return True
            return False
    
    def _process_queue(self):
        """Background thread to process the message queue with rate limiting."""
        while True:
            try:
                # Check if there are messages to send
                with self.queue_lock:
                    if not self.message_queue:
                        time.sleep(1)
                        continue
                
                # Rate limiting
                current_time = time.time()
                time_since_last = current_time - self.last_sent_time
                if time_since_last < (60 / self.rate_limit):
                    sleep_time = (60 / self.rate_limit) - time_since_last
                    time.sleep(sleep_time)
                
                # Get next message
                with self.queue_lock:
                    if not self.message_queue:
                        continue
                    message_data = self.message_queue.pop(0)
                
                # Send message
                try:
                    self.bot.send_message(
                        chat_id=message_data["user_id"],
                        text=message_data["message"],
                        parse_mode=message_data["parse_mode"],
                        reply_markup=message_data["reply_markup"]
                    )
                    self.last_sent_time = time.time()
                
                except TelegramError as e:
                    logger.error(f"Error sending notification to {message_data['user_id']}: {e}")
                    
                    # Retry logic
                    if message_data["retries"] < self.max_retries:
                        message_data["retries"] += 1
                        with self.queue_lock:
                            self.message_queue.append(message_data)
                
            except Exception as e:
                logger.error(f"Error in notification queue processing: {e}")
                time.sleep(5)  # Avoid tight loop on error
    
    def _process_scheduled(self):
        """Background thread to process scheduled notifications."""
        while True:
            try:
                current_time = time.time()
                to_send = []
                
                # Find notifications that are due
                with self.schedule_lock:
                    i = 0
                    while i < len(self.scheduled_notifications):
                        if self.scheduled_notifications[i]["timestamp"] <= current_time:
                            to_send.append(self.scheduled_notifications[i])
                            del self.scheduled_notifications[i]
                        else:
                            i += 1
                
                # Queue notifications for sending
                for notification in to_send:
                    self.notify_user(
                        notification["user_id"],
                        notification["message"],
                        notification["parse_mode"],
                        notification["reply_markup"]
                    )
                
                # Sleep until next notification or check every minute
                with self.schedule_lock:
                    if self.scheduled_notifications:
                        next_time = self.scheduled_notifications[0]["timestamp"]
                        sleep_time = max(1, min(60, next_time - time.time()))
                    else:
                        sleep_time = 60
                
                time.sleep(sleep_time)
            
            except Exception as e:
                logger.error(f"Error in scheduled notification processing: {e}")
                time.sleep(5)  # Avoid tight loop on error

# Create a global notification manager instance
notification_manager = None

def init_notification_manager(bot: Bot, admin_ids: List[str],
                             rate_limit: int = 30, max_retries: int = 3):
    """
    Initialize the global notification manager.
    
    Args:
        bot: Telegram bot instance
        admin_ids: List of admin user IDs
        rate_limit: Maximum messages per minute
        max_retries: Maximum retry attempts for failed messages
    """
    global notification_manager
    notification_manager = NotificationManager(bot, admin_ids, rate_limit, max_retries)
    return notification_manager

def get_notification_manager() -> NotificationManager:
    """
    Get the global notification manager instance.
    
    Returns:
        NotificationManager instance
    """
    global notification_manager
    if notification_manager is None:
        raise RuntimeError("Notification manager not initialized. Call init_notification_manager first.")
    return notification_manager
