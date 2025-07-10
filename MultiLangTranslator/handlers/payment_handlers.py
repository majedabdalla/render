"""
Payment handlers module for MultiLangTranslator Bot

This module provides payment functionality including:
- Payment verification
- Premium feature activation
- Payment status tracking
"""

import logging
import time
from typing import Dict, List, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, ConversationHandler

# Import core modules
from core.session import require_profile
from core.database import get_database_manager
from core.notifications import get_notification_manager
from localization import get_text

# Initialize logger
logger = logging.getLogger(__name__)

@require_profile
def payment_command(update: Update, context: CallbackContext) -> None:
    """Handle the /payment command to show payment options."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Get user data
    user_data = db_manager.get_user_data(user_id)
    
    # Check if user already has premium
    if user_data.get("premium", False):
        update.message.reply_text(
            get_text(user_id, "feature_already_activated"),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Get payment details from bot data
    payeer_account = context.bot_data.get("payeer_account", "N/A")
    bitcoin_address = context.bot_data.get("bitcoin_address", "N/A")
    
    # Create payment message
    message = get_text(
        user_id, 
        "payment_prompt", 
        payeer_account=payeer_account,
        bitcoin_address=bitcoin_address
    )
    
    # Create keyboard with payment verification button
    keyboard = [
        [InlineKeyboardButton(
            get_text(user_id, "payment_verify_button"), 
            callback_data="verify_payment"
        )]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send payment message
    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

def payment_verification_callback(update: Update, context: CallbackContext) -> int:
    """Handle payment verification button click."""
    query = update.callback_query
    query.answer()
    
    user = update.effective_user
    user_id = str(user.id)
    
    # Ask user to send payment proof
    query.edit_message_text(
        get_text(user_id, "payment_send_proof"),
        parse_mode=ParseMode.HTML
    )
    
    return context.bot_data.get("PAYMENT_PROOF", 8)

def handle_payment_proof(update: Update, context: CallbackContext) -> int:
    """Handle payment proof submission."""
    user = update.effective_user
    user_id = str(user.id)
    
    # Get database manager
    db_manager = get_database_manager()
    
    # Check if message contains media or text
    has_proof = False
    proof_type = None
    
    if update.message.photo:
        has_proof = True
        proof_type = "photo"
    elif update.message.document:
        has_proof = True
        proof_type = "document"
    elif update.message.text:
        has_proof = True
        proof_type = "text"
    
    if not has_proof:
        # No proof provided, ask again
        update.message.reply_text(
            get_text(user_id, "payment_send_proof_reminder"),
            parse_mode=ParseMode.HTML
        )
        return context.bot_data.get("PAYMENT_PROOF", 8)
    
    # Create payment record
    payment_data = {
        "proof_type": proof_type,
        "timestamp": int(time.time())
    }
    
    if proof_type == "text":
        payment_data["text"] = update.message.text
    elif proof_type == "photo":
        payment_data["file_id"] = update.message.photo[-1].file_id
    elif proof_type == "document":
        payment_data["file_id"] = update.message.document.file_id
        payment_data["file_name"] = update.message.document.file_name
    
    # Add payment to pending payments
    payment_id = db_manager.add_pending_payment(user_id, payment_data)
    
    # Notify user
    update.message.reply_text(
        get_text(user_id, "payment_received_pending_verification"),
        parse_mode=ParseMode.HTML
    )
    
    # Notify admins
    notification_manager = get_notification_manager()
    
    # Get admin IDs from bot data
    admin_ids = context.bot_data.get("admin_ids", [])
    
    for admin_id in admin_ids:
        # Create admin notification
        admin_message = f"💳 <b>New Payment Verification</b>\n\n"
        admin_message += f"👤 <b>User:</b> {user.first_name}"
        if user.last_name:
            admin_message += f" {user.last_name}"
        if user.username:
            admin_message += f" (@{user.username})"
        admin_message += f"\n🆔 <b>User ID:</b> {user_id}\n"
        admin_message += f"⏱️ <b>Time:</b> {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n\n"
        
        if proof_type == "text":
            admin_message += f"📝 <b>Proof (Text):</b>\n{payment_data['text']}"
        else:
            admin_message += f"📎 <b>Proof:</b> {proof_type.capitalize()} attached"
        
        # Create keyboard for admin approval/rejection
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_payment_{payment_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_payment_{payment_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send notification to admin
        notification_manager.notify_user(
            admin_id,
            admin_message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        # If proof is media, forward it to admin
        if proof_type == "photo" or proof_type == "document":
            try:
                if proof_type == "photo":
                    context.bot.send_photo(
                        chat_id=admin_id,
                        photo=payment_data["file_id"],
                        caption=f"Payment proof from User ID: {user_id}"
                    )
                else:
                    context.bot.send_document(
                        chat_id=admin_id,
                        document=payment_data["file_id"],
                        caption=f"Payment proof from User ID: {user_id}"
                    )
            except Exception as e:
                logger.error(f"Error forwarding media to admin {admin_id}: {e}")
    
    return ConversationHandler.END

# Register handlers
def register_payment_handlers(dispatcher):
    """Register all payment handlers with the dispatcher."""
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler
    
    # Payment command
    dispatcher.add_handler(CommandHandler("payment", payment_command))
    
    # Payment verification conversation
    payment_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(payment_verification_callback, pattern="^verify_payment$")],
        states={
            dispatcher.bot_data.get("PAYMENT_PROOF", 8): [
                MessageHandler(Filters.all & ~Filters.command, handle_payment_proof)
            ],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        name="payment_conversation",
        persistent=False
    )
    
    dispatcher.add_handler(payment_conv_handler)
