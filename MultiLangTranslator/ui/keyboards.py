"""
UI module for MultiLangTranslator Bot

This module provides user interface components including:
- Dynamic keyboard generation
- Menu layouts
- Message templates
"""

import logging
from typing import Dict, List, Any, Optional
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

# Import core modules
from core.database import get_database_manager
from localization import get_text

# Initialize logger
logger = logging.getLogger(__name__)

class KeyboardManager:
    """
    Manager for creating dynamic keyboards based on user language and permissions.
    """
    
    @staticmethod
    def create_main_keyboard(user_id: str) -> ReplyKeyboardMarkup:
        """
        Create the main menu keyboard for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            ReplyKeyboardMarkup with appropriate buttons
        """
        # Get database manager
        db_manager = get_database_manager()
        
        # Get user data
        user_data = db_manager.get_user_data(user_id)
        
        # Check if user has premium
        is_premium = user_data.get("premium", False)
        
        # Create keyboard
        keyboard = [
            [
                KeyboardButton(get_text(user_id, "menu_profile")),
                KeyboardButton(get_text(user_id, "menu_search"))
            ],
            [
                KeyboardButton(get_text(user_id, "menu_payment")),
                KeyboardButton(get_text(user_id, "menu_help"))
            ],
            [
                KeyboardButton(get_text(user_id, "menu_settings"))
            ]
        ]
        
        # Add premium-only buttons if user has premium
        if is_premium:
            keyboard[2].append(KeyboardButton(get_text(user_id, "menu_premium_features")))
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def create_language_keyboard() -> ReplyKeyboardMarkup:
        """
        Create a keyboard with supported languages.
        
        Returns:
            ReplyKeyboardMarkup with language buttons
        """
        from config import SUPPORTED_LANGUAGES
        
        keyboard = [[KeyboardButton(name)] for code, name in SUPPORTED_LANGUAGES.items()]
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    @staticmethod
    def create_gender_keyboard(user_id: str) -> ReplyKeyboardMarkup:
        """
        Create a keyboard with gender options.
        
        Args:
            user_id: User ID for localization
            
        Returns:
            ReplyKeyboardMarkup with gender buttons
        """
        keyboard = [
            [KeyboardButton(get_text(user_id, "male"))],
            [KeyboardButton(get_text(user_id, "female"))],
            [KeyboardButton(get_text(user_id, "other"))]
        ]
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    @staticmethod
    def create_region_keyboard(regions: List[str]) -> ReplyKeyboardMarkup:
        """
        Create a keyboard with region options.
        
        Args:
            regions: List of region names
            
        Returns:
            ReplyKeyboardMarkup with region buttons
        """
        keyboard = [[KeyboardButton(region)] for region in regions]
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    @staticmethod
    def create_country_keyboard(countries: List[str], user_id: str) -> ReplyKeyboardMarkup:
        """
        Create a keyboard with country options.
        
        Args:
            countries: List of country names
            user_id: User ID for localization
            
        Returns:
            ReplyKeyboardMarkup with country buttons
        """
        # Split countries into chunks of 3 for better keyboard layout
        keyboard = []
        row = []
        
        for i, country in enumerate(countries):
            row.append(KeyboardButton(country))
            
            if (i + 1) % 3 == 0 or i == len(countries) - 1:
                keyboard.append(row)
                row = []
        
        # Add "Any Country" option
        keyboard.append([KeyboardButton(get_text(user_id, "any_country"))])
        
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    @staticmethod
    def create_settings_keyboard(user_id: str) -> InlineKeyboardMarkup:
        """
        Create a keyboard with settings options.
        
        Args:
            user_id: User ID for localization
            
        Returns:
            InlineKeyboardMarkup with settings buttons
        """
        # Get database manager
        db_manager = get_database_manager()
        
        # Get user data
        user_data = db_manager.get_user_data(user_id)
        
        # Check notification setting
        notifications_enabled = user_data.get("notifications_enabled", True)
        
        keyboard = [
            [
                InlineKeyboardButton(get_text(user_id, "change_language"), callback_data="settings_language"),
                InlineKeyboardButton(
                    get_text(user_id, "disable_notifications") if notifications_enabled else get_text(user_id, "enable_notifications"), 
                    callback_data="settings_notifications"
                )
            ],
            [
                InlineKeyboardButton(get_text(user_id, "update_profile"), callback_data="settings_profile")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def create_admin_dashboard_keyboard(user_id: str) -> InlineKeyboardMarkup:
        """
        Create a keyboard for admin dashboard.
        
        Args:
            user_id: User ID for localization
            
        Returns:
            InlineKeyboardMarkup with admin dashboard buttons
        """
        keyboard = [
            [
                InlineKeyboardButton(get_text(user_id, "admin_users"), callback_data="admin_users"),
                InlineKeyboardButton(get_text(user_id, "admin_payments"), callback_data="admin_payments")
            ],
            [
                InlineKeyboardButton(get_text(user_id, "admin_stats"), callback_data="admin_stats"),
                InlineKeyboardButton(get_text(user_id, "admin_status"), callback_data="admin_status")
            ],
            [
                InlineKeyboardButton(get_text(user_id, "admin_broadcast"), callback_data="admin_broadcast"),
                InlineKeyboardButton(get_text(user_id, "admin_settings"), callback_data="admin_settings")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)

class MessageTemplates:
    """
    Templates for common messages with proper formatting.
    """
    
    @staticmethod
    def welcome_message(user_id: str, name: str) -> str:
        """
        Create a welcome message for returning users.
        
        Args:
            user_id: User ID for localization
            name: User's name
            
        Returns:
            Formatted welcome message
        """
        return get_text(user_id, "welcome_existing_user", name=name)
    
    @staticmethod
    def new_user_welcome(user_id: str) -> str:
        """
        Create a welcome message for new users.
        
        Args:
            user_id: User ID for localization
            
        Returns:
            Formatted welcome message
        """
        return get_text(user_id, "welcome_new_user")
    
    @staticmethod
    def profile_complete(user_id: str) -> str:
        """
        Create a profile completion message.
        
        Args:
            user_id: User ID for localization
            
        Returns:
            Formatted profile completion message
        """
        return get_text(user_id, "profile_complete")
    
    @staticmethod
    def help_message(user_id: str) -> str:
        """
        Create a help message with all commands.
        
        Args:
            user_id: User ID for localization
            
        Returns:
            Formatted help message
        """
        message = f"<b>{get_text(user_id, 'help_title')}</b>\n\n"
        
        # Basic commands
        message += f"<b>{get_text(user_id, 'basic_commands')}</b>\n"
        message += f"/start - {get_text(user_id, 'help_start')}\n"
        message += f"/menu - {get_text(user_id, 'help_menu')}\n"
        message += f"/help - {get_text(user_id, 'help_help')}\n"
        message += f"/cancel - {get_text(user_id, 'help_cancel')}\n\n"
        
        # Profile commands
        message += f"<b>{get_text(user_id, 'profile_commands')}</b>\n"
        message += f"/profile - {get_text(user_id, 'help_profile')}\n\n"
        
        # Search commands
        message += f"<b>{get_text(user_id, 'search_commands')}</b>\n"
        message += f"/search - {get_text(user_id, 'help_search')}\n\n"
        
        # Payment commands
        message += f"<b>{get_text(user_id, 'payment_commands')}</b>\n"
        message += f"/payment - {get_text(user_id, 'help_payment')}\n\n"
        
        # Settings commands
        message += f"<b>{get_text(user_id, 'settings_commands')}</b>\n"
        message += f"/settings - {get_text(user_id, 'help_settings')}\n\n"
        
        # Additional info
        message += get_text(user_id, 'help_additional_info')
        
        return message
    
    @staticmethod
    def settings_message(user_id: str, language_name: str, notifications_enabled: bool) -> str:
        """
        Create a settings message.
        
        Args:
            user_id: User ID for localization
            language_name: Name of user's language
            notifications_enabled: Whether notifications are enabled
            
        Returns:
            Formatted settings message
        """
        message = f"<b>{get_text(user_id, 'settings_title')}</b>\n\n"
        
        # Language setting
        message += f"🗣️ {get_text(user_id, 'language')}: {language_name}\n"
        
        # Notifications setting
        notifications_status = get_text(user_id, "enabled") if notifications_enabled else get_text(user_id, "disabled")
        message += f"🔔 {get_text(user_id, 'notifications')}: {notifications_status}\n"
        
        return message
    
    @staticmethod
    def profile_info(user_id: str, user_data: Dict[str, Any]) -> str:
        """
        Create a profile info message.
        
        Args:
            user_id: User ID for localization
            user_data: User data dictionary
            
        Returns:
            Formatted profile info message
        """
        message = f"<b>{get_text(user_id, 'current_profile')}</b>\n\n"
        message += f"🗣️ {get_text(user_id, 'language')}: {user_data.get('language', 'N/A')}\n"
        message += f"👤 {get_text(user_id, 'gender')}: {user_data.get('gender', 'N/A')}\n"
        message += f"🌍 {get_text(user_id, 'region')}: {user_data.get('region', 'N/A')}\n"
        message += f"🏙️ {get_text(user_id, 'country')}: {user_data.get('country', 'N/A')}\n\n"
        message += get_text(user_id, "select_field_to_update")
        
        return message
