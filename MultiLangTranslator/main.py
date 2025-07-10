"""
Modified main.py with improved error handling and data validation
for MultiLangTranslator Bot
"""

import os
import json
import logging

from telegram import Update, Bot
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler,
                          CallbackContext)

# Import configuration
import config

# Import core modules
from core.session import init_session_manager
from core.database import init_database_manager
from core.security import init_spam_protection
from core.notifications import init_notification_manager
from core.data_validation import initialize_data_directories, validate_and_repair_data_files

# Import handlers
from handlers.user_handlers import register_user_handlers
from handlers.admin_handlers import register_admin_handlers
from handlers.search_handlers import register_search_handlers
from handlers.payment_handlers import register_payment_handlers
from handlers.menu_handlers import register_menu_handlers, menu_command, handle_menu_selection
from handlers.admin_handlers import toggle_premium_callback

# Import web server for keep-alive


# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_data_directories():
    """Setup necessary directories and files."""
    # Use the new data validation module to initialize all directories and files
    success = initialize_data_directories(config)

    if not success:
        logger.warning(
            "Some data directories or files could not be initialized properly."
        )

    # Validate and repair data files if needed
    validation_results = validate_and_repair_data_files(config)

    # Log validation results
    for file_name, is_valid in validation_results.items():
        if not is_valid:
            logger.warning(f"File validation failed for {file_name}")


def main() -> None:
    """Start the bot."""
    logger.info("Starting bot...")

    try:
        # Setup data directories and initialize files
        setup_data_directories()

        # Create the Updater and pass it your bot's token
        updater = Updater(token=os.environ.get("BOT_TOKEN"))
        # Get the dispatcher to register handlers
        dispatcher = updater.dispatcher

        # Initialize bot data
        dispatcher.bot_data.update({
            "supported_languages": config.SUPPORTED_LANGUAGES,
            "admin_ids": [str(config.ADMIN_ID)],
            "target_group_id": config.TARGET_GROUP_ID,
            "payeer_account": config.PAYEER_ACCOUNT,
            "bitcoin_address": config.BITCOIN_ADDRESS,

            # Conversation states
            "SELECT_LANG": config.SELECT_LANG,
            "SELECT_GENDER": config.SELECT_GENDER,
            "SELECT_REGION": config.SELECT_REGION,
            "SELECT_COUNTRY_IN_REGION": config.SELECT_COUNTRY_IN_REGION,
            "SEARCH_PARTNER_LANG": config.SEARCH_PARTNER_LANG,
            "SEARCH_PARTNER_GENDER": config.SEARCH_PARTNER_GENDER,
            "SEARCH_PARTNER_REGION": config.SEARCH_PARTNER_REGION,
            "SEARCH_PARTNER_COUNTRY": config.SEARCH_PARTNER_COUNTRY,
            "PAYMENT_PROOF": config.PAYMENT_PROOF
        })

        with open("data/regions_countries.json", "r", encoding="utf-8") as f:
            dispatcher.bot_data["countries_by_region"] = json.load(f)
        # Load countries by region from file
        try:
            with open("data/regions_countries.json", "r",
                      encoding="utf-8") as f:
                dispatcher.bot_data["countries_by_region"] = json.load(f)
        except Exception as e:
            logger.warning(f"Couldn't load regions_countries.json: {e}")
            dispatcher.bot_data["countries_by_region"] = {}

        # Initialize core modules
        session_manager = init_session_manager("data/sessions.json")
        db_manager = init_database_manager(config.USER_DATA_FILE,
                                           config.PENDING_PAYMENTS_FILE)
        spam_protection = init_spam_protection()
        notification_manager = init_notification_manager(
            updater.bot, dispatcher.bot_data["admin_ids"])

        # Register handlers
        register_user_handlers(dispatcher)
        register_admin_handlers(dispatcher)
        register_search_handlers(dispatcher)
        register_payment_handlers(dispatcher)

        # Register menu handlers (now includes handler registration internally)
        register_menu_handlers(dispatcher)
        from telegram.ext import MessageHandler, Filters

        # Register callback query handler for premium toggle
        dispatcher.add_handler(CallbackQueryHandler(toggle_premium_callback, pattern="^toggle_premium_"))

        # Add error handler
        dispatcher.add_error_handler(error_handler)

        # Start the Bot
        updater.bot.delete_webhook(drop_pending_updates=True)
        updater.start_polling(drop_pending_updates=True)
        # Log that the bot has started
        logger.info("Bot started. Press Ctrl+C to stop.")

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        # Stop the updater gracefully
        if 'updater' in locals() and updater.running:
            updater.stop()
            logger.info("Updater stopped.")



def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a telegram message to notify the admin."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        # Send a message to the admin if an update is available
        if update.effective_chat:
            context.bot.send_message(chat_id=context.bot_data.get("admin_ids")[0], text=f"⚠️ Bot Error:\n{context.error}\n\nUpdate: {update}")
    except Exception as e:
        logger.error(f"Failed to send error message to admin: {e}")




if __name__ == '__main__':
    main()



