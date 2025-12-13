from http.server import BaseHTTPRequestHandler
import json
import time
from datetime import datetime
from polymarket_apis.clients import PolymarketDataClient

# Hardcoded wallet addresses (from config.json)
WALLET_ADDRESSES = [
    {'number': 1, 'funder': '0x707a2F7bB884E45bF5AA26f0dC44aA3aE309D4ff'},
    {'number': 2, 'funder': '0xdA31710a25Ef1544F31bC014a32b8c6b107b74D0'},
    {'number': 3, 'funder': '0x8eF6726670e61E88146D89e49B03c9b00b4C885F'},
    {'number': 4, 'funder': '0x2E7F3B55cb67B14a80f2c61D23bDc7C1e6b8F1dA'},
    {'number': 5, 'funder': '0x9A3b5C8D4F2E1B7a6C8d5E3F1A2B4C6D8E9F0A1B'},
    {'number': 6, 'funder': '0x1C2D3E4F5A6B7C8D9E0F1A2B3C4D5E6F7A8B9C0D'},
    {'number': 7, 'funder': '0x5F8e3c2A1b9D6E4f7C0A2B3D4E5F6A7B8C9D0E1F'},
    {'number': 8, 'funder': '0x3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B2C'},
    {'number': 9, 'funder': '0x7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E4F5A6B'},
    {'number': 10, 'funder': '0x0E1F2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F'},
    {'number': 11, 'funder': '0x4D5E6F7A8B9C0D1E2F3A4B5C6D7E8F9A0B1C2D3E'},
    {'number': 12, 'funder': '0x6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D'}
]

def fetch_wallet_stats(funder_address):
    """Fetch wallet statistics using polymarket-apis"""
    try:
        data_client = PolymarketDataClient()

        # Get user metrics (includes P&L)
        user_metric = data_client.get_user_metric(funder_address)
        total_pnl = user_metric.amount

        # Get total markets traded
        markets_traded = data_client.get_total_markets_traded(funder_address)

        # Get total volume from leaderboard
        leaderboard_data = data_client.get_leaderboard_user_rank(funder_address)
        total_volume = leaderboard_data.amount

        status = 'Active' if markets_traded > 0 else 'Inactive'

        return {
            'funder': funder_address,
            'volume': total_volume,
            'pnl': total_pnl,
            'trades': markets_traded,
            'status': status
        }

    except Exception as e:
        return {
            'funder': funder_address,
            'volume': 0,
            'pnl': 0,
            'trades': 0,
            'status': 'Error'
        }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        wallet_stats = []
        total_volume = 0
        total_pnl = 0
        total_trades = 0
        active_count = 0

        for wallet in WALLET_ADDRESSES:
            stats = fetch_wallet_stats(wallet['funder'])
            stats['number'] = wallet['number']

            wallet_stats.append(stats)

            # Calculate totals
            total_volume += stats['volume']
            total_pnl += stats['pnl']
            total_trades += stats['trades']
            if stats['status'] == 'Active':
                active_count += 1

            # Small delay to avoid rate limits
            time.sleep(0.3)

        response_data = {
            'wallets': wallet_stats,
            'summary': {
                'total_volume': total_volume,
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'active_wallets': active_count
            },
            'timestamp': datetime.now().isoformat()
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode())
