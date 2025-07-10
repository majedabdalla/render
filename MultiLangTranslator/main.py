"""
Modified main.py with improved error handling and data validation
for MultiLangTranslator Bot
"""

import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from telegram import Update, Bot
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler,
                          CallbackContext)

# Import configuration
try:
    import config
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("config.py not found. Please ensure config.py exists.")
    exit(1)

# Import core modules (with error handling)
try:
    from core.session import init_session_manager
    from core.database import init_database_manager
    from core.security import init_spam_protection
    from core.notifications import init_notification_manager
    from core.data_validation import initialize_data_directories, validate_and_repair_data_files
except ImportError as e:
    # If core modules don't exist, create minimal functionality
    logger = logging.getLogger(__name__)
    logger.warning(f"Core modules not found: {e}")
    
    # Create placeholder functions
    def init_session_manager(file_path):
        return {}
    
    def init_database_manager(user_file, payment_file):
        return {}
    
    def init_spam_protection():
        return {}
    
    def init_notification_manager(bot, admin_ids):
        return {}
    
    def initialize_data_directories(config):
        os.makedirs("data", exist_ok=True)
        return True
    
    def validate_and_repair_data_files(config):
        return {}

# Import handlers (with error handling)
try:
    from handlers.user_handlers import register_user_handlers
    from handlers.admin_handlers import register_admin_handlers
    from handlers.search_handlers import register_search_handlers
    from handlers.payment_handlers import register_payment_handlers
    from handlers.menu_handlers import register_menu_handlers, menu_command, handle_menu_selection
    from handlers.admin_handlers import toggle_premium_callback
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Handler modules not found: {e}")
    
    # Create placeholder functions
    def register_user_handlers(dispatcher):
        pass
    
    def register_admin_handlers(dispatcher):
        pass
    
    def register_search_handlers(dispatcher):
        pass
    
    def register_payment_handlers(dispatcher):
        pass
    
    def register_menu_handlers(dispatcher):
        pass
    
    def toggle_premium_callback(update, context):
        pass

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_data_directories():
    """Setup necessary directories and files."""
    # Create basic data directory
    os.makedirs("data", exist_ok=True)
    
    # Create basic regions_countries.json if it doesn't exist
    regions_file = "data/regions_countries.json"
    if not os.path.exists(regions_file):
        basic_regions = {
            "Europe": ["Germany", "France", "Spain", "Italy"],
            "Asia": ["Japan", "China", "India", "South Korea"],
            "Americas": ["United States", "Canada", "Brazil", "Mexico"],
            "Africa": ["Nigeria", "Egypt", "South Africa", "Kenya"]
        }
        with open(regions_file, "w", encoding="utf-8") as f:
            json.dump(basic_regions, f, indent=2)
    
    # Use the new data validation module to initialize all directories and files
    try:
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
    except Exception as e:
        logger.warning(f"Error in data validation: {e}")


def main() -> None:
    """Start the bot."""
    logger.info("Starting bot...")

    # Check if BOT_TOKEN is available
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is not set!")
        return

    try:
        # Setup data directories and initialize files
        setup_data_directories()

        # Create the Updater and pass it your bot's token
        updater = Updater(token=bot_token)
        # Get the dispatcher to register handlers
        dispatcher = updater.dispatcher

        # Initialize bot data with safe defaults
        dispatcher.bot_data.update({
            "supported_languages": getattr(config, 'SUPPORTED_LANGUAGES', ['en', 'es', 'fr']),
            "admin_ids": [str(getattr(config, 'ADMIN_ID', ''))],
            "target_group_id": getattr(config, 'TARGET_GROUP_ID', ''),
            "payeer_account": getattr(config, 'PAYEER_ACCOUNT', ''),
            "bitcoin_address": getattr(config, 'BITCOIN_ADDRESS', ''),

            # Conversation states
            "SELECT_LANG": getattr(config, 'SELECT_LANG', 1),
            "SELECT_GENDER": getattr(config, 'SELECT_GENDER', 2),
            "SELECT_REGION": getattr(config, 'SELECT_REGION', 3),
            "SELECT_COUNTRY_IN_REGION": getattr(config, 'SELECT_COUNTRY_IN_REGION', 4),
            "SEARCH_PARTNER_LANG": getattr(config, 'SEARCH_PARTNER_LANG', 5),
            "SEARCH_PARTNER_GENDER": getattr(config, 'SEARCH_PARTNER_GENDER', 6),
            "SEARCH_PARTNER_REGION": getattr(config, 'SEARCH_PARTNER_REGION', 7),
            "SEARCH_PARTNER_COUNTRY": getattr(config, 'SEARCH_PARTNER_COUNTRY', 8),
            "PAYMENT_PROOF": getattr(config, 'PAYMENT_PROOF', 9)
        })

        # Load countries by region from file
        try:
            with open("data/regions_countries.json", "r", encoding="utf-8") as f:
                dispatcher.bot_data["countries_by_region"] = json.load(f)
        except Exception as e:
            logger.warning(f"Couldn't load regions_countries.json: {e}")
            dispatcher.bot_data["countries_by_region"] = {}

        # Initialize core modules
        try:
            session_manager = init_session_manager("data/sessions.json")
            db_manager = init_database_manager(
                getattr(config, 'USER_DATA_FILE', 'data/users.json'),
                getattr(config, 'PENDING_PAYMENTS_FILE', 'data/payments.json')
            )
            spam_protection = init_spam_protection()
            notification_manager = init_notification_manager(
                updater.bot, dispatcher.bot_data["admin_ids"])
        except Exception as e:
            logger.warning(f"Error initializing core modules: {e}")

        # Register handlers
        try:
            register_user_handlers(dispatcher)
            register_admin_handlers(dispatcher)
            register_search_handlers(dispatcher)
            register_payment_handlers(dispatcher)
            register_menu_handlers(dispatcher)
            
            # Register callback query handler for premium toggle
            dispatcher.add_handler(CallbackQueryHandler(toggle_premium_callback, pattern="^toggle_premium_"))
        except Exception as e:
            logger.warning(f"Error registering handlers: {e}")

        # Add a simple start command as fallback
        def start_command(update: Update, context: CallbackContext):
            update.message.reply_text("🤖 MultiLangTranslator Bot is running!\n\nBot is operational and ready to serve.")
        
        dispatcher.add_handler(CommandHandler("start", start_command))

        # Add error handler
        dispatcher.add_error_handler(error_handler)

        # Start the Bot
        updater.bot.delete_webhook(drop_pending_updates=True)
        updater.start_polling(drop_pending_updates=True)
        
        # Log that the bot has started
        logger.info("Bot started successfully! Press Ctrl+C to stop.")
        
        # Run the bot until you press Ctrl-C
        updater.idle()

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise e
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
        admin_ids = context.bot_data.get("admin_ids", [])
        if update and hasattr(update, 'effective_chat') and update.effective_chat and admin_ids and admin_ids[0]:
            context.bot.send_message(
                chat_id=admin_ids[0], 
                text=f"⚠️ Bot Error:\n{context.error}\n\nUpdate: {update}"
            )
    except Exception as e:
        logger.error(f"Failed to send error message to admin: {e}")


if __name__ == '__main__':
    main()
