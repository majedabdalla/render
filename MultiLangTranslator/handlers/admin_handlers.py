"""
Admin handlers module for MultiLangTranslator Bot

This module provides admin dashboard functionality including:
- User management (block/unblock)
- Payment verification
- User statistics
- Broadcast messages
- Bot monitoring
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler

# Import core modules
from core.session import require_profile
from core.database import get_database_manager
from core.security import get_spam_protection
from core.notifications import get_notification_manager
from localization import get_text

# Initialize logger
logger = logging.getLogger(__name__)

# Admin authentication decorator
def admin_only(func):
    """
    Decorator to ensure only admins can access a handler.
    
    Args:
        func: The handler function to decorate
        
    Returns:
        Wrapped function that checks for admin privileges
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check if user is an admin
        if str(user_id) not in context.bot_data.get("admin_ids", []):
            logger.warning(f"Unauthorized access attempt to admin function by user {user_id}")
            update.message.reply_text("⛔ You are not authorized to use this command.")
            return
        
        return func(update, context, *args, **kwargs)
    
    return wrapper

# Admin dashboard command
@admin_only
def admin_dashboard(update: Update, context: CallbackContext) -> None:
    """Display admin dashboard with statistics and options."""
    user_id = update.effective_user.id
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Get user statistics
    all_users = db_manager.get_all_users()
    premium_users = db_manager.query_users({"premium": True})
    
    # Get spam protection statistics
    spam_protection = get_spam_protection()
    blocked_users = spam_protection.get_blocked_users()
    
    # Get session statistics
    from core.session import get_session_manager
    session_manager = get_session_manager()
    active_users, total_sessions = session_manager.get_session_count()
    
    # Build dashboard message
    message = "🔐 <b>Admin Dashboard</b>\n\n"
    message += f"👥 <b>Total Users:</b> {len(all_users)}\n"
    message += f"⭐ <b>Premium Users:</b> {len(premium_users)}\n"
    message += f"🚫 <b>Blocked Users:</b> {len(blocked_users)}\n"
    message += f"🟢 <b>Active Sessions:</b> {active_users} users, {total_sessions} sessions\n\n"
    
    # Create keyboard with admin options
    keyboard = [
        [
            InlineKeyboardButton("👥 User List", callback_data="admin_users"),
            InlineKeyboardButton("💳 Pending Payments", callback_data="admin_payments")
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("🔄 System Status", callback_data="admin_status")
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send dashboard
    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Admin dashboard callback handler
@admin_only
def admin_dashboard_callback(update: Update, context: CallbackContext) -> None:
    """Handle admin dashboard button clicks."""
    query = update.callback_query
    query.answer()
    
    action = query.data
    
    if action == "admin_users":
        show_user_list(update, context)
    elif action == "admin_payments":
        show_pending_payments(update, context)
    elif action == "admin_stats":
        show_statistics(update, context)
    elif action == "admin_status":
        show_system_status(update, context)
    elif action == "admin_broadcast":
        start_broadcast(update, context)
    elif action == "admin_settings":
        show_settings(update, context)
    elif action.startswith("block_user_"):
        user_id = action.split("_")[2]
        block_user(update, context, user_id)
    elif action.startswith("unblock_user_"):
        user_id = action.split("_")[2]
        unblock_user(update, context, user_id)
    elif action.startswith("approve_payment_"):
        payment_id = action.replace("approve_payment_", "")
        approve_payment(update, context, payment_id)
    elif action.startswith("reject_payment_"):
        payment_id = action.replace("reject_payment_", "")
        reject_payment(update, context, payment_id)
    elif action == "admin_back":
        # Go back to main dashboard
        query.edit_message_text(
            text="Returning to dashboard...",
            parse_mode=ParseMode.HTML
        )
        admin_dashboard(update, context)

# User list display
def show_user_list(update: Update, context: CallbackContext) -> None:
    """Show list of users with management options."""
    query = update.callback_query
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Get all users
    all_users = db_manager.get_all_users()
    
    # Get spam protection for blocked status
    spam_protection = get_spam_protection()
    
    # Pagination
    page = context.user_data.get("admin_user_page", 0)
    per_page = 5
    total_pages = (len(all_users) + per_page - 1) // per_page
    
    if page >= total_pages:
        page = 0
    
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(all_users))
    
    # Build user list message
    message = f"👥 <b>User List</b> (Page {page+1}/{total_pages})\n\n"
    
    for i in range(start_idx, end_idx):
        user_id = all_users[i]
        user_data = db_manager.get_user_data(user_id)
        
        # Get user status
        is_premium = "⭐" if user_data.get("premium", False) else "  "
        is_blocked = "🚫" if spam_protection.is_user_blocked(user_id) else "  "
        
        # Get user info
        name = user_data.get("name", "Unknown")
        language = user_data.get("language", "Unknown")
        
        message += f"{is_premium} {is_blocked} <b>ID:</b> {user_id}\n"
        message += f"    <b>Name:</b> {name}\n"
        message += f"    <b>Language:</b> {language}\n\n"
    
    # Create navigation keyboard
    keyboard = []
    
    # Add pagination buttons
    nav_row = []
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data="admin_users_prev"))
        nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="admin_users_page"))
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data="admin_users_next"))
        keyboard.append(nav_row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update message
    query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Pending payments display
def show_pending_payments(update: Update, context: CallbackContext) -> None:
    """Show list of pending payments for verification."""
    query = update.callback_query
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Get pending payments
    pending_payments = db_manager.get_pending_payments()
    
    # Build message
    if not pending_payments:
        message = "💳 <b>Pending Payments</b>\n\nNo pending payments to verify."
    else:
        message = f"💳 <b>Pending Payments</b> ({len(pending_payments)})\n\n"
        
        for payment_id, payment_data in pending_payments.items():
            user_id = payment_data.get("user_id", "Unknown")
            timestamp = payment_data.get("timestamp", 0)
            date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
            
            # Get user info
            user_data = db_manager.get_user_data(user_id)
            name = user_data.get("name", "Unknown")
            
            message += f"🆔 <b>Payment ID:</b> {payment_id}\n"
            message += f"👤 <b>User:</b> {name} (ID: {user_id})\n"
            message += f"📅 <b>Date:</b> {date_str}\n"
            
            # Add approve/reject buttons for each payment
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_payment_{payment_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_payment_{payment_id}")
                ]
            ]
            
            # Add back button
            keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Create keyboard
    keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update message
    query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Statistics display
def show_statistics(update: Update, context: CallbackContext) -> None:
    """Show detailed bot statistics."""
    query = update.callback_query
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Get user statistics
    all_users = db_manager.get_all_users()
    premium_users = db_manager.query_users({"premium": True})
    
    # Count users by language
    languages = {}
    for user_id in all_users:
        user_data = db_manager.get_user_data(user_id)
        lang = user_data.get("language", "unknown")
        languages[lang] = languages.get(lang, 0) + 1
    
    # Count users by region
    regions = {}
    for user_id in all_users:
        user_data = db_manager.get_user_data(user_id)
        region = user_data.get("region", "unknown")
        regions[region] = regions.get(region, 0) + 1
    
    # Build statistics message
    message = "📊 <b>Bot Statistics</b>\n\n"
    
    # User counts
    message += f"👥 <b>Total Users:</b> {len(all_users)}\n"
    message += f"⭐ <b>Premium Users:</b> {len(premium_users)} ({len(premium_users)/len(all_users)*100:.1f}%)\n\n"
    
    # Language distribution
    message += "<b>Language Distribution:</b>\n"
    for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
        message += f"  • {lang}: {count} ({count/len(all_users)*100:.1f}%)\n"
    
    message += "\n<b>Region Distribution:</b>\n"
    for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True)[:5]:
        message += f"  • {region}: {count} ({count/len(all_users)*100:.1f}%)\n"
    
    # Create keyboard
    keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update message
    query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# System status display
def show_system_status(update: Update, context: CallbackContext) -> None:
    """Show system status and performance metrics."""
    query = update.callback_query
    
    # Get session manager
    from core.session import get_session_manager
    session_manager = get_session_manager()
    
    # Get active users and sessions
    active_users, total_sessions = session_manager.get_session_count()
    
    # Get spam protection status
    spam_protection = get_spam_protection()
    blocked_users = spam_protection.get_blocked_users()
    
    # Get uptime
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    uptime = time.time() - process.create_time()
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Memory usage
    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    
    # Build status message
    message = "🔄 <b>System Status</b>\n\n"
    
    message += f"⏱️ <b>Uptime:</b> {int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s\n"
    message += f"💾 <b>Memory Usage:</b> {memory_usage:.1f} MB\n"
    message += f"🟢 <b>Active Users:</b> {active_users}\n"
    message += f"📝 <b>Active Sessions:</b> {total_sessions}\n"
    message += f"🚫 <b>Blocked Users:</b> {len(blocked_users)}\n"
    
    # Create keyboard
    keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update message
    query.edit_message_text(
        text=message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Broadcast message to users
def start_broadcast(update: Update, context: CallbackContext) -> None:
    """Start the broadcast message process."""
    query = update.callback_query
    
    # Create keyboard for broadcast options
    keyboard = [
        [
            InlineKeyboardButton("📢 All Users", callback_data="broadcast_all"),
            InlineKeyboardButton("⭐ Premium Users", callback_data="broadcast_premium")
        ],
        [
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update message
    query.edit_message_text(
        text="📢 <b>Broadcast Message</b>\n\nSelect target audience for your broadcast:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Settings display
def show_settings(update: Update, context: CallbackContext) -> None:
    """Show admin settings."""
    query = update.callback_query
    
    # Create keyboard for settings
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Bot Settings", callback_data="settings_bot"),
            InlineKeyboardButton("🛡️ Security Settings", callback_data="settings_security")
        ],
        [
            InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_back")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update message
    query.edit_message_text(
        text="⚙️ <b>Admin Settings</b>\n\nSelect a settings category:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Block user command
@admin_only
def block_user_command(update: Update, context: CallbackContext) -> None:
    """Block a user by ID."""
    args = context.args
    
    if not args or not args[0].isdigit():
        update.message.reply_text("⚠️ Please provide a valid user ID to block.")
        return
    
    user_id = args[0]
    duration = 3600  # Default: 1 hour
    
    # Check for duration argument
    if len(args) > 1 and args[1].isdigit():
        duration = int(args[1])
    
    # Block the user
    spam_protection = get_spam_protection()
    spam_protection.block_user(user_id, duration)
    
    # Notify admin
    update.message.reply_text(f"🚫 User {user_id} has been blocked for {duration} seconds.")
    
    # Notify user
    notification_manager = get_notification_manager()
    notification_manager.notify_user(
        user_id,
        "⚠️ Your account has been temporarily restricted by an administrator."
    )

# Unblock user command
@admin_only
def unblock_user_command(update: Update, context: CallbackContext) -> None:
    """Unblock a user by ID."""
    args = context.args
    
    if not args or not args[0].isdigit():
        update.message.reply_text("⚠️ Please provide a valid user ID to unblock.")
        return
    
    user_id = args[0]
    
    # Unblock the user
    spam_protection = get_spam_protection()
    result = spam_protection.unblock_user(user_id)
    
    if result:
        # Notify admin
        update.message.reply_text(f"✅ User {user_id} has been unblocked.")
        
        # Notify user
        notification_manager = get_notification_manager()
        notification_manager.notify_user(
            user_id,
            "✅ Your account restrictions have been lifted by an administrator."
        )
    else:
        update.message.reply_text(f"ℹ️ User {user_id} was not blocked.")

# Block user from callback
def block_user(update: Update, context: CallbackContext, user_id: str) -> None:
    """Block a user from callback query."""
    query = update.callback_query
    
    # Block the user
    spam_protection = get_spam_protection()
    spam_protection.block_user(user_id)
    
    # Notify admin
    query.answer(f"User {user_id} has been blocked.")
    
    # Notify user
    notification_manager = get_notification_manager()
    notification_manager.notify_user(
        user_id,
        "⚠️ Your account has been temporarily restricted by an administrator."
    )
    
    # Return to user list
    show_user_list(update, context)

# Unblock user from callback
def unblock_user(update: Update, context: CallbackContext, user_id: str) -> None:
    """Unblock a user from callback query."""
    query = update.callback_query
    
    # Unblock the user
    spam_protection = get_spam_protection()
    result = spam_protection.unblock_user(user_id)
    
    if result:
        # Notify admin
        query.answer(f"User {user_id} has been unblocked.")
        
        # Notify user
        notification_manager = get_notification_manager()
        notification_manager.notify_user(
            user_id,
            "✅ Your account restrictions have been lifted by an administrator."
        )
    else:
        query.answer(f"User {user_id} was not blocked.")
    
    # Return to user list
    show_user_list(update, context)

# Approve payment
def approve_payment(update: Update, context: CallbackContext, payment_id: str) -> None:
    """Approve a pending payment."""
    query = update.callback_query
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Update payment status
    admin_id = update.effective_user.id
    result = db_manager.update_payment_status(payment_id, "approved", admin_id)
    
    if result:
        # Get user ID from payment data
        payment_data = db_manager.pending_payments.get(payment_id, {})
        user_id = payment_data.get("user_id")
        
        if user_id:
            # Notify user
            notification_manager = get_notification_manager()
            notification_manager.notify_user(
                user_id,
                get_text(user_id, "feature_activated")
            )
        
        # Notify admin
        query.answer("Payment approved successfully.")
    else:
        query.answer("Error: Payment not found.")
    
    # Return to pending payments list
    show_pending_payments(update, context)

# Reject payment
def reject_payment(update: Update, context: CallbackContext, payment_id: str) -> None:
    """Reject a pending payment."""
    query = update.callback_query
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Update payment status
    admin_id = update.effective_user.id
    result = db_manager.update_payment_status(payment_id, "rejected", admin_id)
    
    if result:
        # Get user ID from payment data
        payment_data = db_manager.pending_payments.get(payment_id, {})
        user_id = payment_data.get("user_id")
        
        if user_id:
            # Notify user
            notification_manager = get_notification_manager()
            notification_manager.notify_user(
                user_id,
                get_text(user_id, "payment_rejected")
            )
        
        # Notify admin
        query.answer("Payment rejected successfully.")
    else:
        query.answer("Error: Payment not found.")
    
    # Return to pending payments list
    show_pending_payments(update, context)

# List users command
@admin_only
def list_users_command(update: Update, context: CallbackContext) -> None:
    """List all users with their basic info."""
    # Get database manager
    db_manager = get_database_manager()
    
    # Get all users
    all_users = db_manager.get_all_users()
    
    # Build message
    message = f"👥 <b>User List</b> (Total: {len(all_users)})\n\n"
    
    # Limit to first 10 users to avoid message size limits
    for i, user_id in enumerate(all_users[:10]):
        user_data = db_manager.get_user_data(user_id)
        
        # Get user info
        name = user_data.get("name", "Unknown")
        language = user_data.get("language", "Unknown")
        is_premium = "⭐" if user_data.get("premium", False) else "  "
        
        message += f"{i+1}. {is_premium} <b>ID:</b> {user_id}, <b>Name:</b> {name}, <b>Lang:</b> {language}\n"
    
    if len(all_users) > 10:
        message += f"\n... and {len(all_users) - 10} more users."
    
    # Send message
    update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML
    )

# Verify payment callback
def verify_payment_callback(update: Update, context: CallbackContext) -> None:
    """Handle payment verification callbacks."""
    query = update.callback_query
    query.answer()
    
    # Extract payment ID from callback data
    data = query.data
    action, payment_id = data.split("_", 1)
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Update payment status
    admin_id = update.effective_user.id
    status = "approved" if action == "approve" else "rejected"
    
    result = db_manager.update_payment_status(payment_id, status, admin_id)
    
    if result:
        # Get user ID from payment data
        payment_data = db_manager.pending_payments.get(payment_id, {})
        user_id = payment_data.get("user_id")
        
        if user_id:
            # Notify user
            notification_manager = get_notification_manager()
            
            if status == "approved":
                message = get_text(user_id, "feature_activated")
            else:
                message = get_text(user_id, "payment_rejected")
            
            notification_manager.notify_user(user_id, message)
        
        # Update admin message
        query.edit_message_text(
            f"Payment {status}. User has been notified.",
            parse_mode=ParseMode.HTML
        )
    else:
        query.edit_message_text(
            "Error: Payment not found or already processed.",
            parse_mode=ParseMode.HTML
        )

# Register handlers
def register_admin_handlers(dispatcher):
    """Register all admin handlers with the dispatcher."""
    # Admin dashboard
    dispatcher.add_handler(CommandHandler("admin", admin_dashboard))
    dispatcher.add_handler(CallbackQueryHandler(admin_dashboard_callback, pattern="^admin_"))
    
    # Block/unblock commands
    dispatcher.add_handler(CommandHandler("block", block_user_command))
    dispatcher.add_handler(CommandHandler("unblock", unblock_user_command))
    
    # List users command
    dispatcher.add_handler(CommandHandler("users", list_users_command))
    
    # Payment verification
    dispatcher.add_handler(CallbackQueryHandler(verify_payment_callback, pattern="^(approve|reject)_payment_"))



# Toggle premium status callback
@admin_only
def toggle_premium_callback(update: Update, context: CallbackContext) -> None:
    """Toggle a user's premium status."""
    query = update.callback_query
    query.answer()

    data = query.data.split('_')
    user_id_to_toggle = data[2]

    db_manager = get_database_manager()
    user_data = db_manager.get_user_data(user_id_to_toggle)
    notification_manager = get_notification_manager()

    is_premium = user_data.get("premium", False)

    if is_premium:
        # Downgrade to non-premium
        db_manager.update_user_data(user_id_to_toggle, {"premium": False, "premium_expiry": None})
        message_to_admin = f"✅ تم إلغاء ترقية المستخدم {user_id_to_toggle} إلى بريميوم."
        message_to_user = get_text(user_id_to_toggle, "premium_revoked")
    else:
        # Upgrade to premium for 3 months
        premium_expiry = int(time.time()) + (90 * 24 * 60 * 60)  # 3 months from now
        db_manager.update_user_data(user_id_to_toggle, {"premium": True, "premium_expiry": premium_expiry})
        message_to_admin = f"✅ تم ترقية المستخدم {user_id_to_toggle} إلى بريميوم لمدة 3 أشهر."
        message_to_user = get_text(user_id_to_toggle, "premium_granted")

    # Notify admin
    query.edit_message_text(text=message_to_admin)

    # Notify user
    notification_manager.notify_user(user_id_to_toggle, message_to_user)

    logger.info(f"Admin {update.effective_user.id} toggled premium for user {user_id_to_toggle}. New status: {not is_premium}")


