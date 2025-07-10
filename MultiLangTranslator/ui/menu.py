"""
Menu module for MultiLangTranslator Bot

This module provides menu-related functionality including:
- Menu display and hiding
- Menu item handling
"""

import logging
from typing import Dict, List, Any, Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ParseMode
from telegram.ext import CallbackContext

# Import core modules
from core.session import require_profile
from core.database import get_database_manager
from localization import get_text
from ui.keyboards import KeyboardManager

# Initialize logger
logger = logging.getLogger(__name__)

@require_profile
def menu_command(update: Update, context: CallbackContext) -> None:
    """
    Handle the /menu command to show the main menu.
    
    This command displays the main menu with all available options
    based on the user's language and permissions.
    """
    user = update.effective_user
    user_id = str(user.id)
    
    # Create keyboard using KeyboardManager
    keyboard = KeyboardManager.create_main_keyboard(user_id)
    
    # Send menu message
    update.message.reply_text(
        get_text(user_id, "main_menu_text"),
        reply_markup=keyboard
    )

def hide_menu_command(update: Update, context: CallbackContext) -> None:
    """
    Handle the /hidemenu command to hide the main menu.
    
    This command removes the keyboard and displays a confirmation message.
    """
    user = update.effective_user
    user_id = str(user.id)
    
    update.message.reply_text(
        get_text(user_id, "menu_hidden"),
        reply_markup=ReplyKeyboardRemove()
    )

def handle_menu_selection(update: Update, context: CallbackContext) -> None:
    """
    Handle menu item selection from the main keyboard.
    
    This function routes menu selections to the appropriate handlers
    based on the text of the selected menu item.
    """
    user = update.effective_user
    user_id = str(user.id)
    text = update.message.text
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Get user data
    user_data = db_manager.get_user_data(user_id)
    
    # Check which menu item was selected
    if text == get_text(user_id, "menu_profile"):
        # Call profile update handler
        from handlers.user_handlers import update_profile_command
        update_profile_command(update, context)
    
    elif text == get_text(user_id, "menu_search"):
        # Call search handler
        from handlers.search_handlers import start_partner_search
        start_partner_search(update, context)
    
    elif text == get_text(user_id, "menu_payment"):
        # Call payment handler
        from handlers.payment_handlers import payment_command
        payment_command(update, context)
    
    elif text == get_text(user_id, "menu_help"):
        # Call help handler
        from handlers.user_handlers import help_command
        help_command(update, context)
    
    elif text == get_text(user_id, "menu_settings"):
        # Call settings handler
        from handlers.user_handlers import settings_command
        settings_command(update, context)
    
    elif text == get_text(user_id, "menu_premium_features"):
        # Check if user has premium
        if user_data.get("premium", False):
            # Show premium features
            show_premium_features(update, context)
        else:
            # Redirect to payment
            from handlers.payment_handlers import payment_command
            payment_command(update, context)
    
    elif text == get_text(user_id, "menu_hide"):
        # Hide menu
        hide_menu_command(update, context)
    
    else:
        # Unknown menu item, ignore
        pass

def show_premium_features(update: Update, context: CallbackContext) -> None:
    """
    Show premium features to premium users.
    
    This function displays a list of premium features available to the user.
    """
    user = update.effective_user
    user_id = str(user.id)
    
    # Create premium features message
    message = f"<b>{get_text(user_id, 'premium_features_title')}</b>\n\n"
    message += f"✅ {get_text(user_id, 'premium_feature_1')}\n"
    message += f"✅ {get_text(user_id, 'premium_feature_2')}\n"
    message += f"✅ {get_text(user_id, 'premium_feature_3')}\n"
    message += f"✅ {get_text(user_id, 'premium_feature_4')}\n\n"
    message += get_text(user_id, 'premium_features_footer')
    
    # Send message
    update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML
    )

# Register handlers
def register_menu_handlers(dispatcher):
    """
    Register all menu handlers with the dispatcher.
    
    Args:
        dispatcher: Telegram dispatcher
        
    Returns:
        Menu handler for text messages (should be registered last)
    """
    from telegram.ext import CommandHandler, MessageHandler, Filters
    
    # Menu command
    dispatcher.add_handler(CommandHandler("menu", menu_command))
    
    # Hide menu command
    dispatcher.add_handler(CommandHandler("hidemenu", hide_menu_command))
    
    # Menu selection handler
    # This should be added after all other handlers to avoid conflicts
    menu_handler = MessageHandler(
        Filters.text & ~Filters.command & Filters.regex(r'^(.*menu_.*|.*settings|.*profile|.*search|.*payment|.*help)$'),
        handle_menu_selection
    )
    
    # Return for later registration (should be registered last)
    return menu_handler
