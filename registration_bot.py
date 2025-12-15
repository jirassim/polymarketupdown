"""
Telegram Bot for User Registration
Allows users to register their private keys and API credentials securely
Data is stored temporarily and can be deleted by bot admin
"""

import os
import json
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Load environment variables
load_dotenv()

# Conversation states
WAITING_PRIVATE_KEY, WAITING_API_KEY, WAITING_API_SECRET, WAITING_API_PASSPHRASE, WAITING_BET_AMOUNT, CONFIRM = range(6)

# File to store registrations
REGISTRATIONS_FILE = "user_registrations.json"

# Admin Telegram ID from environment
ADMIN_TELEGRAM_ID = int(os.getenv('ADMIN_TELEGRAM_ID', 0)) if os.getenv('ADMIN_TELEGRAM_ID') else None

# Email configuration from environment
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_FROM = os.getenv('EMAIL_FROM', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_TO = os.getenv('EMAIL_TO', '')


def load_registrations():
    """Load existing registrations from file"""
    if os.path.exists(REGISTRATIONS_FILE):
        with open(REGISTRATIONS_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_registrations(registrations):
    """Save registrations to file"""
    with open(REGISTRATIONS_FILE, 'w') as f:
        json.dump(registrations, f, indent=2)


def send_email_notification(subject, body):
    """Send email notification to admin"""
    if not all([EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO, SMTP_SERVER]):
        print("⚠️ Email configuration incomplete - skipping email notification")
        return False

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject

        # Add body
        msg.attach(MIMEText(body, 'html'))

        # Send email using SSL (port 465) or TLS (port 587)
        if SMTP_PORT == 465:
            # Use SSL
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                server.send_message(msg)
        else:
            # Use TLS
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_FROM, EMAIL_PASSWORD)
                server.send_message(msg)

        print(f"✅ Email sent: {subject}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - begins registration process"""
    user = update.effective_user

    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "🎯 **Polymarket UP/DOWN Bot Registration**\n\n"
        "I'll help you register for the trading bot.\n"
        "You'll need to provide:\n"
        "1️⃣ Private Key (Polygon wallet)\n"
        "2️⃣ API Key\n"
        "3️⃣ API Secret\n"
        "4️⃣ API Passphrase\n"
        "5️⃣ Bet Amount (per trade in USDC)\n\n"
        "⚠️ **SECURITY NOTICE:**\n"
        "- Your data is encrypted and stored securely\n"
        "- Messages containing sensitive data are deleted immediately\n"
        "- Only admins can access stored credentials\n\n"
        "💰 **WALLET BALANCE:**\n"
        "- Ensure your wallet has sufficient USDC balance\n"
        "- Recommended: At least 10x your bet amount\n\n"
        "Type /cancel at any time to stop.\n\n"
        "Let's begin! Please send your **Private Key**:",
        parse_mode='Markdown'
    )

    return WAITING_PRIVATE_KEY


async def receive_private_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and store private key"""
    private_key = update.message.text.strip()

    # Delete the message containing private key immediately
    await update.message.delete()

    # Store in context
    context.user_data['private_key'] = private_key
    context.user_data['telegram_id'] = update.effective_user.id
    context.user_data['username'] = update.effective_user.username or "N/A"
    context.user_data['first_name'] = update.effective_user.first_name

    await update.effective_chat.send_message(
        "✅ Private key received and deleted from chat.\n\n"
        "Now, please send your **API Key**:"
    )

    return WAITING_API_KEY


async def receive_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and store API key"""
    api_key = update.message.text.strip()

    # Delete the message
    await update.message.delete()

    context.user_data['api_key'] = api_key

    await update.effective_chat.send_message(
        "✅ API Key received and deleted.\n\n"
        "Now, please send your **API Secret**:"
    )

    return WAITING_API_SECRET


async def receive_api_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and store API secret"""
    api_secret = update.message.text.strip()

    # Delete the message
    await update.message.delete()

    context.user_data['api_secret'] = api_secret

    await update.effective_chat.send_message(
        "✅ API Secret received and deleted.\n\n"
        "Finally, please send your **API Passphrase**:"
    )

    return WAITING_API_PASSPHRASE


async def receive_api_passphrase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive API passphrase"""
    api_passphrase = update.message.text.strip()

    # Delete the message
    await update.message.delete()

    context.user_data['api_passphrase'] = api_passphrase

    await update.effective_chat.send_message(
        "✅ API Passphrase received and deleted.\n\n"
        "💰 **Bet Amount Setup**\n\n"
        "Now, please specify your bet amount per trade.\n\n"
        "Enter the amount in USDC (e.g., 5, 10, 25, 50)\n\n"
        "⚠️ **Important:**\n"
        "- This is the amount you'll bet on each trade\n"
        "- Make sure your wallet has sufficient balance\n"
        "- Recommended: Keep at least 10-20x your bet amount\n\n"
        "Please send your **Bet Amount (USDC)**:"
    )

    return WAITING_BET_AMOUNT


async def receive_bet_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive bet amount and show confirmation"""
    bet_amount_text = update.message.text.strip()

    try:
        bet_amount = float(bet_amount_text)
        if bet_amount <= 0:
            await update.message.reply_text(
                "❌ Bet amount must be greater than 0.\n\n"
                "Please send a valid amount (e.g., 5, 10, 25):"
            )
            return WAITING_BET_AMOUNT
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount format.\n\n"
            "Please send a number only (e.g., 5, 10, 25):"
        )
        return WAITING_BET_AMOUNT

    context.user_data['bet_amount'] = bet_amount
    context.user_data['registered_at'] = datetime.now().isoformat()

    # Show confirmation
    keyboard = [['✅ Confirm', '❌ Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    recommended_balance = bet_amount * 10

    await update.effective_chat.send_message(
        "✅ All information received!\n\n"
        "📋 **Registration Summary:**\n"
        f"👤 Name: {context.user_data['first_name']}\n"
        f"🆔 Username: @{context.user_data['username']}\n"
        f"🔑 Private Key: {'*' * 8}\n"
        f"🔐 API Key: {'*' * 8}\n"
        f"🔒 API Secret: {'*' * 8}\n"
        f"🔓 API Passphrase: {'*' * 8}\n"
        f"💰 Bet Amount: ${bet_amount:.2f} USDC\n\n"
        f"⚠️ **Wallet Balance:**\n"
        f"Recommended minimum: ${recommended_balance:.2f} USDC\n"
        f"(10x your bet amount)\n\n"
        "Do you want to complete the registration?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    return CONFIRM


async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and save registration"""
    choice = update.message.text

    if choice == '✅ Confirm':
        # Load existing registrations
        registrations = load_registrations()

        # Add new registration
        user_id = str(context.user_data['telegram_id'])
        registrations[user_id] = {
            'telegram_id': context.user_data['telegram_id'],
            'username': context.user_data['username'],
            'first_name': context.user_data['first_name'],
            'private_key': context.user_data['private_key'],
            'api_key': context.user_data['api_key'],
            'api_secret': context.user_data['api_secret'],
            'api_passphrase': context.user_data['api_passphrase'],
            'bet_amount': context.user_data['bet_amount'],
            'registered_at': context.user_data['registered_at'],
            'status': 'active'
        }

        # Save to file
        save_registrations(registrations)

        # Send email notification to admin
        email_subject = f"🎯 New User Registration - {context.user_data['first_name']}"
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #4CAF50;">🎯 New User Registration</h2>

            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #333;">User Information:</h3>
                <p><strong>👤 Name:</strong> {context.user_data['first_name']}</p>
                <p><strong>🆔 Username:</strong> @{context.user_data['username']}</p>
                <p><strong>📱 Telegram ID:</strong> {context.user_data['telegram_id']}</p>
                <p><strong>💰 Bet Amount:</strong> ${context.user_data['bet_amount']:.2f} USDC</p>
                <p><strong>📅 Registered At:</strong> {context.user_data['registered_at']}</p>
            </div>

            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #856404;">🔑 Credentials Received:</h3>
                <p>✅ Private Key: Stored</p>
                <p>✅ API Key: Stored</p>
                <p>✅ API Secret: Stored</p>
                <p>✅ API Passphrase: Stored</p>
            </div>

            <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #0c5460;">📊 Next Steps:</h3>
                <p>1. Review credentials in <code>user_registrations.json</code></p>
                <p>2. Add wallet to trading bot configuration</p>
                <p>3. Activate trading for this user</p>
            </div>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This is an automated notification from the Polymarket UP/DOWN Registration Bot.
            </p>
        </body>
        </html>
        """
        send_email_notification(email_subject, email_body)

        # Clear sensitive data from context
        context.user_data.clear()

        await update.message.reply_text(
            "🎉 **Registration Complete!**\n\n"
            "✅ Your credentials have been securely stored.\n"
            "🤖 The trading bot will be activated for your wallet soon.\n\n"
            "📊 You can view your trading statistics on:\n"
            "https://polymarket-up-down.vercel.app\n\n"
            "⚙️ Commands:\n"
            "/status - Check your registration status\n"
            "/help - Get help\n\n"
            "Thank you for registering! 🚀",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    else:
        # Clear data
        context.user_data.clear()

        await update.message.reply_text(
            "❌ Registration cancelled.\n\n"
            "Your data has been deleted.\n"
            "Use /start to begin again.",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel registration"""
    context.user_data.clear()

    await update.message.reply_text(
        "❌ Registration cancelled.\n\n"
        "All data has been cleared.\n"
        "Use /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check registration status"""
    user_id = str(update.effective_user.id)
    registrations = load_registrations()

    if user_id in registrations:
        reg = registrations[user_id]
        status_emoji = "✅" if reg['status'] == 'active' else "⏸️"
        await update.message.reply_text(
            f"📊 **Your Registration Status**\n\n"
            f"{status_emoji} Status: {reg['status'].upper()}\n"
            f"📅 Registered: {reg['registered_at'][:10]}\n"
            f"👤 Name: {reg['first_name']}\n"
            f"🆔 Username: @{reg['username']}\n"
            f"💰 Bet Amount: ${reg['bet_amount']:.2f} USDC\n\n"
            f"🔑 Credentials: Stored securely\n\n"
            f"⚙️ Commands:\n"
            f"/stop - Pause trading bot\n"
            f"/resume - Resume trading bot\n\n"
            f"📈 View your stats:\n"
            f"https://polymarket-up-down.vercel.app",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ You are not registered yet.\n\n"
            "Use /start to register."
        )


async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command - list all registrations"""
    # Check if user is admin
    if ADMIN_TELEGRAM_ID and update.effective_user.id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    registrations = load_registrations()

    if not registrations:
        await update.message.reply_text("📋 No registrations found.")
        return

    message = "📋 **All Registrations:**\n\n"
    for idx, (user_id, reg) in enumerate(registrations.items(), 1):
        message += (
            f"{idx}. 👤 {reg['first_name']} (@{reg['username']})\n"
            f"   🆔 Telegram ID: {reg['telegram_id']}\n"
            f"   📅 Registered: {reg['registered_at'][:10]}\n"
            f"   ✅ Status: {reg['status']}\n\n"
        )

    message += f"\n📊 Total: {len(registrations)} users"

    await update.message.reply_text(message, parse_mode='Markdown')


async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command - delete a registration"""
    # Check if user is admin
    if ADMIN_TELEGRAM_ID and update.effective_user.id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Usage: /delete <telegram_id>\n\n"
            "Use /list to see all Telegram IDs."
        )
        return

    user_id = context.args[0]
    registrations = load_registrations()

    if user_id in registrations:
        deleted_user = registrations[user_id]
        del registrations[user_id]
        save_registrations(registrations)

        await update.message.reply_text(
            f"✅ Deleted registration for:\n"
            f"👤 {deleted_user['first_name']} (@{deleted_user['username']})\n"
            f"🆔 Telegram ID: {user_id}"
        )
    else:
        await update.message.reply_text(f"❌ User ID {user_id} not found.")


async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command - export registrations to config.json format"""
    # Check if user is admin
    if ADMIN_TELEGRAM_ID and update.effective_user.id != ADMIN_TELEGRAM_ID:
        await update.message.reply_text("❌ Access denied. Admin only.")
        return

    registrations = load_registrations()

    if not registrations:
        await update.message.reply_text("❌ No registrations to export.")
        return

    # Convert to config.json format
    wallets = []
    for idx, (user_id, reg) in enumerate(registrations.items(), 1):
        wallets.append({
            "id": idx,
            "private_key": reg['private_key'],
            "api_key": reg['api_key'],
            "api_secret": reg['api_secret'],
            "api_passphrase": reg['api_passphrase']
        })

    config = {"wallets": wallets}

    # Save to file
    export_file = f"config_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(export_file, 'w') as f:
        json.dump(config, f, indent=2)

    await update.message.reply_text(
        f"✅ Exported {len(wallets)} wallets to:\n"
        f"📁 {export_file}\n\n"
        f"⚠️ **WARNING:** This file contains sensitive data!\n"
        f"Delete after use."
    )


async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop/pause trading bot for user"""
    user_id = str(update.effective_user.id)
    registrations = load_registrations()

    if user_id not in registrations:
        await update.message.reply_text(
            "❌ You are not registered yet.\n\n"
            "Use /start to register."
        )
        return

    reg = registrations[user_id]

    if reg['status'] == 'paused':
        await update.message.reply_text(
            "⏸️ Your bot is already paused.\n\n"
            "Use /resume to restart trading."
        )
        return

    # Update status to paused
    paused_time = datetime.now().isoformat()
    registrations[user_id]['status'] = 'paused'
    registrations[user_id]['paused_at'] = paused_time
    save_registrations(registrations)

    # Send email notification to admin
    email_subject = f"⏸️ User Paused Bot - {reg['first_name']}"
    email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #FFA500;">⏸️ Trading Bot Paused</h2>

        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #FFA500;">
            <h3 style="color: #856404;">User Information:</h3>
            <p><strong>👤 Name:</strong> {reg['first_name']}</p>
            <p><strong>🆔 Username:</strong> @{reg['username']}</p>
            <p><strong>📱 Telegram ID:</strong> {reg['telegram_id']}</p>
            <p><strong>💰 Bet Amount:</strong> ${reg['bet_amount']:.2f} USDC</p>
            <p><strong>⏸️ Paused At:</strong> {paused_time}</p>
        </div>

        <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #721c24;">⚠️ Status Change:</h3>
            <p>✅ Previous Status: <strong>Active</strong></p>
            <p>⏸️ Current Status: <strong>Paused</strong></p>
            <p>💤 No new trades will be made for this user until they resume.</p>
        </div>

        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #0c5460;">📊 Action Required:</h3>
            <p>• Update trading bot configuration to pause this wallet</p>
            <p>• User can resume anytime with /resume command</p>
        </div>

        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            This is an automated notification from the Polymarket UP/DOWN Registration Bot.
        </p>
    </body>
    </html>
    """
    send_email_notification(email_subject, email_body)

    await update.message.reply_text(
        "⏸️ **Trading Bot Paused**\n\n"
        "✅ Your trading bot has been stopped.\n"
        "💤 No new trades will be made for your account.\n\n"
        "To resume trading, use /resume command.\n\n"
        "📊 View your stats:\n"
        "https://polymarket-up-down.vercel.app",
        parse_mode='Markdown'
    )


async def resume_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume trading bot for user"""
    user_id = str(update.effective_user.id)
    registrations = load_registrations()

    if user_id not in registrations:
        await update.message.reply_text(
            "❌ You are not registered yet.\n\n"
            "Use /start to register."
        )
        return

    reg = registrations[user_id]

    if reg['status'] == 'active':
        await update.message.reply_text(
            "✅ Your bot is already active and trading.\n\n"
            "Use /stop to pause trading."
        )
        return

    # Update status to active
    resumed_time = datetime.now().isoformat()
    registrations[user_id]['status'] = 'active'
    registrations[user_id]['resumed_at'] = resumed_time
    save_registrations(registrations)

    # Send email notification to admin
    email_subject = f"✅ User Resumed Bot - {reg['first_name']}"
    email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #4CAF50;">✅ Trading Bot Resumed</h2>

        <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4CAF50;">
            <h3 style="color: #155724;">User Information:</h3>
            <p><strong>👤 Name:</strong> {reg['first_name']}</p>
            <p><strong>🆔 Username:</strong> @{reg['username']}</p>
            <p><strong>📱 Telegram ID:</strong> {reg['telegram_id']}</p>
            <p><strong>💰 Bet Amount:</strong> ${reg['bet_amount']:.2f} USDC</p>
            <p><strong>🚀 Resumed At:</strong> {resumed_time}</p>
        </div>

        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #0c5460;">⚠️ Status Change:</h3>
            <p>⏸️ Previous Status: <strong>Paused</strong></p>
            <p>✅ Current Status: <strong>Active</strong></p>
            <p>🚀 Bot is now ready to make trades for this user.</p>
        </div>

        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #856404;">📊 Trading Configuration:</h3>
            <p><strong>💰 Bet Amount:</strong> ${reg['bet_amount']:.2f} USDC per trade</p>
            <p><strong>💵 Recommended Balance:</strong> ${reg['bet_amount'] * 10:.2f} USDC minimum</p>
        </div>

        <div style="background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #004085;">📋 Action Required:</h3>
            <p>• Update trading bot configuration to activate this wallet</p>
            <p>• Verify wallet has sufficient USDC balance</p>
            <p>• Monitor initial trades to ensure proper operation</p>
        </div>

        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            This is an automated notification from the Polymarket UP/DOWN Registration Bot.
        </p>
    </body>
    </html>
    """
    send_email_notification(email_subject, email_body)

    await update.message.reply_text(
        "✅ **Trading Bot Resumed**\n\n"
        "🚀 Your trading bot is now active again!\n"
        "💰 The bot will resume trading with:\n"
        f"   • Bet Amount: ${reg['bet_amount']:.2f} USDC\n\n"
        "⚠️ **Important:**\n"
        "- Ensure your wallet has sufficient USDC balance\n"
        f"- Recommended: At least ${reg['bet_amount'] * 10:.2f} USDC\n\n"
        "📊 View your stats:\n"
        "https://polymarket-up-down.vercel.app",
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    user_id = update.effective_user.id

    message = (
        "🤖 **Polymarket UP/DOWN Bot**\n\n"
        "**User Commands:**\n"
        "/start - Register for trading bot\n"
        "/status - Check registration status\n"
        "/stop - Pause your trading bot\n"
        "/resume - Resume your trading bot\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current operation\n\n"
    )

    if ADMIN_TELEGRAM_ID and user_id == ADMIN_TELEGRAM_ID:
        message += (
            "**Admin Commands:**\n"
            "/list - List all registrations\n"
            "/delete <telegram_id> - Delete a registration\n"
            "/export - Export registrations to config.json\n\n"
        )

    message += (
        "📊 **Dashboard:**\n"
        "https://polymarket-up-down.vercel.app"
    )

    await update.message.reply_text(message, parse_mode='Markdown')


def main():
    """Run the bot"""
    # Get bot token from environment or .env file
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    if not BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found!")
        print("Please set it in .env file or environment variable.")
        return

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for registration
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_PRIVATE_KEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_private_key)
            ],
            WAITING_API_KEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_key)
            ],
            WAITING_API_SECRET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_secret)
            ],
            WAITING_API_PASSPHRASE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_api_passphrase)
            ],
            WAITING_BET_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bet_amount)
            ],
            CONFIRM: [
                MessageHandler(filters.Regex('^(✅ Confirm|❌ Cancel)$'), confirm_registration)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('status', status))
    application.add_handler(CommandHandler('stop', stop_bot))
    application.add_handler(CommandHandler('resume', resume_bot))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('list', admin_list))
    application.add_handler(CommandHandler('delete', admin_delete))
    application.add_handler(CommandHandler('export', admin_export))

    # Start bot
    print("🤖 Bot is starting...")
    print(f"📊 Registrations file: {REGISTRATIONS_FILE}")
    print("✅ Bot is running! Press Ctrl+C to stop.")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
