"""
Menu handlers module for MultiLangTranslator Bot

This module provides menu-related functionality including:
- Dynamic keyboard creation
- Menu command handling
- Menu item actions
"""

import logging
from typing import Dict, List, Any, Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ParseMode
from telegram.ext import CallbackContext

# Import core modules
from core.session import require_profile
from core.database import get_database_manager
from localization import get_text

# Initialize logger
logger = logging.getLogger(__name__)


def create_main_keyboard(user_id: str) -> List[List[KeyboardButton]]:
    """
    Create a dynamic main keyboard based on user's language and permissions.
    
    Args:
        user_id: User ID
        
    Returns:
        Keyboard layout with buttons
    """
    # Get database manager
    db_manager = get_database_manager()

    # Get user data
    user_data = db_manager.get_user_data(user_id)

    # Check if user has premium
    is_premium = user_data.get("premium", False)

    # Create keyboard
    keyboard = [[
        KeyboardButton(get_text(user_id, "menu_profile")),
        KeyboardButton(get_text(user_id, "menu_search"))
    ],
                [
                    KeyboardButton(get_text(user_id, "menu_payment")),
                    KeyboardButton(get_text(user_id, "menu_help"))
                ], [KeyboardButton(get_text(user_id, "menu_settings"))]]

    # Add premium-only buttons if user has premium
    if is_premium:
        keyboard[2].append(
            KeyboardButton(get_text(user_id, "menu_premium_features")))

    return keyboard


@require_profile
def menu_command(update: Update, context: CallbackContext) -> None:
    """Handle the /menu command to show the main menu."""
    user = update.effective_user
    user_id = str(user.id)

    # Create keyboard
    keyboard = create_main_keyboard(user_id)

    # Send menu message
    update.message.reply_text(get_text(user_id, "main_menu_text"),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard, resize_keyboard=True))


def hide_menu_command(update: Update, context: CallbackContext) -> None:
    """Handle the /hidemenu command to hide the main menu."""
    user = update.effective_user
    user_id = str(user.id)

    update.message.reply_text(get_text(user_id, "menu_hidden"),
                              reply_markup=ReplyKeyboardRemove())


def handle_menu_selection(update: Update, context: CallbackContext) -> None:
    from handlers.user_handlers import (start_update_language,
                                        start_update_gender,
                                        start_update_region,
                                        start_update_country)
    """
    Handle menu item selection from the main keyboard.
    
    This function routes menu selections to the appropriate handlers.
    """
    user = update.effective_user
    user_id = str(user.id)
    text = update.message.text
    print(f"[DEBUG] Received text from user: {text!r}")

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
        
    elif text == get_text(user_id, "menu_search"):
        from handlers.search_handlers import start_partner_search
        return start_partner_search(update, context)


    elif text == get_text(user_id, "menu_help"):
        # Call help handler
        from handlers.user_handlers import help_command
        help_command(update, context)

    elif text == get_text(user_id, "menu_settings"):
        # Call settings handler
        from handlers.user_handlers import settings_command
        settings_command(update, context)
    elif text == get_text(user_id, "update_language"):
        return start_update_language(update, context)

    elif text == get_text(user_id, "update_gender"):
        return start_update_gender(update, context)

    elif text == get_text(user_id, "update_region"):
        return start_update_region(update, context)

    elif text == get_text(user_id, "update_country"):
        return start_update_country(update, context)

    elif text == get_text(user_id, "menu_premium_features"):
        # Check if user has premium
        if user_data.get("premium", False):
            # Show premium features
            show_premium_features(update, context)
        else:
            # Redirect to payment
            from handlers.payment_handlers import payment_command
            payment_command(update, context)
    else:
        # إذا لم يكن النص يطابق أي زر معروف
        update.message.reply_text(
            "❗ لم أفهم اختيارك من القائمة. يرجى استخدام الأزرار الموجودة فقط.")


def show_premium_features(update: Update, context: CallbackContext) -> None:
    """Show premium features to premium users."""
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
    update.message.reply_text(message, parse_mode=ParseMode.HTML)


# Register handlers
def register_menu_handlers(dispatcher):
    """Register all menu handlers with the dispatcher."""
    from telegram.ext import CommandHandler, MessageHandler, Filters

    # Menu command
    dispatcher.add_handler(CommandHandler("menu", menu_command))

    # Hide menu command
    dispatcher.add_handler(CommandHandler("hidemenu", hide_menu_command))

    # Menu selection handler
    # This should be added after all other handlers to avoid conflicts
    menu_handler = MessageHandler(Filters.text & ~Filters.command,
                                  handle_menu_selection)
