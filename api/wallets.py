from http.server import BaseHTTPRequestHandler
import json
import time
from datetime import datetime
from polymarket_apis.clients import PolymarketDataClient

# Hardcoded wallet addresses (from config.json)
WALLET_ADDRESSES = [
    {'number': 1, 'funder': '0x707a2F7bB884E45bF5AA26f0dC44aA3aE309D4ff'},
    {'number': 2, 'funder': '0xdA31710a25Ef1544F31bC014a32b8c6b107b74D0'},
    {'number': 3, 'funder': '0x5ef82699d9ffd7a5a092cad77cd6b07dae52b33e'},
    {'number': 4, 'funder': '0x2ad5198d59f6088819a52aeffa11bddb62f495c1'},
    {'number': 5, 'funder': '0xdb9c2e152d90fc79f92da47b8b22e36e8480a8be'},
    {'number': 6, 'funder': '0x059ebc6734c0a0af9ddd72bf3213250c0a653f67'},
    {'number': 7, 'funder': '0x05B1822C0702a85ac7F603409AB0061F80fD06e6'},
    {'number': 8, 'funder': '0x1f6a48dfac186A4a841f86439D4660C900FD2b18'},
    {'number': 9, 'funder': '0x2bd58cffc23ce88efc7e6d20eb5802f57360c2fa'},
    {'number': 10, 'funder': '0x2631bf72fedf7ac3b20632c0d3223e4cd865cc94'},
    {'number': 11, 'funder': '0x935714939bb64cf43e460b76ebd93734ab200d8f'},
    {'number': 12, 'funder': '0x7883ee83b91ed33a905bcdcb9d6762b8f7f6df7d'}
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
