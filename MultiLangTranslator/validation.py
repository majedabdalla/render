"""
Integration module for MultiLangTranslator Bot

This module integrates all components of the bot and provides
validation functions to ensure everything works correctly.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional
from telegram import Update, Bot, ParseMode
from telegram.ext import CallbackContext

# Import core modules
from core.session import get_session_manager
from core.database import get_database_manager
from core.security import get_spam_protection
from core.notifications import get_notification_manager
from core.message_forwarder import get_message_forwarder

# Initialize logger
logger = logging.getLogger(__name__)

def validate_bot_configuration(bot: Bot, context: CallbackContext) -> Dict[str, Any]:
    """
    Validate the bot configuration and return a report.
    
    Args:
        bot: Telegram bot instance
        context: Callback context
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "info": []
    }
    
    # Check bot token
    try:
        bot_info = bot.get_me()
        results["info"].append(f"Bot connected successfully: @{bot_info.username}")
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Bot connection failed: {e}")
    
    # Check admin IDs
    admin_ids = context.bot_data.get("admin_ids", [])
    if not admin_ids:
        results["warnings"].append("No admin IDs configured")
    else:
        results["info"].append(f"Admin IDs configured: {', '.join(admin_ids)}")
    
    # Check target group ID
    target_group_id = context.bot_data.get("target_group_id")
    if not target_group_id:
        results["warnings"].append("No target group ID configured for message forwarding")
    else:
        results["info"].append(f"Target group ID configured: {target_group_id}")
    
    # Check supported languages
    supported_languages = context.bot_data.get("supported_languages", {})
    if not supported_languages:
        results["warnings"].append("No supported languages configured")
    else:
        results["info"].append(f"Supported languages: {', '.join(supported_languages.values())}")
    
    return results

def validate_language_files() -> Dict[str, Any]:
    """
    Validate language files and return a report.
    
    Returns:
        Dictionary with validation results
    """
    results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "info": []
    }
    
    # Get locales directory
    locales_dir = "locales"
    if not os.path.exists(locales_dir):
        results["success"] = False
        results["errors"].append(f"Locales directory not found: {locales_dir}")
        return results
    
    # Get language files
    language_files = [f for f in os.listdir(locales_dir) if f.endswith(".json")]
    if not language_files:
        results["success"] = False
        results["errors"].append("No language files found")
        return results
    
    results["info"].append(f"Found {len(language_files)} language files: {', '.join(language_files)}")
    
    # Load English language file as reference
    en_file = os.path.join(locales_dir, "en.json")
    if not os.path.exists(en_file):
        results["success"] = False
        results["errors"].append("English language file not found")
        return results
    
    try:
        with open(en_file, "r", encoding="utf-8") as f:
            en_data = json.load(f)
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Error loading English language file: {e}")
        return results
    
    # Check each language file
    for lang_file in language_files:
        if lang_file == "en.json":
            continue
        
        lang_path = os.path.join(locales_dir, lang_file)
        try:
            with open(lang_path, "r", encoding="utf-8") as f:
                lang_data = json.load(f)
            
            # Check for missing keys
            missing_keys = [key for key in en_data if key not in lang_data]
            if missing_keys:
                results["warnings"].append(f"{lang_file} is missing {len(missing_keys)} keys: {', '.join(missing_keys[:5])}{'...' if len(missing_keys) > 5 else ''}")
            
            # Check for extra keys
            extra_keys = [key for key in lang_data if key not in en_data]
            if extra_keys:
                results["warnings"].append(f"{lang_file} has {len(extra_keys)} extra keys: {', '.join(extra_keys[:5])}{'...' if len(extra_keys) > 5 else ''}")
            
            results["info"].append(f"{lang_file}: {len(lang_data)} keys ({len(missing_keys)} missing, {len(extra_keys)} extra)")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Error loading {lang_file}: {e}")
    
    return results

def validate_core_modules() -> Dict[str, Any]:
    """
    Validate core modules and return a report.
    
    Returns:
        Dictionary with validation results
    """
    results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "info": []
    }
    
    # Check session manager
    try:
        session_manager = get_session_manager()
        results["info"].append("Session manager is available")
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Session manager not available: {e}")
    
    # Check database manager
    try:
        db_manager = get_database_manager()
        results["info"].append("Database manager is available")
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Database manager not available: {e}")
    
    # Check spam protection
    try:
        spam_protection = get_spam_protection()
        results["info"].append("Spam protection is available")
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Spam protection not available: {e}")
    
    # Check notification manager
    try:
        notification_manager = get_notification_manager()
        results["info"].append("Notification manager is available")
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Notification manager not available: {e}")
    
    # Check message forwarder
    try:
        message_forwarder = get_message_forwarder()
        results["info"].append("Message forwarder is available")
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Message forwarder not available: {e}")
    
    return results

def validate_handlers(dispatcher) -> Dict[str, Any]:
    """
    Validate handlers and return a report.
    
    Args:
        dispatcher: Telegram dispatcher
        
    Returns:
        Dictionary with validation results
    """
    results = {
        "success": True,
        "errors": [],
        "warnings": [],
        "info": []
    }
    
    # Check handlers
    handlers = dispatcher.handlers
    if not handlers:
        results["success"] = False
        results["errors"].append("No handlers registered")
        return results
    
    # Count handlers by group
    handler_counts = {}
    for group in handlers:
        handler_counts[group] = len(handlers[group])
    
    results["info"].append(f"Handler groups: {handler_counts}")
    
    # Check specific handlers
    command_handlers = []
    for group in handlers:
        for handler in handlers[group]:
            if hasattr(handler, 'command'):
                command_handlers.extend(handler.command)
    
    results["info"].append(f"Command handlers: {', '.join(sorted(command_handlers))}")
    
    # Check required commands
    required_commands = ['start', 'menu', 'hidemenu', 'help', 'settings', 'profile', 'search', 'payment', 'cancel']
    missing_commands = [cmd for cmd in required_commands if cmd not in command_handlers]
    
    if missing_commands:
        results["warnings"].append(f"Missing command handlers: {', '.join(missing_commands)}")
    
    return results

def send_validation_report(bot: Bot, admin_id: str, report: Dict[str, Any]) -> None:
    """
    Send a validation report to an admin.
    
    Args:
        bot: Telegram bot instance
        admin_id: Admin ID to send the report to
        report: Validation report
    """
    # Create report message
    message = f"<b>🔍 Bot Validation Report</b>\n\n"
    
    # Add overall status
    if report["success"]:
        message += "✅ <b>Overall Status:</b> Success\n\n"
    else:
        message += "❌ <b>Overall Status:</b> Failed\n\n"
    
    # Add errors
    if report["errors"]:
        message += f"<b>Errors ({len(report['errors'])}):</b>\n"
        for i, error in enumerate(report["errors"], 1):
            message += f"{i}. ❌ {error}\n"
        message += "\n"
    
    # Add warnings
    if report["warnings"]:
        message += f"<b>Warnings ({len(report['warnings'])}):</b>\n"
        for i, warning in enumerate(report["warnings"], 1):
            message += f"{i}. ⚠️ {warning}\n"
        message += "\n"
    
    # Add info
    if report["info"]:
        message += f"<b>Info ({len(report['info'])}):</b>\n"
        for i, info in enumerate(report["info"], 1):
            message += f"{i}. ℹ️ {info}\n"
    
    # Send message
    try:
        bot.send_message(
            chat_id=admin_id,
            text=message,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error sending validation report: {e}")

def run_full_validation(bot: Bot, context: CallbackContext, admin_id: str) -> Dict[str, Any]:
    """
    Run a full validation of the bot and send a report to the admin.
    
    Args:
        bot: Telegram bot instance
        context: Callback context
        admin_id: Admin ID to send the report to
        
    Returns:
        Dictionary with validation results
    """
    # Create overall report
    overall_report = {
        "success": True,
        "errors": [],
        "warnings": [],
        "info": []
    }
    
    # Validate bot configuration
    config_report = validate_bot_configuration(bot, context)
    overall_report["success"] &= config_report["success"]
    overall_report["errors"].extend([f"[Config] {e}" for e in config_report["errors"]])
    overall_report["warnings"].extend([f"[Config] {w}" for w in config_report["warnings"]])
    overall_report["info"].extend([f"[Config] {i}" for i in config_report["info"]])
    
    # Validate language files
    lang_report = validate_language_files()
    overall_report["success"] &= lang_report["success"]
    overall_report["errors"].extend([f"[Lang] {e}" for e in lang_report["errors"]])
    overall_report["warnings"].extend([f"[Lang] {w}" for w in lang_report["warnings"]])
    overall_report["info"].extend([f"[Lang] {i}" for i in lang_report["info"]])
    
    # Validate core modules
    core_report = validate_core_modules()
    overall_report["success"] &= core_report["success"]
    overall_report["errors"].extend([f"[Core] {e}" for e in core_report["errors"]])
    overall_report["warnings"].extend([f"[Core] {w}" for w in core_report["warnings"]])
    overall_report["info"].extend([f"[Core] {i}" for i in core_report["info"]])
    
    # Validate handlers
    handler_report = validate_handlers(context.dispatcher)
    overall_report["success"] &= handler_report["success"]
    overall_report["errors"].extend([f"[Handlers] {e}" for e in handler_report["errors"]])
    overall_report["warnings"].extend([f"[Handlers] {w}" for w in handler_report["warnings"]])
    overall_report["info"].extend([f"[Handlers] {i}" for i in handler_report["info"]])
    
    # Send report to admin
    send_validation_report(bot, admin_id, overall_report)
    
    return overall_report
