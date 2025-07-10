"""
Message forwarding module for MultiLangTranslator Bot

This module provides functionality to forward files, images, and chat logs
to a designated admin group with user identification information.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union
from telegram import Update, Message, User, Chat, ParseMode
from telegram.ext import CallbackContext
from telegram.error import TelegramError

# Initialize logger
logger = logging.getLogger(__name__)

class MessageForwarder:
    """
    Handles forwarding of messages, files, and chat logs to admin group.
    """
    
    def __init__(self, bot, target_group_id: str):
        """
        Initialize the message forwarder.
        
        Args:
            bot: Telegram bot instance
            target_group_id: ID of the target admin group
        """
        self.bot = bot
        self.target_group_id = target_group_id
        logger.info(f"MessageForwarder initialized with target group: {target_group_id}")
    
    def forward_message(self, message: Message, context: Optional[CallbackContext] = None) -> bool:
        """
        Forward a message to the admin group with user information.
        
        Args:
            message: Message to forward
            context: Optional callback context
            
        Returns:
            True if forwarding was successful, False otherwise
        """
        try:
            # Get user information
            user = message.from_user
            chat = message.chat
            
            # Create header with user information
            header = self._create_user_info_header(user, chat)
            
            # Send header to admin group
            self.bot.send_message(
                chat_id=self.target_group_id,
                text=header,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
            # Forward the actual message
            if message.text and not message.photo and not message.document and not message.video and not message.audio:
                # For text messages, send as new message to preserve formatting
                self.bot.send_message(
                    chat_id=self.target_group_id,
                    text=f"<b>Message:</b>\n{message.text}",
                    parse_mode=ParseMode.HTML
                )
            else:
                # For media messages, use forward_message
                message.forward(chat_id=self.target_group_id)
            
            logger.info(f"Message from user {user.id} forwarded to admin group")
            return True
            
        except TelegramError as e:
            logger.error(f"Error forwarding message: {e}")
            return False
    
    def forward_chat_log(self, user1: User, user2: User, messages: List[Dict[str, Any]]) -> bool:
        """
        Forward a chat log between two users to the admin group.
        
        Args:
            user1: First user
            user2: Second user
            messages: List of message dictionaries
            
        Returns:
            True if forwarding was successful, False otherwise
        """
        try:
            # Create header with chat information
            header = f"<b>📋 Chat Log</b>\n\n"
            header += f"<b>Between:</b>\n"
            header += f"👤 {self._format_user_info(user1)}\n"
            header += f"👤 {self._format_user_info(user2)}\n"
            header += f"<b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n"
            header += f"<b>Message Count:</b> {len(messages)}\n\n"
            header += f"<b>--- Begin Chat Log ---</b>\n"
            
            # Send header to admin group
            self.bot.send_message(
                chat_id=self.target_group_id,
                text=header,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
            # Send messages in chunks to avoid hitting message length limits
            chat_log = ""
            current_chunk = ""
            
            for msg in messages:
                sender_id = msg.get("from_user_id")
                sender_name = msg.get("from_user_name", "Unknown")
                text = msg.get("text", "")
                timestamp = msg.get("timestamp", 0)
                time_str = time.strftime('%H:%M:%S', time.localtime(timestamp))
                
                message_entry = f"[{time_str}] {sender_name} ({sender_id}): {text}\n"
                
                # Check if adding this message would exceed Telegram's message length limit
                if len(current_chunk) + len(message_entry) > 4000:
                    # Send current chunk
                    self.bot.send_message(
                        chat_id=self.target_group_id,
                        text=current_chunk,
                        parse_mode=ParseMode.HTML
                    )
                    current_chunk = message_entry
                else:
                    current_chunk += message_entry
            
            # Send any remaining messages
            if current_chunk:
                self.bot.send_message(
                    chat_id=self.target_group_id,
                    text=current_chunk,
                    parse_mode=ParseMode.HTML
                )
            
            # Send footer
            footer = f"<b>--- End Chat Log ---</b>"
            self.bot.send_message(
                chat_id=self.target_group_id,
                text=footer,
                parse_mode=ParseMode.HTML
            )
            
            logger.info(f"Chat log between users {user1.id} and {user2.id} forwarded to admin group")
            return True
            
        except TelegramError as e:
            logger.error(f"Error forwarding chat log: {e}")
            return False
    
    def forward_file(self, file_id: str, file_type: str, caption: str, user: User) -> bool:
        """
        Forward a file to the admin group with user information.
        
        Args:
            file_id: Telegram file ID
            file_type: Type of file (photo, document, video, audio)
            caption: Caption for the file
            user: User who sent the file
            
        Returns:
            True if forwarding was successful, False otherwise
        """
        try:
            # Create header with user information
            header = self._create_user_info_header(user, None)
            header += f"\n<b>File Type:</b> {file_type.capitalize()}"
            
            # Send header to admin group
            self.bot.send_message(
                chat_id=self.target_group_id,
                text=header,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ ترقية هذا المستخدم", callback_data=f"toggle_premium_{user.id}")
                ]])
            )
            
            # Forward the file based on type
            if file_type == "photo":
                self.bot.send_photo(
                    chat_id=self.target_group_id,
                    photo=file_id,
                    caption=caption
                )
            elif file_type == "document":
                self.bot.send_document(
                    chat_id=self.target_group_id,
                    document=file_id,
                    caption=caption
                )
            elif file_type == "video":
                self.bot.send_video(
                    chat_id=self.target_group_id,
                    video=file_id,
                    caption=caption
                )
            elif file_type == "audio":
                self.bot.send_audio(
                    chat_id=self.target_group_id,
                    audio=file_id,
                    caption=caption
                )
            else:
                logger.warning(f"Unknown file type: {file_type}")
                return False
            
            logger.info(f"File from user {user.id} forwarded to admin group")
            return True
            
        except TelegramError as e:
            logger.error(f"Error forwarding file: {e}")
            return False
    
    def _create_user_info_header(self, user: User, chat: Optional[Chat] = None) -> str:
        """
        Create a header with user information.
        
        Args:
            user: User object
            chat: Optional chat object
            
        Returns:
            Formatted header string
        """
        header = f"<b>📨 Forwarded Message</b>\n\n"
        header += f"<b>From User:</b>\n"
        header += self._format_user_info(user)
        
        if chat and chat.type != "private":
            header += f"\n\n<b>From Chat:</b>\n"
            header += f"<b>Chat ID:</b> {chat.id}\n"
            header += f"<b>Chat Type:</b> {chat.type}\n"
            header += f"<b>Chat Title:</b> {chat.title}\n"
        
        header += f"\n<b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
        
        return header
    
    def _format_user_info(self, user: User) -> str:
        """
        Format user information.
        
        Args:
            user: User object
            
        Returns:
            Formatted user information string
        """
        info = f"<b>User ID:</b> {user.id}\n"
        info += f"<b>Name:</b> {user.first_name}"
        
        if user.last_name:
            info += f" {user.last_name}"
        
        if user.username:
            info += f" (@{user.username})"
        
        if user.language_code:
            info += f"\n<b>Language:</b> {user.language_code}"
        
        return info

# Global instance
_message_forwarder = None

def init_message_forwarder(bot, target_group_id: str) -> MessageForwarder:
    """
    Initialize the message forwarder.
    
    Args:
        bot: Telegram bot instance
        target_group_id: ID of the target admin group
        
    Returns:
        MessageForwarder instance
    """
    global _message_forwarder
    if _message_forwarder is None:
        _message_forwarder = MessageForwarder(bot, target_group_id)
    return _message_forwarder

def get_message_forwarder() -> MessageForwarder:
    """
    Get the message forwarder instance.
    
    Returns:
        MessageForwarder instance
    """
    global _message_forwarder
    if _message_forwarder is None:
        raise RuntimeError("Message forwarder not initialized")
    return _message_forwarder
