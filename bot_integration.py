#!/usr/bin/env python3
"""
Dashboard Integration for Polymarket Trading Bot
Connects the main trading bot with the dashboard API
"""

import json
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional
import threading
from decimal import Decimal

logger = logging.getLogger(__name__)

class DashboardIntegration:
    """
    Integration class to connect trading bot with dashboard
    Reports trades, statistics, and wallet status to dashboard API
    """

    def __init__(self, api_url: str = "http://localhost:5000/api", user_id: str = "default"):
        """
        Initialize dashboard integration

        Args:
            api_url: Dashboard API URL
            user_id: User identifier for this bot instance
        """
        self.api_url = api_url
        self.user_id = user_id
        self.session = None
        self._running = False
        self._report_thread = None
        self._trade_queue = asyncio.Queue()

    async def start(self):
        """Start the integration service"""
        self._running = True
        self.session = aiohttp.ClientSession()

        # Start background tasks
        asyncio.create_task(self._trade_reporter())
        asyncio.create_task(self._stats_reporter())

        logger.info(f"Dashboard integration started for user {self.user_id}")

    async def stop(self):
        """Stop the integration service"""
        self._running = False
        if self.session:
            await self.session.close()
        logger.info("Dashboard integration stopped")

    async def report_trade(self, trade_data: Dict):
        """
        Report a trade to the dashboard

        Args:
            trade_data: Trade information including:
                - wallet_number: Wallet number (1-12)
                - market_id: Market identifier
                - market_question: Market question text
                - side: UP or DOWN
                - amount: Trade amount in USDC
                - price: Execution price
                - status: pending, filled, cancelled
                - tx_hash: Transaction hash
        """
        try:
            # Add user_id to trade data
            trade_data['user_id'] = self.user_id

            # Convert Decimal to float for JSON serialization
            for key in ['amount', 'price']:
                if key in trade_data and isinstance(trade_data[key], Decimal):
                    trade_data[key] = float(trade_data[key])

            # Queue trade for reporting
            await self._trade_queue.put(trade_data)

        except Exception as e:
            logger.error(f"Error queueing trade for dashboard: {e}")

    async def _trade_reporter(self):
        """Background task to report trades to dashboard"""
        while self._running:
            try:
                # Get trade from queue (with timeout to allow checking _running)
                trade_data = await asyncio.wait_for(
                    self._trade_queue.get(),
                    timeout=1.0
                )

                # Send to dashboard API
                async with self.session.post(
                    f"{self.api_url}/trades",
                    json=trade_data
                ) as response:
                    if response.status == 200:
                        logger.debug(f"Trade reported to dashboard: {trade_data['market_question'][:50]}")
                    else:
                        logger.error(f"Failed to report trade: {response.status}")

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error reporting trade: {e}")

    async def update_wallet_status(self, wallet_number: int, status: Dict):
        """
        Update wallet status on dashboard

        Args:
            wallet_number: Wallet number (1-12)
            status: Status information including:
                - is_active: Whether wallet is active
                - balance: Current USDC balance
                - position_count: Number of open positions
                - daily_volume: Today's volume
                - pnl: Today's P&L
        """
        try:
            endpoint = f"{self.api_url}/wallets/{wallet_number}/status"
            status['user_id'] = self.user_id

            async with self.session.post(endpoint, json=status) as response:
                if response.status == 200:
                    logger.debug(f"Wallet {wallet_number} status updated")
                else:
                    logger.error(f"Failed to update wallet status: {response.status}")

        except Exception as e:
            logger.error(f"Error updating wallet status: {e}")

    async def _stats_reporter(self):
        """Background task to periodically report statistics"""
        while self._running:
            try:
                # Report stats every 60 seconds
                await asyncio.sleep(60)

                # Gather current statistics
                stats = await self._gather_statistics()

                # Send to dashboard
                async with self.session.post(
                    f"{self.api_url}/stats/update",
                    json={'user_id': self.user_id, 'stats': stats}
                ) as response:
                    if response.status == 200:
                        logger.debug("Statistics updated on dashboard")

            except Exception as e:
                logger.error(f"Error reporting statistics: {e}")

    async def _gather_statistics(self) -> Dict:
        """Gather current bot statistics"""
        # This would integrate with the main bot to get real statistics
        # For now, return placeholder data
        return {
            'timestamp': datetime.now().isoformat(),
            'total_volume_24h': 0,
            'total_trades_24h': 0,
            'active_positions': 0,
            'win_rate': 0,
            'profit_loss_24h': 0
        }


class TradingBotDashboardAdapter:
    """
    Adapter to integrate existing trading bot with dashboard
    Wraps the main bot methods to report to dashboard
    """

    def __init__(self, bot_instance, dashboard_integration: DashboardIntegration):
        """
        Initialize adapter

        Args:
            bot_instance: The main CryptoUpDownBot instance
            dashboard_integration: Dashboard integration instance
        """
        self.bot = bot_instance
        self.dashboard = dashboard_integration

        # Wrap bot methods to report to dashboard
        self._wrap_methods()

    def _wrap_methods(self):
        """Wrap bot methods to report activities to dashboard"""

        # Save original methods
        original_buy_wallet_pair = self.bot.buy_wallet_pair
        original_buy_random_side = self.bot.buy_random_side

        # Create wrapped version of buy_wallet_pair
        async def wrapped_buy_wallet_pair(pair_idx: int, market: Dict) -> Optional[Dict]:
            # Call original method
            result = original_buy_wallet_pair(pair_idx, market)

            # Report to dashboard if successful
            if result:
                pair = self.bot.wallet_pairs[pair_idx]

                # Report trade for wallet 1
                if result.get('order_id1'):
                    await self.dashboard.report_trade({
                        'wallet_id': pair[0] + 1,
                        'wallet_number': pair[0] + 1,
                        'market_id': market['market_id'],
                        'market_question': market['question'],
                        'side': 'UP',
                        'amount': result.get('size', 5) * 0.49,
                        'price': 0.49,
                        'status': 'pending',
                        'tx_hash': result.get('order_id1')
                    })

                # Report trade for wallet 2
                if result.get('order_id2'):
                    await self.dashboard.report_trade({
                        'wallet_id': pair[1] + 1,
                        'wallet_number': pair[1] + 1,
                        'market_id': market['market_id'],
                        'market_question': market['question'],
                        'side': 'DOWN',
                        'amount': result.get('size', 5) * 0.49,
                        'price': 0.49,
                        'status': 'pending',
                        'tx_hash': result.get('order_id2')
                    })

            return result

        # Create wrapped version of buy_random_side
        async def wrapped_buy_random_side(market: Dict) -> Optional[Dict]:
            # Call original method
            result = original_buy_random_side(market)

            # Report to dashboard if successful
            if result:
                await self.dashboard.report_trade({
                    'wallet_id': 1,  # Default to wallet 1 for single wallet trades
                    'wallet_number': 1,
                    'market_id': market['market_id'],
                    'market_question': market['question'],
                    'side': result['side'],
                    'amount': result.get('size', 5) * result.get('buy_price', 0.5),
                    'price': result.get('buy_price', 0.5),
                    'status': result.get('status', 'pending'),
                    'tx_hash': result.get('buy_order_id')
                })

            return result

        # Replace methods
        self.bot.buy_wallet_pair = wrapped_buy_wallet_pair
        self.bot.buy_random_side = wrapped_buy_random_side

    async def sync_wallets(self):
        """Sync wallet information with dashboard"""
        for idx, pair in enumerate(self.bot.wallet_pairs):
            pair_number = idx + 1

            # Update wallet 1 of pair
            wallet1_idx = pair[0]
            wallet1_address = self.bot.wallet_addresses[wallet1_idx]
            await self.dashboard.update_wallet_status(
                wallet1_idx + 1,
                {
                    'address': wallet1_address,
                    'is_active': not self.bot.is_pair_disabled(idx),
                    'position': 'UP',
                    'order_amount': self.bot.get_pair_amount(idx)
                }
            )

            # Update wallet 2 of pair
            wallet2_idx = pair[1]
            wallet2_address = self.bot.wallet_addresses[wallet2_idx]
            await self.dashboard.update_wallet_status(
                wallet2_idx + 1,
                {
                    'address': wallet2_address,
                    'is_active': not self.bot.is_pair_disabled(idx),
                    'position': 'DOWN',
                    'order_amount': self.bot.get_pair_amount(idx)
                }
            )


def integrate_with_dashboard(bot_instance, api_url: str = "http://localhost:5000/api", user_id: str = None):
    """
    Integrate existing bot with dashboard

    Args:
        bot_instance: The CryptoUpDownBot instance
        api_url: Dashboard API URL
        user_id: User identifier (will use wallet address if not provided)

    Returns:
        DashboardIntegration instance
    """
    # Generate user_id from wallet address if not provided
    if not user_id:
        user_id = f"USER_{bot_instance.wallet_addresses[0][:10]}"

    # Create integration
    dashboard = DashboardIntegration(api_url, user_id)

    # Create adapter
    adapter = TradingBotDashboardAdapter(bot_instance, dashboard)

    # Start integration in background
    async def start_integration():
        await dashboard.start()
        await adapter.sync_wallets()

    # Run in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_integration())

    # Start background thread for async operations
    def run_async_loop():
        loop.run_forever()

    thread = threading.Thread(target=run_async_loop, daemon=True)
    thread.start()

    logger.info(f"Dashboard integration active for user {user_id}")
    logger.info(f"View dashboard at: http://localhost/?user={user_id}")

    return dashboard


# Example usage in main bot
if __name__ == "__main__":
    # This would be added to your main bot file (updown_bot.py)

    # Import your bot
    from updown_bot import CryptoUpDownBot

    # Create bot instance
    bot = CryptoUpDownBot()

    # Integrate with dashboard
    dashboard = integrate_with_dashboard(bot)

    # Run bot as normal
    bot.run()