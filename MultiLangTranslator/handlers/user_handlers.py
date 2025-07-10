"""
User handlers module for MultiLangTranslator Bot

This module provides advanced user command functionality including:
- Profile management
- Menu navigation
- Advanced search features
- Settings management
- Help and support
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional, Union
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from handlers.menu_handlers import create_main_keyboard
from localization import get_text
from telegram.ext import CallbackContext, MessageHandler, Filters
from telegram.ext import ConversationHandler
from data_handler import update_user_data, get_user_data
from core.session import require_profile
from core.database import get_database_manager
from core.notifications import get_notification_manager
from core.security import get_spam_protection
from core.session import get_session_manager
from core.session import get_chat_partner, clear_chat_partner

# Import core modules
from core.session import get_session_manager, require_profile, require_premium
from core.database import get_database_manager
from core.security import get_spam_protection
from core.notifications import get_notification_manager
from localization import get_text
from core.session import get_chat_partner, clear_chat_partner
from handlers.menu_handlers import (menu_command, create_main_keyboard, handle_menu_selection,)

# Initialize logger
logger = logging.getLogger(__name__)


# Start command handler
def start(update: Update, context: CallbackContext) -> int:
    """
    Handle the /start command.
    
    This is the entry point for new users and returning users.
    For new users, it starts the profile creation process.
    For returning users, it shows a welcome back message and the main menu.
    """
    user = update.effective_user
    user_id = str(user.id)

    # Get database manager
    db_manager = get_database_manager()

    # Get user data
    user_data = db_manager.get_user_data(user_id)

    # Check if user has a complete profile
    required_fields = ["language", "gender", "region", "country"]
    has_profile = all(field in user_data for field in required_fields)

    if has_profile:
        # User has a profile, show welcome back message
        language = user_data.get("language", "en")

        # Update user name if changed
        if user.first_name and (user_data.get("name") != user.first_name):
            db_manager.update_user_data(user_id, {"name": user.first_name})

        # Send welcome back message
        update.message.reply_text(get_text(user_id,
                                           "welcome_existing_user",
                                           name=user.first_name),
                                  parse_mode=ParseMode.HTML)

        # Show main menu
        show_main_menu(update, context)

        return ConversationHandler.END
    else:
        # New user, start profile creation
        db_manager.update_user_data(user_id, {
            "name": user.first_name,
            "username": user.username,
            "language": "en",  # اللغة الافتراضية
            "profile_complete": False
        })

        # Show language selection
        languages = context.bot_data.get("supported_languages", {})
        keyboard = [[KeyboardButton(name)] for code, name in languages.items()]

        update.message.reply_text(get_text(user_id,
                                           "welcome_new_user",
                                           lang_code="en"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      keyboard, one_time_keyboard=True))

        return context.bot_data.get("SELECT_LANG", 0)


# Language selection handler
def language_selection(update: Update, context: CallbackContext) -> int:
    """Handle language selection during profile creation."""
    user = update.effective_user
    user_id = str(user.id)
    selected_language = update.message.text

    # Get database manager
    db_manager = get_database_manager()

    # Map selected language name to language code
    languages = context.bot_data.get("supported_languages", {})
    language_code = None

    for code, name in languages.items():
        if name == selected_language:
            language_code = code
            break

    if not language_code:
        # Invalid selection, ask again
        keyboard = [[KeyboardButton(name)] for code, name in languages.items()]

        update.message.reply_text(get_text(user_id,
                                           "invalid_language",
                                           lang_code="en"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      keyboard, one_time_keyboard=True))

        return context.bot_data.get("SELECT_LANG", 0)

    # Save language preference
    db_manager.update_user_data(user_id, {"language": language_code})

    # Show gender selection
    keyboard = [[KeyboardButton(get_text(user_id, "male"))],
                [KeyboardButton(get_text(user_id, "female"))],
                [KeyboardButton(get_text(user_id, "other"))]]

    update.message.reply_text(get_text(user_id, "choose_gender"),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard, one_time_keyboard=True))

    return context.bot_data.get("SELECT_GENDER", 1)


# Gender selection handler
def gender_selection(update: Update, context: CallbackContext) -> int:
    """Handle gender selection during profile creation."""
    user = update.effective_user
    user_id = str(user.id)
    selected_gender = update.message.text

    # Get database manager
    db_manager = get_database_manager()

    # Validate gender selection
    valid_genders = [
        get_text(user_id, "male"),
        get_text(user_id, "female"),
        get_text(user_id, "other")
    ]

    if selected_gender not in valid_genders:
        # Invalid selection, ask again
        keyboard = [[KeyboardButton(get_text(user_id, "male"))],
                    [KeyboardButton(get_text(user_id, "female"))],
                    [KeyboardButton(get_text(user_id, "other"))]]

        update.message.reply_text(get_text(user_id, "invalid_gender"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      keyboard, one_time_keyboard=True))

        return context.bot_data.get("SELECT_GENDER", 1)

    # Map localized gender to English
    gender_map = {
        get_text(user_id, "male"): "male",
        get_text(user_id, "female"): "female",
        get_text(user_id, "other"): "other"
    }

    # Save gender
    db_manager.update_user_data(user_id,
                                {"gender": gender_map[selected_gender]})

    # Show region selection
    regions_countries = load_regions_countries()
    regions = list(regions_countries.keys())

    keyboard = [[KeyboardButton(region)] for region in regions]

    update.message.reply_text(get_text(user_id, "choose_region"),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard, one_time_keyboard=True))

    return context.bot_data.get("SELECT_REGION", 2)


# Region selection handler
def region_selection(update: Update, context: CallbackContext) -> int:
    """Handle region selection during profile creation."""
    user = update.effective_user
    user_id = str(user.id)
    selected_region = update.message.text

    # Get database manager
    db_manager = get_database_manager()

    # Load regions and countries
    regions_countries = load_regions_countries()

    if selected_region not in regions_countries:
        # Invalid selection, ask again
        regions = list(regions_countries.keys())
        keyboard = [[KeyboardButton(region)] for region in regions]

        update.message.reply_text(get_text(user_id, "invalid_region"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      keyboard, one_time_keyboard=True))

        return context.bot_data.get("SELECT_REGION", 2)

    # Save region
    db_manager.update_user_data(user_id, {"region": selected_region})

    # Store region in context for country selection
    context.user_data["selected_region"] = selected_region

    # Show country selection
    countries = regions_countries[selected_region]

    # Split countries into chunks of 3 for better keyboard layout
    keyboard = []
    row = []

    for i, country in enumerate(countries):
        row.append(KeyboardButton(country))

        if (i + 1) % 3 == 0 or i == len(countries) - 1:
            keyboard.append(row)
            row = []

    update.message.reply_text(get_text(user_id,
                                       "choose_country_in_region",
                                       region=selected_region),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard, one_time_keyboard=True))

    return context.bot_data.get("SELECT_COUNTRY_IN_REGION", 3)


# Country selection handler
def country_selection(update: Update, context: CallbackContext) -> int:
    """Handle country selection during profile creation."""
    user = update.effective_user
    user_id = str(user.id)
    selected_country = update.message.text

    # Get database manager
    db_manager = get_database_manager()

    # Get selected region from context
    selected_region = context.user_data.get("selected_region")

    if not selected_region:
        # Something went wrong, restart from region selection
        regions_countries = load_regions_countries()
        regions = list(regions_countries.keys())

        keyboard = [[KeyboardButton(region)] for region in regions]

        update.message.reply_text(get_text(user_id, "choose_region"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      keyboard, one_time_keyboard=True))

        return context.bot_data.get("SELECT_REGION", 2)

    # Load regions and countries
    regions_countries = load_regions_countries()

    if selected_country not in regions_countries[selected_region]:
        # Invalid selection, ask again
        countries = regions_countries[selected_region]

        # Split countries into chunks of 3 for better keyboard layout
        keyboard = []
        row = []

        for i, country in enumerate(countries):
            row.append(KeyboardButton(country))

            if (i + 1) % 3 == 0 or i == len(countries) - 1:
                keyboard.append(row)
                row = []

        update.message.reply_text(
            get_text(user_id, "country_not_found_in_region"),
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

        return context.bot_data.get("SELECT_COUNTRY_IN_REGION", 3)

    # Save country
    db_manager.update_user_data(user_id, {"country": selected_country})

    # Profile complete
    update.message.reply_text(get_text(user_id, "profile_complete"),
                              reply_markup=ReplyKeyboardRemove())

    # Show main menu
    show_main_menu(update, context)

    return ConversationHandler.END


# Cancel handler
def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel current conversation."""
    user = update.effective_user
    user_id = str(user.id)

    update.message.reply_text(get_text(user_id, "cancel_profile"),
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


# Menu command handler
def menu_command(update: Update, context: CallbackContext) -> None:
    """Handle the /menu command to show the main menu."""
    show_main_menu(update, context)


# Show main menu
def show_main_menu(update: Update, context: CallbackContext) -> None:
    """Show the main menu with all available options."""
    user = update.effective_user
    user_id = str(user.id)

    # Get database manager
    db_manager = get_database_manager()

    # Get user data
    user_data = db_manager.get_user_data(user_id)

    # Create dynamic keyboard based on user's language
    language = user_data.get("language", "en")

    # Create keyboard with main menu options
    keyboard = create_main_keyboard(user_id, language)

    # Send menu message
    update.message.reply_text(get_text(user_id, "main_menu_text"),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard, resize_keyboard=True))


# Create main keyboard
def create_main_keyboard(user_id: str,
                         language: str) -> List[List[KeyboardButton]]:
    """
    Create a dynamic main keyboard based on user's language.
    
    Args:
        user_id: User ID
        language: Language code
        
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


# Hide menu
def hide_menu(update: Update, context: CallbackContext) -> None:
    """Hide the main menu."""
    user = update.effective_user
    user_id = str(user.id)

    update.message.reply_text(get_text(user_id, "menu_hidden"),
                              reply_markup=ReplyKeyboardRemove())


# Profile update command
@require_profile
def update_profile_command(update: Update, context: CallbackContext) -> int:
    """Start the profile update process."""
    user = update.effective_user
    user_id = str(user.id)

    # Get database manager
    db_manager = get_database_manager()

    # Get user data
    user_data = db_manager.get_user_data(user_id)

    # Create keyboard with profile fields
    keyboard = [[KeyboardButton(get_text(user_id, "update_language"))],
                [KeyboardButton(get_text(user_id, "update_gender"))],
                [KeyboardButton(get_text(user_id, "update_region"))],
                [KeyboardButton(get_text(user_id, "update_country"))],
                [KeyboardButton("⬅️ " + get_text(user_id, "back"))]]

    # Show current profile
    message = f"<b>{get_text(user_id, 'current_profile')}</b>\n\n"
    message += f"🗣️ {get_text(user_id, 'language')}: {user_data.get('language', 'N/A')}\n"
    message += f"👤 {get_text(user_id, 'gender')}: {user_data.get('gender', 'N/A')}\n"
    message += f"🌍 {get_text(user_id, 'region')}: {user_data.get('region', 'N/A')}\n"
    message += f"🏙️ {get_text(user_id, 'country')}: {user_data.get('country', 'N/A')}\n\n"
    message += get_text(user_id, "select_field_to_update")

    update.message.reply_text(message,
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard, one_time_keyboard=True),
                              parse_mode=ParseMode.HTML)

    # Get session manager
    session_manager = get_session_manager()

    # Update session state
    session_manager.update_session(user_id,
                                   "profile_update",
                                   state="field_selection")

    return context.bot_data.get("UPDATE_PROFILE_FIELD", 10)


# Help command
def help_command(update: Update, context: CallbackContext) -> None:
    """Show help information."""
    user = update.effective_user
    user_id = str(user.id)

    # Get database manager
    db_manager = get_database_manager()

    # Get user data
    user_data = db_manager.get_user_data(user_id)

    # Create help message
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

    # Send help message
    update.message.reply_text(message, parse_mode=ParseMode.HTML)


# Settings command
@require_profile
def settings_command(update: Update, context: CallbackContext) -> None:
    """Show and manage user settings."""
    user = update.effective_user
    user_id = str(user.id)

    # Get database manager
    db_manager = get_database_manager()

    # Get user data
    user_data = db_manager.get_user_data(user_id)

    # Create settings message
    message = f"<b>{get_text(user_id, 'settings_title')}</b>\n\n"

    # Language setting
    language = user_data.get("language", "en")
    language_name = context.bot_data.get("supported_languages",
                                         {}).get(language, language)
    message += f"🗣️ {get_text(user_id, 'language')}: {language_name}\n"

    # Notifications setting
    notifications_enabled = user_data.get("notifications_enabled", True)
    notifications_status = get_text(
        user_id, "enabled") if notifications_enabled else get_text(
            user_id, "disabled")
    message += f"🔔 {get_text(user_id, 'notifications')}: {notifications_status}\n"

    # Create inline keyboard for settings
    keyboard = [[
        InlineKeyboardButton(get_text(user_id, "change_language"),
                             callback_data="settings_language"),
        InlineKeyboardButton(
            get_text(user_id, "disable_notifications") if notifications_enabled
            else get_text(user_id, "enable_notifications"),
            callback_data="settings_notifications")
    ],
                [
                    InlineKeyboardButton(get_text(user_id, "update_profile"),
                                         callback_data="settings_profile")
                ]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send settings message
    update.message.reply_text(message,
                              reply_markup=reply_markup,
                              parse_mode=ParseMode.HTML)


# Settings callback handler
def settings_callback(update: Update, context: CallbackContext) -> None:
    """Handle settings callback queries."""
    query = update.callback_query
    query.answer()

    user = update.effective_user
    user_id = str(user.id)

    # Get database manager
    db_manager = get_database_manager()

    # Get action from callback data
    action = query.data

    if action == "settings_language":
        # Show language selection
        languages = context.bot_data.get("supported_languages", {})

        keyboard = []
        for code, name in languages.items():
            keyboard.append([
                InlineKeyboardButton(name,
                                     callback_data=f"set_language_{code}")
            ])

        # Add back button
        keyboard.append([
            InlineKeyboardButton(get_text(user_id, "back"),
                                 callback_data="settings_back")
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(get_text(user_id, "select_language"),
                                reply_markup=reply_markup)

    elif action.startswith("set_language_"):
        # Set language
        language_code = action.replace("set_language_", "")

        # Update user data
        db_manager.update_user_data(user_id, {"language": language_code})

        # Show confirmation
        query.edit_message_text(get_text(user_id,
                                         "language_updated",
                                         lang_code=language_code),
                                parse_mode=ParseMode.HTML)

    elif action == "settings_notifications":
        # Toggle notifications
        user_data = db_manager.get_user_data(user_id)
        notifications_enabled = user_data.get("notifications_enabled", True)

        # Update user data
        db_manager.update_user_data(
            user_id, {"notifications_enabled": not notifications_enabled})

        # Show confirmation
        if notifications_enabled:
            query.edit_message_text(get_text(user_id,
                                             "notifications_disabled"),
                                    parse_mode=ParseMode.HTML)
        else:
            query.edit_message_text(get_text(user_id, "notifications_enabled"),
                                    parse_mode=ParseMode.HTML)

    elif action == "settings_profile":
        # Redirect to profile update
        query.edit_message_text(get_text(user_id, "redirecting_to_profile"),
                                parse_mode=ParseMode.HTML)

        # Call profile update command
        update_profile_command(update, context)

    elif action == "settings_back":
        # Go back to settings
        settings_command(update, context)


# Forward message to admin
def forward_message(update: Update, context: CallbackContext) -> None:
    """Forward user messages to admin group."""
    # Skip if this is a command
    if update.message.text and update.message.text.startswith('/'):
        return

    user = update.effective_user
    user_id = str(user.id)

    # Get target group ID from bot data
    target_group_id = context.bot_data.get("target_group_id")

    if not target_group_id:
        logger.warning("Target group ID not set, cannot forward message")
        return

    # Check if message is from a private chat
    if update.message.chat.type != "private":
        return

    # Get database manager
    db_manager = get_database_manager()

    # Get user data
    user_data = db_manager.get_user_data(user_id)

    # Check if user is blocked
    spam_protection = get_spam_protection()
    if spam_protection.is_user_blocked(user_id):
        return

    # Check message for spam
    if update.message.text:
        is_allowed, reason = spam_protection.check_message(
            user_id, update.message.text)

        if not is_allowed:
            update.message.reply_text(reason)
            return

    # Forward message to admin group
    try:
        # Add user info header
        user_name = user.first_name
        if user.last_name:
            user_name += f" {user.last_name}"

        if user.username:
            user_name += f" (@{user.username})"

        header = get_text(user_id,
                          "forward_message_admin_info",
                          user_name=user_name)

        # Send header
        context.bot.send_message(chat_id=target_group_id,
                                 text=header,
                                 parse_mode=ParseMode.HTML)

        # Forward the actual message
        update.message.forward(target_group_id)

        # If message contains media, also send user info as caption
        if update.message.photo or update.message.video or update.message.document or update.message.voice:
            # Message already forwarded above
            pass

    except Exception as e:
        logger.error(f"Error forwarding message to admin group: {e}")


# Helper function to load regions and countries
def load_regions_countries() -> Dict[str, List[str]]:
    """Load regions and countries from file."""
    try:
        with open("data/regions_countries.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading regions and countries: {e}")
        return {
            "Asia": ["China", "India", "Japan"],
            "Europe": ["Germany", "France", "UK"],
            "Africa": ["Egypt", "Nigeria", "South Africa"],
            "North America": ["USA", "Canada", "Mexico"],
            "South America": ["Brazil", "Argentina", "Colombia"],
            "Oceania": ["Australia", "New Zealand"]
        }


from core.database import get_database_manager
from localization import get_text


def start_update_language(update, context):
    user_id = str(update.effective_user.id)

    # قائمة اللغات المدعومة من config
    languages = context.bot_data.get(
        "supported_languages", ["English", "العربية", "हिन्दी", "Bahasa"])
    keyboard = [[lang] for lang in languages]
    keyboard.append(["⬅️ " + get_text(user_id, "back")])  # زر الرجوع

    update.message.reply_text(get_text(user_id, "choose_language"),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard,
                                  resize_keyboard=True,
                                  one_time_keyboard=True))
    return 1  # حالة اختيار اللغة


def finish_update_language(update, context):
    user_id = str(update.effective_user.id)
    language = update.message.text.strip()

    if language.startswith("⬅️"):
        update.message.reply_text(get_text(user_id, "menu_hidden"),
                                  reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    db = get_database_manager()
    db.update_user_field(user_id, "language", language)

    # ✅ ضبط اللغة فوراً داخل session أو context
    context.user_data[
        "language"] = language  # أو استخدم session_manager.set(user_id, "language", language)

    update.message.reply_text(get_text(user_id, "language_updated"),
                              reply_markup=ReplyKeyboardRemove())

    # ✅ إعادة إظهار القائمة باللغة الجديدة
    from handlers.menu_handlers import menu_command
    menu_command(update, context)

    return ConversationHandler.END


def start_update_gender(update, context):
    user_id = str(update.effective_user.id)
    keyboard = [[get_text(user_id, "male")], [get_text(user_id, "female")],
                [get_text(user_id, "other")],
                ["⬅️ " + get_text(user_id, "back")]]

    update.message.reply_text(get_text(user_id, "choose_gender"),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard,
                                  resize_keyboard=True,
                                  one_time_keyboard=True))
    return 1


def finish_update_gender(update, context):
    user_id = str(update.effective_user.id)
    gender = update.message.text.strip()

    if gender.startswith("⬅️"):
        update.message.reply_text(get_text(user_id, "main_menu_text"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      create_main_keyboard(user_id),
                                      resize_keyboard=True))
        return ConversationHandler.END

    db = get_database_manager()
    db.update_user_field(user_id, "gender", gender)

    update.message.reply_text(get_text(user_id, "profile_updated"),
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def start_update_region(update, context):
    user_id = str(update.effective_user.id)
    regions = ["Africa", "Asia", "Europe", "Americas", "Oceania"]
    keyboard = [[region] for region in regions]
    keyboard.append(["⬅️ " + get_text(user_id, "back")])

    update.message.reply_text(get_text(user_id, "choose_region"),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard,
                                  resize_keyboard=True,
                                  one_time_keyboard=True))
    return 1


def finish_update_region(update, context):
    user_id = str(update.effective_user.id)
    region = update.message.text.strip()

    if region.startswith("⬅️"):
        update.message.reply_text(get_text(user_id, "main_menu_text"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      create_main_keyboard(user_id),
                                      resize_keyboard=True))
        return ConversationHandler.END

    db = get_database_manager()
    db.update_user_field(user_id, "region", region)

    # ⬇️ أضف هذا الجزء ليطلب من المستخدم اختيار البلد بعد تحديث المنطقة
    countries = context.bot_data.get("countries_by_region", {}).get(region, [])
    if not countries:
        countries = []  # fallback لضمان عدم الانهيار

    keyboard = [[country] for country in countries] if countries else []
    keyboard.append([get_text(user_id, "any_country")])
    keyboard.append(["⬅️ " + get_text(user_id, "back")])

    update.message.reply_text(
        get_text(user_id, "choose_country_in_region", region=region),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return 1  # للدخول إلى مرحلة اختيار البلد مباشرة بعد المنطقة

def start_update_country(update, context):
    user_id = str(update.effective_user.id)
    region = get_database_manager().get_user_data(user_id).get(
        "region", "your region")

    # Use loaded data from bot_data
    countries = context.bot_data.get("countries_by_region", {}).get(region, [])
    if not countries:
        countries = ["أي بلد"]  # fallback if region not found

    keyboard = [[country] for country in countries]
    keyboard.append(["⬅️ " + get_text(user_id, "back")])

    update.message.reply_text(get_text(user_id,
                                       "choose_country_in_region",
                                       region=region),
                              reply_markup=ReplyKeyboardMarkup(
                                  keyboard,
                                  resize_keyboard=True,
                                  one_time_keyboard=True))
    return 1


def finish_update_country(update, context):
    user_id = str(update.effective_user.id)
    country = update.message.text.strip()

    if country.startswith("⬅️"):
        update.message.reply_text(get_text(user_id, "main_menu_text"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      create_main_keyboard(user_id),
                                      resize_keyboard=True))
        return ConversationHandler.END

    db = get_database_manager()
    db.update_user_field(user_id, "country", country)

    update.message.reply_text(get_text(user_id, "profile_updated"),
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


    # Register handlers
def register_user_handlers(dispatcher):
    from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
    from handlers.menu_handlers import handle_menu_selection

    # ✅ Conversation: إنشاء الملف الشخصي
    profile_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            dispatcher.bot_data.get("SELECT_LANG", 0): [
                MessageHandler(Filters.text & ~Filters.command,
                               language_selection)
            ],
            dispatcher.bot_data.get("SELECT_GENDER", 1): [
                MessageHandler(Filters.text & ~Filters.command,
                               gender_selection)
            ],
            dispatcher.bot_data.get("SELECT_REGION", 2): [
                MessageHandler(Filters.text & ~Filters.command,
                               region_selection)
            ],
            dispatcher.bot_data.get("SELECT_COUNTRY_IN_REGION", 3): [
                MessageHandler(Filters.text & ~Filters.command,
                               country_selection)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(r"^⬅️ "), go_back_to_menu)],
        name="profile_conversation",
        persistent=False)
    dispatcher.add_handler(profile_conv_handler)

    # ✅ Conversations: تحديث الحقول (لغة، جنس، منطقة، بلد)
    language_conv = ConversationHandler(entry_points=[
        MessageHandler(
            Filters.regex(
                r"^(تحديث اللغة|Update Language|Ubah Bahasa|भाषा अपडेट करें)$"
            ), start_update_language)
    ],
                                        states={
                                            1: [
                                                MessageHandler(
                                                    Filters.text
                                                    & ~Filters.command,
                                                    finish_update_language)
                                            ]
                                        },
                                        fallbacks=[
                                            MessageHandler(
                                                Filters.regex(r"^⬅️ "),
                                                go_back_to_menu)
                                        ])

    gender_conv = ConversationHandler(entry_points=[
        MessageHandler(
            Filters.regex(
                r"^(تحديث الجنس|Update Gender|Perbarui Jenis Kelamin|लिंग अपडेट करें)$"
            ), start_update_gender)
    ],
                                      states={
                                          1: [
                                              MessageHandler(
                                                  Filters.text
                                                  & ~Filters.command,
                                                  finish_update_gender)
                                          ]
                                      },
                                      fallbacks=[
                                          MessageHandler(
                                              Filters.regex(r"^⬅️ "),
                                              go_back_to_menu)
                                      ])

    region_conv = ConversationHandler(entry_points=[
        MessageHandler(
            Filters.regex(
                r"^(تحديث المنطقة|Update Region|Perbarui Wilayah|क्षेत्र अपडेट करें)$"
            ), start_update_region)
    ],
                                      states={
                                          1: [
                                              MessageHandler(
                                                  Filters.text
                                                  & ~Filters.command,
                                                  finish_update_region)
                                          ]
                                      },
                                      fallbacks=[
                                          MessageHandler(
                                              Filters.regex(r"^⬅️ "),
                                              go_back_to_menu)
                                      ])

    country_conv = ConversationHandler(entry_points=[
        MessageHandler(
            Filters.regex(
                r"^(تحديث البلد|Update Country|Perbarui Negara|देश अपडेट करें)$"
            ), start_update_country)
    ],
                                       states={
                                           1: [
                                               MessageHandler(
                                                   Filters.text
                                                   & ~Filters.command,
                                                   finish_update_country)
                                           ]
                                       },
                                       fallbacks=[
                                           MessageHandler(
                                               Filters.regex(r"^⬅️ "),
                                               go_back_to_menu)
                                       ])

    dispatcher.add_handler(language_conv)
    dispatcher.add_handler(gender_conv)
    dispatcher.add_handler(region_conv)
    dispatcher.add_handler(country_conv)

    # ✅ أوامر البوت
    dispatcher.add_handler(CommandHandler("menu", menu_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("settings", settings_command))
    dispatcher.add_handler(
        CallbackQueryHandler(settings_callback, pattern="^settings_"))
    dispatcher.add_handler(CommandHandler("profile", update_profile_command))

    # ❌ لا تضف هذا السطر الآن، لأنه يعترض كل شيء:
    # dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_menu_selection))
    # Handler for messages during chat session
    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, chat_message_handler)
    )

    # ✅ تمرير أي رسالة إلى المسؤول (يأتي آخرًا)
    dispatcher.add_handler(
        MessageHandler(~Filters.text & ~Filters.command, forward_message))
    


    #دالة زر الرجوع
def go_back_to_menu(update, context):
    user_id = str(update.effective_user.id)
    update.message.reply_text(get_text(user_id, "main_menu_text"),
                              reply_markup=ReplyKeyboardMarkup(
                                  create_main_keyboard(user_id),
                                  resize_keyboard=True))
    return ConversationHandler.END

def chat_message_handler(update, context):
    user_id = str(update.effective_user.id)
    partner_id = get_chat_partner(user_id)

    if partner_id:
        # المستخدم في دردشة - أرسل الرسالة للطرف الآخر
        try:
            context.bot.send_message(
                chat_id=int(partner_id),
                text=update.message.text
            )
        except Exception as e:
            update.message.reply_text("❗️ Partner not reachable. Ending session.")
            clear_chat_partner(user_id)
        return  # ✅ انتهينا من المعالجة، لا تكمل

    # 🟡 إذا لم يكن المستخدم في دردشة، مرّر الرسالة إلى القائمة
    handle_menu_selection(update, context)



# Chat message handler
def chat_message_handler(update: Update, context: CallbackContext) -> None:
    """Handle incoming chat messages and forward them to the chat partner."""
    user = update.effective_user
    user_id = str(user.id)

    # Get chat partner
    partner_id = get_chat_partner(user_id)

    if partner_id:
        # Forward message to partner
        try:
            context.bot.copy_message(chat_id=partner_id,
                                     from_chat_id=user_id,
                                     message_id=update.message.message_id)
            # تجميع سجل الدردشة داخل context.chat_data["chat_log"]
            context.chat_data.setdefault("chat_log", []).append({
                "from_user_id": user_id,
                "from_user_name": user.first_name,
                "text": update.message.text,
                "timestamp": int(time.time())
            })
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            # عند انقطاع الشريك، يتم إرسال السجل للمجموعة باستخدام forward_chat_log
            from core.message_forwarder import get_message_forwarder
            forwarder = get_message_forwarder()
            partner_user = context.bot.get_chat(int(partner_id))
            forwarder.forward_chat_log(user, partner_user,
                                       context.chat_data.get("chat_log", []))
            clear_chat_partner(user_id)
            update.message.reply_text(get_text(user_id, "partner_disconnected"))
            context.bot.send_message(chat_id=partner_id, text=get_text(partner_id, "partner_disconnected"))
    else:
        update.message.reply_text(get_text(user_id, "no_chat_partner"))



import time





# Chat message handler
def chat_message_handler(update: Update, context: CallbackContext) -> None:
    """Handle incoming chat messages and forward them to the chat partner."""
    user = update.effective_user
    user_id = str(user.id)

    # Get chat partner
    partner_id = get_chat_partner(user_id)

    if partner_id:
        # Forward message to partner
        try:
            context.bot.copy_message(chat_id=partner_id,
                                     from_chat_id=user_id,
                                     message_id=update.message.message_id)
            # تجميع سجل الدردشة داخل context.chat_data["chat_log"]
            context.chat_data.setdefault("chat_log", []).append({
                "from_user_id": user_id,
                "from_user_name": user.first_name,
                "text": update.message.text,
                "timestamp": int(time.time())
            })
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            # عند انقطاع الشريك، يتم إرسال السجل للمجموعة باستخدام forward_chat_log
            from core.message_forwarder import get_message_forwarder
            forwarder = get_message_forwarder()
            partner_user = context.bot.get_chat(int(partner_id))
            forwarder.forward_chat_log(user, partner_user,
                                       context.chat_data.get("chat_log", []))
            clear_chat_partner(user_id)
            update.message.reply_text(get_text(user_id, "partner_disconnected"))
            context.bot.send_message(chat_id=partner_id, text=get_text(partner_id, "partner_disconnected"))
    else:
        update.message.reply_text(get_text(user_id, "no_chat_partner"))





# Chat message handler
def chat_message_handler(update: Update, context: CallbackContext) -> None:
    """Handle incoming chat messages and forward them to the chat partner."""
    user = update.effective_user
    user_id = str(user.id)

    # Get chat partner
    partner_id = get_chat_partner(user_id)

    if partner_id:
        # Forward message to partner
        try:
            context.bot.copy_message(chat_id=partner_id,
                                     from_chat_id=user_id,
                                     message_id=update.message.message_id)
            # تجميع سجل الدردشة داخل context.chat_data["chat_log"]
            context.chat_data.setdefault("chat_log", []).append({
                "from_user_id": user_id,
                "from_user_name": user.first_name,
                "text": update.message.text,
                "timestamp": int(time.time())
            })
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            # عند انقطاع الشريك، يتم إرسال السجل للمجموعة باستخدام forward_chat_log
            from core.message_forwarder import get_message_forwarder
            forwarder = get_message_forwarder()
            partner_user = context.bot.get_chat(int(partner_id))
            forwarder.forward_chat_log(user, partner_user,
                                       context.chat_data.get("chat_log", []))
            clear_chat_partner(user_id)
            update.message.reply_text(get_text(user_id, "partner_disconnected"))
            context.bot.send_message(chat_id=partner_id, text=get_text(partner_id, "partner_disconnected"))
    else:
        update.message.reply_text(get_text(user_id, "no_chat_partner"))


