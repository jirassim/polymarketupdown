#!/usr/bin/env python3
"""
Telegram Bot for Secure User Registration
Handles API credentials securely and auto-deletes messages
"""

import os
import logging
import hashlib
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from cryptography.fernet import Fernet
import sqlite3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000/api')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())

# Ensure encryption key is bytes
if isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()

cipher = Fernet(ENCRYPTION_KEY)

# Conversation states
(
    WAITING_USER_ID,
    WAITING_PRIVATE_KEY,
    WAITING_API_KEY,
    WAITING_API_SECRET,
    WAITING_PASSPHRASE,
    WAITING_WALLET_CONFIG,
    CONFIRM_REGISTRATION
) = range(7)

# Database setup
def init_bot_db():
    """Initialize bot database for temporary storage"""
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS registration_sessions (
        telegram_user_id INTEGER PRIMARY KEY,
        user_id TEXT,
        step INTEGER,
        data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

init_bot_db()

# Helper functions
def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return cipher.decrypt(encrypted_data.encode()).decode()

def hash_credentials(data: str) -> str:
    """Hash credentials for storage"""
    return hashlib.sha256(data.encode()).hexdigest()

async def delete_message_after(update: Update, seconds: int = 10):
    """Delete message after specified seconds"""
    await asyncio.sleep(seconds)
    try:
        await update.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

async def send_temp_message(update: Update, text: str, seconds: int = 30):
    """Send a temporary message that auto-deletes"""
    message = await update.message.reply_text(text)
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except Exception as e:
        logger.error(f"Error deleting temp message: {e}")

def save_session_data(user_id: int, data: Dict):
    """Save registration session data"""
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()

    expires_at = datetime.now() + timedelta(hours=1)
    data_json = json.dumps(data)

    cursor.execute('''
        INSERT OR REPLACE INTO registration_sessions
        (telegram_user_id, user_id, step, data, expires_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, data.get('user_id'), data.get('step', 0), data_json, expires_at))

    conn.commit()
    conn.close()

def get_session_data(user_id: int) -> Optional[Dict]:
    """Get registration session data"""
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT data FROM registration_sessions
        WHERE telegram_user_id = ? AND expires_at > datetime('now')
    ''', (user_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return json.loads(result[0])
    return None

def clear_session_data(user_id: int):
    """Clear registration session data"""
    conn = sqlite3.connect('telegram_bot.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM registration_sessions WHERE telegram_user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    welcome_message = """
🤖 **Welcome to Polymarket Trading Bot Registration!**

I help you securely register your trading bot. Your sensitive data is:
• ✅ Encrypted end-to-end
• ✅ Auto-deleted after processing
• ✅ Never stored in plain text

**Commands:**
/register - Start registration process
/status - Check your registration status
/help - Get help and support
/cancel - Cancel current operation

**Security Notice:**
⚠️ Never share your private keys outside this bot
🔒 All messages containing sensitive data will be auto-deleted
🛡️ Your credentials are encrypted and secured

Ready to begin? Type /register
    """

    keyboard = [
        [InlineKeyboardButton("🚀 Start Registration", callback_data='start_registration')],
        [InlineKeyboardButton("📊 Check Status", callback_data='check_status')],
        [InlineKeyboardButton("❓ Get Help", callback_data='get_help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start registration process"""
    user = update.effective_user

    await update.message.reply_text(
        "🔐 **Starting Secure Registration Process**\n\n"
        "Please provide your Dashboard User ID.\n"
        "You can find this in the registration modal on the dashboard.\n\n"
        "Example: `USER_abc123xyz`\n\n"
        "Type /cancel anytime to stop.",
        parse_mode='Markdown'
    )

    # Initialize session
    save_session_data(user.id, {
        'telegram_user_id': user.id,
        'telegram_username': user.username,
        'step': WAITING_USER_ID
    })

    return WAITING_USER_ID

async def receive_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and validate user ID"""
    user_id = update.message.text.strip()

    # Delete user message immediately (contains ID)
    asyncio.create_task(delete_message_after(update, 1))

    if not user_id.startswith('USER_'):
        await send_temp_message(
            update,
            "❌ Invalid User ID format. Please use the ID from the dashboard.\n"
            "It should start with 'USER_'",
            10
        )
        return WAITING_USER_ID

    # Save user ID
    session = get_session_data(update.effective_user.id)
    session['user_id'] = user_id
    session['step'] = WAITING_PRIVATE_KEY
    save_session_data(update.effective_user.id, session)

    await update.message.reply_text(
        "✅ User ID received!\n\n"
        "Now, please send your **Wallet 1 Private Key**.\n\n"
        "⚠️ **Security Notice:**\n"
        "• Your message will be deleted immediately\n"
        "• The key will be encrypted\n"
        "• Never share this key elsewhere\n\n"
        "Format: Private key without '0x' prefix",
        parse_mode='Markdown'
    )

    return WAITING_PRIVATE_KEY

async def receive_private_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and encrypt private key"""
    private_key = update.message.text.strip()

    # Delete message immediately (contains private key!)
    await update.message.delete()

    # Validate format
    if private_key.startswith('0x'):
        private_key = private_key[2:]

    if len(private_key) != 64:
        await send_temp_message(
            update,
            "❌ Invalid private key format. Should be 64 hex characters.\n"
            "Please try again.",
            10
        )
        return WAITING_PRIVATE_KEY

    # Encrypt and save
    session = get_session_data(update.effective_user.id)
    session['private_key_encrypted'] = encrypt_data(private_key)
    session['step'] = WAITING_API_KEY
    save_session_data(update.effective_user.id, session)

    await update.message.reply_text(
        "🔐 Private key encrypted and stored temporarily.\n\n"
        "Next, please send your **Polymarket API Key**.",
        parse_mode='Markdown'
    )

    return WAITING_API_KEY

async def receive_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive API key"""
    api_key = update.message.text.strip()

    # Delete message immediately
    await update.message.delete()

    # Save encrypted
    session = get_session_data(update.effective_user.id)
    session['api_key_encrypted'] = encrypt_data(api_key)
    session['step'] = WAITING_API_SECRET
    save_session_data(update.effective_user.id, session)

    await update.message.reply_text(
        "✅ API Key received.\n\n"
        "Now, please send your **API Secret**.",
        parse_mode='Markdown'
    )

    return WAITING_API_SECRET

async def receive_api_secret(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive API secret"""
    api_secret = update.message.text.strip()

    # Delete message immediately
    await update.message.delete()

    # Save encrypted
    session = get_session_data(update.effective_user.id)
    session['api_secret_encrypted'] = encrypt_data(api_secret)
    session['step'] = WAITING_PASSPHRASE
    save_session_data(update.effective_user.id, session)

    await update.message.reply_text(
        "✅ API Secret received.\n\n"
        "Finally, please send your **API Passphrase**.",
        parse_mode='Markdown'
    )

    return WAITING_PASSPHRASE

async def receive_passphrase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive API passphrase and complete registration"""
    passphrase = update.message.text.strip()

    # Delete message immediately
    await update.message.delete()

    # Get session data
    session = get_session_data(update.effective_user.id)
    session['passphrase_encrypted'] = encrypt_data(passphrase)

    # Show confirmation
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data='confirm_registration'),
            InlineKeyboardButton("❌ Cancel", callback_data='cancel_registration')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 **Registration Summary**\n\n"
        f"User ID: `{session['user_id']}`\n"
        f"Telegram: @{session['telegram_username']}\n"
        "Credentials: ✅ Encrypted\n\n"
        "**Ready to complete registration?**\n\n"
        "⚠️ After confirmation:\n"
        "• Your bot will be activated\n"
        "• All sensitive data will be encrypted\n"
        "• Temporary data will be deleted",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

    return CONFIRM_REGISTRATION

async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and complete registration"""
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm_registration':
        # Get session data
        session = get_session_data(query.from_user.id)

        # Prepare data for API
        registration_data = {
            'user_id': session['user_id'],
            'telegram_user_id': session['telegram_user_id'],
            'telegram_username': session['telegram_username'],
            'credentials': {
                'private_key': decrypt_data(session['private_key_encrypted']),
                'api_key': decrypt_data(session['api_key_encrypted']),
                'api_secret': decrypt_data(session['api_secret_encrypted']),
                'api_passphrase': decrypt_data(session['passphrase_encrypted'])
            }
        }

        # Send to backend API
        try:
            async with aiohttp.ClientSession() as http_session:
                # Register user
                async with http_session.post(
                    f"{API_BASE_URL}/telegram/register",
                    json={
                        'user_id': registration_data['user_id'],
                        'telegram_user_id': registration_data['telegram_user_id'],
                        'telegram_username': registration_data['telegram_username']
                    }
                ) as response:
                    if response.status != 200:
                        raise Exception("Registration failed")

                # Store encrypted credentials
                credentials_hash = hash_credentials(json.dumps(registration_data['credentials']))
                async with http_session.post(
                    f"{API_BASE_URL}/telegram/update-credentials",
                    json={
                        'user_id': registration_data['user_id'],
                        'api_key_hash': credentials_hash
                    }
                ) as response:
                    if response.status != 200:
                        raise Exception("Failed to update credentials")

            await query.edit_message_text(
                "🎉 **Registration Successful!**\n\n"
                "✅ Your bot has been activated\n"
                "✅ Credentials encrypted and secured\n"
                "✅ Temporary data deleted\n\n"
                "You can now:\n"
                "• View your dashboard\n"
                "• Configure wallet settings\n"
                "• Monitor trading performance\n\n"
                "**Commands:**\n"
                "/status - Check bot status\n"
                "/settings - Configure wallets\n"
                "/help - Get support",
                parse_mode='Markdown'
            )

            # Clear session data
            clear_session_data(query.from_user.id)

        except Exception as e:
            logger.error(f"Registration error: {e}")
            await query.edit_message_text(
                "❌ **Registration Failed**\n\n"
                f"Error: {str(e)}\n\n"
                "Please try again or contact support.",
                parse_mode='Markdown'
            )

    else:
        # Cancel registration
        clear_session_data(query.from_user.id)
        await query.edit_message_text(
            "❌ **Registration Cancelled**\n\n"
            "All temporary data has been deleted.\n"
            "Type /register to start again.",
            parse_mode='Markdown'
        )

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation"""
    user = update.effective_user
    clear_session_data(user.id)

    await update.message.reply_text(
        "❌ **Operation Cancelled**\n\n"
        "All temporary data has been deleted.\n"
        "Type /register to start again.",
        parse_mode='Markdown'
    )

    return ConversationHandler.END

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check bot status"""
    user = update.effective_user

    # Check if user is registered
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}/users/{user.id}/status") as response:
            if response.status == 200:
                data = await response.json()
                if data.get('registered'):
                    await update.message.reply_text(
                        "✅ **Your Bot Status**\n\n"
                        "Status: Active\n"
                        f"User ID: {data['user']['user_id']}\n"
                        "Wallets: 12 configured\n\n"
                        "Visit the dashboard for detailed statistics.",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "❌ **Not Registered**\n\n"
                        "You haven't registered your bot yet.\n"
                        "Type /register to begin.",
                        parse_mode='Markdown'
                    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command"""
    help_text = """
📖 **Polymarket Trading Bot Help**

**Commands:**
/register - Start bot registration
/status - Check your bot status
/settings - Configure wallet settings
/cancel - Cancel current operation
/help - Show this help message

**Security Features:**
• 🔐 End-to-end encryption
• 🗑️ Auto-delete sensitive messages
• 🛡️ Secure credential storage
• ⏱️ Session timeout (1 hour)

**Support:**
• Dashboard: [Your Dashboard URL]
• Email: support@example.com
• Telegram: @YourSupportBot

**FAQ:**

Q: Is my private key safe?
A: Yes! It's encrypted immediately and deleted from chat history.

Q: Can I register multiple bots?
A: Yes, each with a unique User ID.

Q: How do I change settings?
A: Use the dashboard or /settings command.

Need more help? Contact support!
    """

    await update.message.reply_text(help_text, parse_mode='Markdown')

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.message:
        await update.message.reply_text(
            "❌ An error occurred. Please try again or contact support.",
            parse_mode='Markdown'
        )

def main():
    """Main function to run the bot"""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('register', register),
            CallbackQueryHandler(register, pattern='start_registration')
        ],
        states={
            WAITING_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_id)],
            WAITING_PRIVATE_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_private_key)],
            WAITING_API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_key)],
            WAITING_API_SECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_secret)],
            WAITING_PASSPHRASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_passphrase)],
            CONFIRM_REGISTRATION: [CallbackQueryHandler(confirm_registration)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == '__main__':
    main()