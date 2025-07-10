"""
Search handlers module for MultiLangTranslator Bot

This module provides search functionality including:
- Partner search by language, gender, region, and country
- Advanced search options for premium users
- Search results display and management
"""

import logging
import random
from typing import Dict, List, Any, Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, ConversationHandler
from telegram.ext import MessageHandler, Filters
import config
from handlers.menu_handlers import handle_menu_selection
from core.session import set_chat_partner, get_chat_partner
from telegram import ReplyKeyboardRemove
from telegram.ext import MessageHandler, CommandHandler, ConversationHandler, Filters
from handlers.menu_handlers import handle_menu_selection
from telegram.ext import (CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler)

# Import core modules
from core.session import require_profile, require_premium
from core.database import get_database_manager
from core.notifications import get_notification_manager
from localization import get_text
from data_handler import get_all_users
from random import choice

# Initialize logger
logger = logging.getLogger(__name__)


# Start partner search
@require_profile
def start_partner_search(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_id = str(user.id)

    # احصل على حالة المستخدم من قاعدة البيانات
    db = get_database_manager()
    user_data = db.get_user_data(user_id)
    is_premium = user_data.get("premium", False)

    if not is_premium:
        # المستخدم المجاني → بحث عشوائي
        return perform_random_search(update, context)

    else:
        # المستخدم المدفوع → بحث متقدم
        languages = context.bot_data.get("supported_languages", {})
        keyboard = [[KeyboardButton(name)] for code, name in languages.items()]
        keyboard.append([KeyboardButton(get_text(user_id, "any_language"))])
        keyboard.append([KeyboardButton(get_text(user_id, "cancel"))])

        update.message.reply_text(
            get_text(user_id, "search_partner_prompt_language"),
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

        return context.bot_data.get("SEARCH_PARTNER_LANG", 4)


def perform_random_search(update: Update, context: CallbackContext) -> int:
    user_id = str(update.effective_user.id)

    # استخرج كل المستخدمين المتصلين (profile_complete و not blocked و ليس نفس الشخص)
    from data_handler import load_user_data
    all_users = load_user_data()
    candidates = []

    for uid, data in all_users.items():
        if uid == user_id:
            continue
        if not data.get("profile_complete", False):
            continue
        if data.get("blocked", False):
            continue

        candidates.append({
            "user_id": uid,
            "name": data.get("name", "Unknown"),
            "language": data.get("language", "Unknown"),
            "gender": data.get("gender", "Unknown"),
            "country": data.get("country", "Unknown"),
            "username": data.get("username", None)
        })

    if not candidates:
        update.message.reply_text(get_text(user_id, "search_results_none"),
                                  reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    import random
    match = random.choice(candidates)

    # ربط المستخدمين للدردشة
    partner_id = str(match["user_id"])
    set_chat_partner(user_id, partner_id)
    set_chat_partner(partner_id, user_id)

    # إرسال رسالة بدء الدردشة للطرفين
    context.bot.send_message(chat_id=partner_id, text=get_text(partner_id, "chat_started"))
    context.bot.send_message(chat_id=user_id, text=get_text(user_id, "chat_started"))

    result_message = get_text(user_id, "search_results_found",
                              count=1) + "\n\n"
    result_message += (
        f"{match['name']}\n"
        f"{get_text(user_id, 'language')}: {match['language']}\n"
        f"{get_text(user_id, 'gender')}: {get_text(user_id, match['gender'])}\n"
        f"{get_text(user_id, 'country')}: {match['country']}\n")
    if match.get("username"):
        result_message += f"@{match['username']}"

    update.message.reply_text(result_message,
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Language selection for partner search
def search_partner_language(update: Update, context: CallbackContext) -> int:
    """Handle language selection for partner search."""
    user = update.effective_user
    user_id = str(user.id)
    selected_language = update.message.text

    # Get database manager
    db_manager = get_database_manager()

    # Check if "Any Language" was selected
    if selected_language == get_text(user_id, "any_language"):
        # Store "any" as the selected language
        context.user_data["search_language"] = "any"
    else:
        # Map selected language name to language code
        languages = context.bot_data.get("supported_languages", {})
        language_code = None

        for code, name in languages.items():
            if name == selected_language:
                language_code = code
                break

        if not language_code:
            # Invalid selection, ask again
            keyboard = [[KeyboardButton(name)]
                        for code, name in languages.items()]
            keyboard.append(
                [KeyboardButton(get_text(user_id, "any_language"))])
            keyboard.append([KeyboardButton(get_text(user_id, "cancel"))])

            update.message.reply_text(get_text(user_id, "invalid_language"),
                                      reply_markup=ReplyKeyboardMarkup(
                                          keyboard, one_time_keyboard=True))

            return context.bot_data.get("SEARCH_PARTNER_LANG", 4)

        # Store the selected language code
        context.user_data["search_language"] = language_code

    # Show gender selection
    keyboard = [[KeyboardButton(get_text(user_id, "male"))],
                [KeyboardButton(get_text(user_id, "female"))],
                [KeyboardButton(get_text(user_id, "other"))],
                [KeyboardButton(get_text(user_id, "any_gender"))],
                [KeyboardButton(get_text(user_id, "cancel"))]]

    update.message.reply_text(
        get_text(user_id, "search_partner_prompt_gender"),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

    return context.bot_data.get("SEARCH_PARTNER_GENDER", 5)


# Gender selection for partner search
def search_partner_gender(update: Update, context: CallbackContext) -> int:
    """Handle gender selection for partner search."""
    user = update.effective_user
    user_id = str(user.id)
    selected_gender = update.message.text

    # Check if "Any Gender" was selected
    if selected_gender == get_text(user_id, "any_gender"):
        # Store "any" as the selected gender
        context.user_data["search_gender"] = "any"
    else:
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
                        [KeyboardButton(get_text(user_id, "other"))],
                        [KeyboardButton(get_text(user_id, "any_gender"))],
                        [KeyboardButton(get_text(user_id, "cancel"))]]

            update.message.reply_text(get_text(user_id, "invalid_gender"),
                                      reply_markup=ReplyKeyboardMarkup(
                                          keyboard, one_time_keyboard=True))

            return context.bot_data.get("SEARCH_PARTNER_GENDER", 5)

        # Map localized gender to English
        gender_map = {
            get_text(user_id, "male"): "male",
            get_text(user_id, "female"): "female",
            get_text(user_id, "other"): "other"
        }

        # Store the selected gender
        context.user_data["search_gender"] = gender_map[selected_gender]

    # Show region selection
    # Get database manager
    db_manager = get_database_manager()

    # Get user data
    user_data = db_manager.get_user_data(user_id)

    # Check if user has premium
    is_premium = user_data.get("premium", False)

    if not is_premium:
        # Non-premium users can only search by language and gender
        # Perform search with current criteria
        search_results = perform_search(context, user_id)

        # Show results
        show_search_results(update, context, search_results)

        return ConversationHandler.END

    # Premium users can search by region and country
    # Load regions
    import json
    try:
        with open("data/regions_countries.json", "r", encoding="utf-8") as f:
            regions_countries = json.load(f)
            regions = list(regions_countries.keys())
    except Exception as e:
        logger.error(f"Error loading regions: {e}")
        regions = [
            "Asia", "Europe", "Africa", "North America", "South America",
            "Oceania"
        ]

    keyboard = [[KeyboardButton(region)] for region in regions]

    # Add "Any Region" option
    keyboard.append([KeyboardButton(get_text(user_id, "any_region"))])

    # Add cancel button
    keyboard.append([KeyboardButton(get_text(user_id, "cancel"))])

    update.message.reply_text(
        get_text(user_id, "search_partner_prompt_region_for_country"),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

    return context.bot_data.get("SEARCH_PARTNER_REGION", 6)


# Region selection for partner search
def search_partner_region(update: Update, context: CallbackContext) -> int:
    """Handle region selection for partner search."""
    user = update.effective_user
    user_id = str(user.id)
    selected_region = update.message.text

    # Check if "Any Region" was selected
    if selected_region == get_text(user_id, "any_region"):
        # Store "any" as the selected region
        context.user_data["search_region"] = "any"

        # Skip country selection
        search_results = perform_search(context, user_id)

        # Show results
        show_search_results(update, context, search_results)

        return ConversationHandler.END

    # Load regions and countries
    import json
    try:
        with open("data/regions_countries.json", "r", encoding="utf-8") as f:
            regions_countries = json.load(f)
    except Exception as e:
        logger.error(f"Error loading regions and countries: {e}")
        regions_countries = {
            "Asia": ["China", "India", "Japan"],
            "Europe": ["Germany", "France", "UK"],
            "Africa": ["Egypt", "Nigeria", "South Africa"],
            "North America": ["USA", "Canada", "Mexico"],
            "South America": ["Brazil", "Argentina", "Colombia"],
            "Oceania": ["Australia", "New Zealand"]
        }

    if selected_region not in regions_countries:
        # Invalid selection, ask again
        regions = list(regions_countries.keys())
        keyboard = [[KeyboardButton(region)] for region in regions]
        keyboard.append([KeyboardButton(get_text(user_id, "any_region"))])
        keyboard.append([KeyboardButton(get_text(user_id, "cancel"))])

        update.message.reply_text(get_text(user_id, "invalid_region"),
                                  reply_markup=ReplyKeyboardMarkup(
                                      keyboard, one_time_keyboard=True))

        return context.bot_data.get("SEARCH_PARTNER_REGION", 6)

    # Store the selected region
    context.user_data["search_region"] = selected_region

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

    # Add "Any Country" option
    keyboard.append([KeyboardButton(get_text(user_id, "any_country"))])

    # Add cancel button
    keyboard.append([KeyboardButton(get_text(user_id, "cancel"))])

    update.message.reply_text(
        get_text(user_id,
                 "search_partner_select_country_from_region",
                 region=selected_region),
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))

    return context.bot_data.get("SEARCH_PARTNER_COUNTRY", 7)


# Country selection for partner search
def search_partner_country(update: Update, context: CallbackContext) -> int:
    """Handle country selection for partner search."""
    user = update.effective_user
    user_id = str(user.id)
    selected_country = update.message.text

    # Check if "Any Country" was selected
    if selected_country == get_text(user_id, "any_country"):
        # Store "any" as the selected country
        context.user_data["search_country"] = "any"
    else:
        # Get selected region from context
        selected_region = context.user_data.get("search_region")

        if not selected_region or selected_region == "any":
            # Something went wrong, restart from region selection
            return search_partner_region(update, context)

        # Load regions and countries
        import json
        try:
            with open("data/regions_countries.json", "r",
                      encoding="utf-8") as f:
                regions_countries = json.load(f)
        except Exception as e:
            logger.error(f"Error loading regions and countries: {e}")
            regions_countries = {
                "Asia": ["China", "India", "Japan"],
                "Europe": ["Germany", "France", "UK"],
                "Africa": ["Egypt", "Nigeria", "South Africa"],
                "North America": ["USA", "Canada", "Mexico"],
                "South America": ["Brazil", "Argentina", "Colombia"],
                "Oceania": ["Australia", "New Zealand"]
            }

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

            # Add "Any Country" option
            keyboard.append([KeyboardButton(get_text(user_id, "any_country"))])

            # Add cancel button
            keyboard.append([KeyboardButton(get_text(user_id, "cancel"))])

            update.message.reply_text(
                get_text(user_id, "country_not_found_in_region"),
                reply_markup=ReplyKeyboardMarkup(keyboard,
                                                 one_time_keyboard=True))

            return context.bot_data.get("SEARCH_PARTNER_COUNTRY", 7)

        # Store the selected country
        context.user_data["search_country"] = selected_country

    # Perform search with all criteria
    search_results = perform_search(context, user_id)

    # Show results
    show_search_results(update, context, search_results)

    return ConversationHandler.END


# Perform search based on criteria
def perform_search(context: CallbackContext,
                   user_id: str) -> List[Dict[str, Any]]:
    """
    Perform search based on criteria in context.user_data.
    
    Args:
        context: CallbackContext
        user_id: User ID
        
    Returns:
        List of matching user data dictionaries
    """
    # Get database manager
    db_manager = get_database_manager()

    # Get all users
    all_users = db_manager.get_all_users()

    # Get search criteria
    search_language = context.user_data.get("search_language", "any")
    search_gender = context.user_data.get("search_gender", "any")
    search_region = context.user_data.get("search_region", "any")
    search_country = context.user_data.get("search_country", "any")

    # Filter users based on criteria
    matching_users = []

    for other_id in all_users:
        # Skip self
        if other_id == user_id:
            continue

        # Get user data
        other_data = db_manager.get_user_data(other_id)

        # Check language
        if search_language != "any" and other_data.get(
                "language") != search_language:
            continue

        # Check gender
        if search_gender != "any" and other_data.get(
                "gender") != search_gender:
            continue

        # Check region
        if search_region != "any" and other_data.get(
                "region") != search_region:
            continue

        # Check country
        if search_country != "any" and other_data.get(
                "country") != search_country:
            continue

        # Add to matching users
        matching_users.append({
            "user_id": other_id,
            "name": other_data.get("name", "Unknown"),
            "language": other_data.get("language", "Unknown"),
            "gender": other_data.get("gender", "Unknown"),
            "region": other_data.get("region", "Unknown"),
            "country": other_data.get("country", "Unknown")
        })

    return matching_users


def perform_random_search(update: Update, context: CallbackContext) -> int:
    """Search randomly for online users."""
    user = update.effective_user
    user_id = str(user.id)

    db = get_database_manager()
    all_users = db.get_all_users()
    matching_users = []

    for other_id in all_users:
        if other_id == user_id:
            continue
        other_data = db.get_user_data(other_id)
        if other_data.get("looking_for_partner"):
            matching_users.append({
                "user_id":
                other_id,
                "name":
                other_data.get("name", "Unknown"),
                "language":
                other_data.get("language", "Unknown"),
                "gender":
                other_data.get("gender", "Unknown"),
                "region":
                other_data.get("region", "Unknown"),
                "country":
                other_data.get("country", "Unknown")
            })

    if not matching_users:
        update.message.reply_text(get_text(user_id, "search_results_none"),
                                  reply_markup=ReplyKeyboardRemove())
    else:
        show_search_results(update, context, matching_users)

    return ConversationHandler.END


# Show search results
def show_search_results(update: Update, context: CallbackContext,
                        results: List[Dict[str, Any]]) -> None:
    """
    Show search results to the user.
    
    Args:
        update: Update
        context: CallbackContext
        results: List of matching user data dictionaries
    """
    user = update.effective_user
    user_id = str(user.id)

    if not results:
        # No results
        update.message.reply_text(get_text(user_id, "search_results_none"),
                                  reply_markup=ReplyKeyboardRemove())
        return

    # Show results
    message = get_text(user_id, "search_results_found",
                       count=len(results)) + "\n\n"

    for i, result in enumerate(results[:10]):  # Limit to 10 results
        message += f"{i+1}. <b>{result['name']}</b>\n"
        message += f"   🗣️ {get_text(user_id, 'language')}: {context.bot_data.get('supported_languages', {}).get(result['language'], result['language'])}\n"
        message += f"   👤 {get_text(user_id, 'gender')}: {get_text(user_id, result['gender'])}\n"
        message += f"   🌍 {get_text(user_id, 'region')}: {result['region']}\n"
        message += f"   🏙️ {get_text(user_id, 'country')}: {result['country']}\n\n"

    if len(results) > 10:
        message += get_text(user_id, "more_results", count=len(results) - 10)

    # Create inline keyboard for contacting users
    keyboard = []

    for i, result in enumerate(results[:5]):  # Limit to 5 contact buttons
        keyboard.append([
            InlineKeyboardButton(
                f"{get_text(user_id, 'contact')} {result['name']}",
                callback_data=f"contact_{result['user_id']}")
        ])

    # Add button to search again
    keyboard.append([
        InlineKeyboardButton(get_text(user_id, "search_again"),
                             callback_data="search_again")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send results
    update.message.reply_text(message,
                              reply_markup=reply_markup,
                              parse_mode=ParseMode.HTML)


# Contact user callback
def contact_user_callback(update: Update, context: CallbackContext) -> None:
    """Handle contact user callback."""
    query = update.callback_query
    query.answer()

    user = update.effective_user
    user_id = str(user.id)

    # Extract target user ID from callback data
    target_id = query.data.replace("contact_", "")

    # Get database manager
    db_manager = get_database_manager()

    # Get target user data
    target_data = db_manager.get_user_data(target_id)

    if not target_data:
        # User not found
        query.edit_message_text(get_text(user_id, "user_not_found"),
                                parse_mode=ParseMode.HTML)
        return

    # Get notification manager
    notification_manager = get_notification_manager()

    # Notify target user
    notification_manager.notify_user(
        target_id,
        get_text(target_id,
                 "contact_request",
                 name=user.first_name,
                 language=context.bot_data.get("supported_languages", {}).get(
                     db_manager.get_user_data(user_id).get("language", "en"),
                     "Unknown")),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(get_text(target_id, "accept_contact"),
                                 callback_data=f"accept_contact_{user_id}"),
            InlineKeyboardButton(get_text(target_id, "decline_contact"),
                                 callback_data=f"decline_contact_{user_id}")
        ]]))

    # Notify requesting user
    query.edit_message_text(get_text(user_id,
                                     "contact_request_sent",
                                     name=target_data.get("name", "Unknown")),
                            parse_mode=ParseMode.HTML)


# Search again callback
def search_again_callback(update: Update, context: CallbackContext) -> None:
    """Handle search again callback."""
    query = update.callback_query
    query.answer()

    # Clear previous search criteria
    context.user_data.pop("search_language", None)
    context.user_data.pop("search_gender", None)
    context.user_data.pop("search_region", None)
    context.user_data.pop("search_country", None)

    # Start new search
    query.edit_message_text(get_text(query.from_user.id,
                                     "starting_new_search"),
                            parse_mode=ParseMode.HTML)

    # Call start_partner_search
    start_partner_search(update, context)


# Accept contact callback
def accept_contact_callback(update: Update, context: CallbackContext) -> None:
    """Handle accept contact callback."""
    query = update.callback_query
    query.answer()

    user = update.effective_user
    user_id = str(user.id)

    # Extract requester user ID from callback data
    requester_id = query.data.replace("accept_contact_", "")

    # Get database manager
    db_manager = get_database_manager()

    # Get requester user data
    requester_data = db_manager.get_user_data(requester_id)

    if not requester_data:
        # User not found
        query.edit_message_text(get_text(user_id, "user_not_found"),
                                parse_mode=ParseMode.HTML)
        return

    # Get notification manager
    notification_manager = get_notification_manager()

    # Notify requester
    notification_manager.notify_user(
        requester_id,
        get_text(requester_id,
                 "contact_accepted",
                 name=user.first_name,
                 username=user.username
                 or get_text(requester_id, "no_username")),
        parse_mode=ParseMode.HTML)

    # Notify accepting user
    query.edit_message_text(
        get_text(user_id,
                 "contact_accepted_confirmation",
                 name=requester_data.get("name", "Unknown"),
                 username=requester_data.get("username",
                                             get_text(user_id,
                                                      "no_username"))),
        parse_mode=ParseMode.HTML)


# Decline contact callback
def decline_contact_callback(update: Update, context: CallbackContext) -> None:
    """Handle decline contact callback."""
    query = update.callback_query
    query.answer()

    user = update.effective_user
    user_id = str(user.id)

    # Extract requester user ID from callback data
    requester_id = query.data.replace("decline_contact_", "")

    # Get database manager
    db_manager = get_database_manager()

    # Get requester user data
    requester_data = db_manager.get_user_data(requester_id)

    if not requester_data:
        # User not found
        query.edit_message_text(get_text(user_id, "user_not_found"),
                                parse_mode=ParseMode.HTML)
        return

    # Get notification manager
    notification_manager = get_notification_manager()

    # Notify requester
    notification_manager.notify_user(requester_id,
                                     get_text(requester_id,
                                              "contact_declined",
                                              name=user.first_name),
                                     parse_mode=ParseMode.HTML)

    # Notify declining user
    query.edit_message_text(get_text(user_id,
                                     "contact_declined_confirmation",
                                     name=requester_data.get(
                                         "name", "Unknown")),
                            parse_mode=ParseMode.HTML)



from random import choice
from data_handler import get_user_data, get_all_users, has_complete_profile


def find_random_partner(current_user_id: str) -> Dict[str, Any]:
    """
    Find a random online user (excluding self) with a complete profile.
    """
    all_users = get_all_users()
    candidates = [
        uid for uid in all_users
        if uid != current_user_id and has_complete_profile(uid)
    ]

    if not candidates:
        return None

    chosen_id = choice(candidates)
    return get_user_data(chosen_id)


def perform_random_search(update: Update, context: CallbackContext) -> int:
    """Search for a random available user (free users only)."""
    user = update.effective_user
    user_id = str(user.id)

    all_users = get_all_users()

    # استثناء المستخدم الحالي من النتائج
    available_users = [u for u in all_users if u["user_id"] != user_id]

    if not available_users:
        update.message.reply_text(get_text(user_id, "search_results_none"),
                                  reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # اختيار شريك عشوائي
    match = random.choice(available_users)

    message = (
        f"{get_text(user_id, 'language')}: {match['language']}\n"
        f"{get_text(user_id, 'gender')}: {get_text(user_id, match['gender'])}\n"
        f"{get_text(user_id, 'country')}: {match['country']}\n")
    if match.get("username"):
        message += f"@{match['username']}\n"

    update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def register_search_handlers(dispatcher):
    # ⬅️ زر القائمة: بحث عن شريك
    search_menu_handler = MessageHandler(
        Filters.regex(r"^(بحث عن شريك|Search Partner 🔍|Cari Pasangan|साथी खोजें)$"),
        start_partner_search
    )

    # 🧭 أمر /search
    search_command_handler = CommandHandler("search", start_partner_search)

    # 🔁 محادثة البحث التفاعلي
    search_conv_handler = ConversationHandler(
        entry_points=[
            search_command_handler,
            search_menu_handler
        ],
        states={
            dispatcher.bot_data.get("SEARCH_PARTNER_LANG", 4): [
                MessageHandler(Filters.text & ~Filters.command, search_partner_language)
            ],
            dispatcher.bot_data.get("SEARCH_PARTNER_GENDER", 5): [
                MessageHandler(Filters.text & ~Filters.command, search_partner_gender)
            ],
            dispatcher.bot_data.get("SEARCH_PARTNER_REGION", 6): [
                MessageHandler(Filters.text & ~Filters.command, search_partner_region)
            ],
            dispatcher.bot_data.get("SEARCH_PARTNER_COUNTRY", 7): [
                MessageHandler(Filters.text & ~Filters.command, search_partner_country)
            ],
        },
        fallbacks=[
            MessageHandler(Filters.regex(r"^⬅️ "), handle_menu_selection),
            CommandHandler("cancel", lambda u, c: ConversationHandler.END)
        ],
        name="partner_search_conversation",
        persistent=False
    )

    # تسجيل المحادثة التفاعلية
    dispatcher.add_handler(search_conv_handler)

    # 🔘 ردود الأزرار التفاعلية للنتائج
    dispatcher.add_handler(CallbackQueryHandler(contact_user_callback, pattern="^contact_"))
    dispatcher.add_handler(CallbackQueryHandler(search_again_callback, pattern="^search_again$"))
    dispatcher.add_handler(CallbackQueryHandler(accept_contact_callback, pattern="^accept_contact_"))
    dispatcher.add_handler(CallbackQueryHandler(decline_contact_callback, pattern="^decline_contact_"))


def perform_random_search(update, context):
    """ابحث عن مستخدم متاح وابدأ جلسة دردشة."""
    from core.session import get_session_manager
    from data_handler import load_user_data, get_user_data
    import random

    user = update.effective_user
    user_id = str(user.id)

    # تحميل كل المستخدمين
    users = load_user_data()
    online_users = get_session_manager().get_active_users()

    # المرشحون للدردشة (مستخدمون متصلون ومكتملو الملف الشخصي وليسوا المستخدم الحالي)
    candidates = [
        uid for uid in online_users
        if uid != user_id and users.get(uid, {}).get("profile_complete", False)
        and not get_chat_partner(uid)
    ]

    if not candidates:
        update.message.reply_text(get_text(user_id, "search_results_none"))
        return ConversationHandler.END

    # اختر شريك عشوائي
    partner_id = random.choice(candidates)

    # احفظ الجلسة
    set_chat_partner(user_id, partner_id)

    # أرسل رسالة للطرفين
    update.message.reply_text(
        get_text(user_id, "chat_started"),
        reply_markup=ReplyKeyboardRemove()
    )
    context.bot.send_message(
        chat_id=int(partner_id),
        text=get_text(partner_id, "chat_started"),
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
