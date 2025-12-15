# Telegram Registration Bot

## Overview
This bot allows users to register their private keys and API credentials for the Polymarket UP/DOWN trading bot.

## Features
- 🔐 Secure credential collection
- 🗑️ Auto-delete sensitive messages
- 💾 Local data storage
- 👨‍💼 Admin management commands
- 📊 Export to config.json format

## Setup Instructions

### 1. Create a Telegram Bot
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the bot token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Telegram User ID
1. Search for `@userinfobot` on Telegram
2. Start a chat with it
3. It will send you your User ID (a number like: `123456789`)

### 3. Install Dependencies
```bash
cd /Users/mac/Documents/claude/updownnewclaim/dashboard
pip3 install python-telegram-bot python-dotenv
```

### 4. Configure Environment Variables
Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and add:
```
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_TELEGRAM_ID=your_telegram_user_id_here

# Email Notification Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_FROM=your_email@gmail.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_TO=admin_email@gmail.com
```

**Email Notifications Setup (Gmail):**
1. Go to Google Account settings: https://myaccount.google.com/
2. Enable 2-Step Verification
3. Go to App Passwords: https://myaccount.google.com/apppasswords
4. Create a new App Password for "Mail"
5. Copy the 16-character password
6. Use it as `EMAIL_PASSWORD` in `.env`

**Note:** Email notifications are optional. If not configured, the bot will still work but won't send email alerts.

### 5. Run the Bot Locally
```bash
cd /Users/mac/Documents/claude/updownnewclaim/dashboard
python3 registration_bot.py
```

## User Commands

### `/start`
Begin the registration process. The bot will ask for:
1. Private Key (Polygon wallet)
2. API Key
3. API Secret
4. API Passphrase
5. Bet Amount (per trade in USDC)

**Security Note:** All messages containing sensitive data are deleted immediately after being received.

### `/status`
Check your registration status and view your credentials (masked), bet amount, and trading status.

### `/stop`
Pause your trading bot. The bot will stop making new trades for your account until you resume it.

**Example:**
```
/stop
```

Response: "⏸️ Trading Bot Paused - No new trades will be made for your account."

### `/resume`
Resume your trading bot. The bot will start trading again with your configured bet amount.

**Example:**
```
/resume
```

Response: "✅ Trading Bot Resumed - Your bot is now active again!"

### `/help`
Display help message with all available commands.

### `/cancel`
Cancel the current registration process and clear all data.

## Admin Commands

### `/list`
List all registered users with their:
- Name and username
- Telegram ID
- Registration date
- Status

### `/delete <telegram_id>`
Delete a specific user's registration.

Example:
```
/delete 123456789
```

### `/export`
Export all registrations to `config.json` format for the trading bot.

Creates a file like: `config_export_20231215_143025.json`

**⚠️ WARNING:** This file contains private keys and API credentials. Delete after use!

## Security Features

1. **Auto-Delete Messages**: All messages containing private keys, API keys, secrets, and passphrases are automatically deleted from the chat immediately after being received.

2. **Local Storage**: Data is stored locally in `user_registrations.json` (gitignored).

3. **Admin-Only Access**: Only the configured admin can view, export, or delete registrations.

4. **Encrypted Communication**: All Telegram communications are encrypted by default.

5. **Email Notifications**: Admin receives email alerts when new users register with complete user information.

## Data Storage

Registrations are stored in `user_registrations.json`:

```json
{
  "123456789": {
    "telegram_id": 123456789,
    "username": "john_doe",
    "first_name": "John",
    "private_key": "0x...",
    "api_key": "...",
    "api_secret": "...",
    "api_passphrase": "...",
    "registered_at": "2023-12-15T14:30:25",
    "status": "active"
  }
}
```

**⚠️ IMPORTANT:** This file contains sensitive data and is gitignored. Back it up securely!

## Testing Locally

1. Start the bot:
```bash
python3 registration_bot.py
```

2. Open Telegram and search for your bot (the name you gave it with @BotFather)

3. Send `/start` to begin registration

4. Follow the prompts to enter your credentials

5. Test admin commands:
   - `/list` - See all registrations
   - `/export` - Export to config.json

## Deployment (Production)

After testing locally, you can deploy to:
- **Railway**: For 24/7 operation
- **Heroku**: Free tier available
- **VPS**: Any Linux server

### Railway Deployment
```bash
# Install Railway CLI
npm install -g railway

# Login
railway login

# Initialize project
railway init

# Add environment variables
railway variables set TELEGRAM_BOT_TOKEN=your_token
railway variables set ADMIN_TELEGRAM_ID=your_id

# Deploy
railway up
```

## File Structure

```
dashboard/
├── registration_bot.py          # Main bot code
├── user_registrations.json      # User data (gitignored)
├── .env                         # Environment variables (gitignored)
├── .env.example                 # Example env file
└── README_TELEGRAM_BOT.md       # This file
```

## Troubleshooting

### Bot doesn't respond
- Check if bot is running: `ps aux | grep registration_bot`
- Check bot token is correct in `.env`
- Check internet connection

### Messages not deleting
- Ensure bot has admin rights (not required for private chats)
- Check bot has `delete_messages` permission

### Can't export registrations
- Check you're the admin (ADMIN_TELEGRAM_ID matches your ID)
- Check write permissions in directory

## Support

For issues or questions:
- Email: polymarket.up.down@gmail.com
- Dashboard: https://dashboard-kirsghnhw-jirasssims-projects.vercel.app
