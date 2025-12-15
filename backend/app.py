#!/usr/bin/env python3
"""
Polymarket Trading Bot Dashboard - Backend API
FastAPI application for managing bot users and displaying statistics
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio
import aioredis
import sqlite3
import hashlib
import secrets
import os
from contextlib import asynccontextmanager

# Initialize FastAPI app
app = FastAPI(title="Polymarket Bot Dashboard API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Database initialization
def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('dashboard.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        telegram_user_id INTEGER,
        telegram_username TEXT,
        api_key_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP,
        is_active BOOLEAN DEFAULT 1,
        settings TEXT DEFAULT '{}'
    )
    ''')

    # Wallets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        wallet_number INTEGER NOT NULL,
        address TEXT NOT NULL,
        funder_address TEXT,
        position TEXT DEFAULT 'auto',
        order_amount REAL DEFAULT 5.0,
        max_daily_volume REAL DEFAULT 500.0,
        auto_claim_enabled BOOLEAN DEFAULT 1,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        UNIQUE(user_id, wallet_number)
    )
    ''')

    # Trades table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        wallet_id INTEGER NOT NULL,
        market_id TEXT,
        market_question TEXT,
        side TEXT,
        amount REAL,
        price REAL,
        status TEXT,
        tx_hash TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (wallet_id) REFERENCES wallets (id)
    )
    ''')

    # Statistics table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS statistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        date DATE NOT NULL,
        total_volume REAL DEFAULT 0,
        total_trades INTEGER DEFAULT 0,
        winning_trades INTEGER DEFAULT 0,
        profit_loss REAL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        UNIQUE(user_id, date)
    )
    ''')

    # Pending registrations (temporary storage for Telegram bot)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pending_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        telegram_user_id INTEGER,
        telegram_username TEXT,
        verification_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Pydantic models
class UserRegistration(BaseModel):
    user_id: str
    telegram_user_id: Optional[int]
    telegram_username: Optional[str]

class WalletSettings(BaseModel):
    tradingPair: str
    orderAmount: float
    maxDailyVolume: float
    autoClaimEnabled: bool

class Trade(BaseModel):
    user_id: str
    wallet_id: int
    market_id: str
    market_question: str
    side: str
    amount: float
    price: float
    status: str
    tx_hash: Optional[str]

# Database helper functions
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('dashboard.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_user_stats(user_id: str, conn=None) -> Dict:
    """Get user statistics"""
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False

    cursor = conn.cursor()

    # Get today's stats
    today = datetime.now().date()
    cursor.execute('''
        SELECT * FROM statistics
        WHERE user_id = ? AND date = ?
    ''', (user_id, today))

    stats = cursor.fetchone()

    if close_conn:
        conn.close()

    if stats:
        return dict(stats)
    else:
        return {
            'totalVolume': 0,
            'totalTrades': 0,
            'winRate': 0,
            'profitLoss': 0,
            'activeWallets': 0,
            'totalWallets': 12,
            'volumeChange': 0,
            'tradesPerHour': 0
        }

def get_user_wallets(user_id: str) -> List[Dict]:
    """Get user wallets"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT w.*,
               COUNT(t.id) as trades_count,
               SUM(CASE WHEN t.timestamp > datetime('now', '-1 day') THEN t.amount ELSE 0 END) as volume_24h,
               SUM(CASE WHEN t.status = 'filled' THEN t.amount * (t.price - 0.5) ELSE 0 END) as pnl
        FROM wallets w
        LEFT JOIN trades t ON w.id = t.wallet_id
        WHERE w.user_id = ?
        GROUP BY w.id
        ORDER BY w.wallet_number
    ''', (user_id,))

    wallets = []
    for row in cursor.fetchall():
        wallet = dict(row)
        wallet['status'] = 'active' if wallet['is_active'] else 'inactive'
        wallet['number'] = wallet['wallet_number']
        wallet['tradesCount'] = wallet['trades_count']
        wallet['volume24h'] = wallet['volume_24h'] or 0
        wallet['pnl'] = wallet['pnl'] or 0
        wallets.append(wallet)

    conn.close()
    return wallets

def get_recent_trades(user_id: str, limit: int = 20) -> List[Dict]:
    """Get recent trades"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT t.*, w.wallet_number
        FROM trades t
        JOIN wallets w ON t.wallet_id = w.id
        WHERE t.user_id = ?
        ORDER BY t.timestamp DESC
        LIMIT ?
    ''', (user_id, limit))

    trades = []
    for row in cursor.fetchall():
        trade = dict(row)
        trade['walletNumber'] = trade['wallet_number']
        trade['market'] = trade['market_question']
        trades.append(trade)

    conn.close()
    return trades

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Polymarket Trading Bot Dashboard API", "version": "1.0.0"}

@app.get("/api/stats")
async def get_stats(user_id: str = "default"):
    """Get dashboard statistics"""
    stats = get_user_stats(user_id)

    # Calculate additional metrics
    conn = get_db_connection()
    cursor = conn.cursor()

    # Active wallets count
    cursor.execute('''
        SELECT COUNT(*) as active_count
        FROM wallets
        WHERE user_id = ? AND is_active = 1
    ''', (user_id,))
    active_wallets = cursor.fetchone()['active_count']

    # Volume history (last 24 hours)
    cursor.execute('''
        SELECT
            strftime('%H', timestamp) as hour,
            SUM(amount) as volume
        FROM trades
        WHERE user_id = ? AND timestamp > datetime('now', '-1 day')
        GROUP BY hour
        ORDER BY hour
    ''', (user_id,))

    volume_history = [0] * 24
    for row in cursor.fetchall():
        hour = int(row['hour'])
        volume_history[hour] = row['volume']

    conn.close()

    stats.update({
        'activeWallets': active_wallets,
        'volumeHistory': volume_history
    })

    return stats

@app.get("/api/wallets")
async def get_wallets(user_id: str = "default"):
    """Get all wallets for a user"""
    wallets = get_user_wallets(user_id)
    return wallets

@app.get("/api/trades/recent")
async def get_trades(user_id: str = "default", limit: int = 20):
    """Get recent trades"""
    trades = get_recent_trades(user_id, limit)
    return trades

@app.post("/api/wallets/{wallet_id}/settings")
async def update_wallet_settings(wallet_id: int, settings: WalletSettings):
    """Update wallet settings"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE wallets
        SET position = ?,
            order_amount = ?,
            max_daily_volume = ?,
            auto_claim_enabled = ?
        WHERE id = ?
    ''', (
        settings.tradingPair,
        settings.orderAmount,
        settings.maxDailyVolume,
        settings.autoClaimEnabled,
        wallet_id
    ))

    conn.commit()
    conn.close()

    # Broadcast update to WebSocket clients
    await manager.broadcast(json.dumps({
        'type': 'wallet_update',
        'wallet_id': wallet_id,
        'settings': settings.dict()
    }))

    return {"status": "success"}

@app.get("/api/users/{user_id}/status")
async def check_user_status(user_id: str):
    """Check user registration status"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    conn.close()

    if user:
        return {"registered": True, "user": dict(user)}
    else:
        return {"registered": False}

@app.post("/api/trades")
async def add_trade(trade: Trade):
    """Add a new trade (called by bot)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO trades (user_id, wallet_id, market_id, market_question,
                           side, amount, price, status, tx_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        trade.user_id, trade.wallet_id, trade.market_id,
        trade.market_question, trade.side, trade.amount,
        trade.price, trade.status, trade.tx_hash
    ))

    trade_id = cursor.lastrowid
    conn.commit()

    # Update statistics
    cursor.execute('''
        INSERT OR REPLACE INTO statistics (user_id, date, total_volume, total_trades)
        VALUES (
            ?,
            date('now'),
            COALESCE((SELECT total_volume FROM statistics WHERE user_id = ? AND date = date('now')), 0) + ?,
            COALESCE((SELECT total_trades FROM statistics WHERE user_id = ? AND date = date('now')), 0) + 1
        )
    ''', (trade.user_id, trade.user_id, trade.amount, trade.user_id))

    conn.commit()
    conn.close()

    # Broadcast to WebSocket
    await manager.broadcast(json.dumps({
        'type': 'trade',
        'trade': trade.dict()
    }))

    return {"status": "success", "trade_id": trade_id}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Telegram Bot integration endpoints

@app.post("/api/telegram/register")
async def telegram_register(user_id: str, telegram_user_id: int, telegram_username: str):
    """Register user from Telegram bot"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create user
        cursor.execute('''
            INSERT INTO users (user_id, telegram_user_id, telegram_username, last_active)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, telegram_user_id, telegram_username))

        # Create default wallets (12 wallets, 6 pairs)
        for i in range(1, 13):
            cursor.execute('''
                INSERT INTO wallets (user_id, wallet_number, address, position)
                VALUES (?, ?, ?, ?)
            ''', (user_id, i, f"0x{'0'*40}", "auto"))

        conn.commit()
        conn.close()

        return {"status": "success", "message": "User registered successfully"}
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="User already exists")

@app.post("/api/telegram/update-credentials")
async def update_credentials(user_id: str, api_key_hash: str):
    """Update user credentials (hashed)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE users
        SET api_key_hash = ?, last_active = CURRENT_TIMESTAMP
        WHERE user_id = ?
    ''', (api_key_hash, user_id))

    conn.commit()
    conn.close()

    return {"status": "success"}

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)