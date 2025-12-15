#!/usr/bin/env python3
"""
Real Trading Dashboard - Uses EOA addresses that actually trade
"""

import json
import requests
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS
from datetime import datetime
from decimal import Decimal

app = Flask(__name__)
CORS(app)

# Load BOTH funder and EOA addresses from config.json
def load_wallet_addresses():
    """Load both funder and EOA addresses from config.json"""
    with open('../config.json', 'r') as f:
        config = json.load(f)

    wallets = []

    # Map wallet configs to get BOTH addresses
    wallet_configs = [
        ('wallet', 1),
        ('wallet2', 2),
        ('wallet3', 3),
        ('wallet4', 4),
        ('wallet5', 5),
        ('wallet6', 6),
        ('wallet7', 7),
        ('wallet8', 8),
        ('wallet9', 9),
        ('wallet10', 10),
        ('wallet11', 11),
        ('wallet12', 12)
    ]

    for wallet_key, number in wallet_configs:
        if wallet_key in config:
            wallet_data = config[wallet_key]
            wallets.append({
                'number': number,
                'funder': wallet_data['funder'],  # Safe/Proxy wallet
                'address': wallet_data['address']  # EOA wallet (actual trading)
            })

    return wallets

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real Trading Dashboard - EOA Wallets</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .loading { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .fade-in { animation: fadeIn 0.5s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    </style>
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-4">
        <!-- Header -->
        <div class="bg-gradient-to-r from-blue-800 to-purple-800 rounded-lg p-6 mb-6">
            <h1 class="text-4xl font-bold mb-2">🎯 Real Trading Dashboard</h1>
            <p class="text-gray-300">Showing actual EOA trading wallets (not proxies)</p>
            <div class="mt-4">
                <button onclick="refreshData()" class="bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg text-lg font-semibold">
                    🔄 Refresh All Data
                </button>
                <span class="ml-4 text-sm text-gray-300">Last updated: <span id="lastUpdate">Never</span></span>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-gradient-to-br from-green-700 to-green-900 rounded-lg p-4">
                <div class="text-gray-300 text-sm mb-1">📊 Total Volume</div>
                <div id="totalVolume" class="text-3xl font-bold">Loading...</div>
            </div>
            <div class="bg-gradient-to-br from-blue-700 to-blue-900 rounded-lg p-4">
                <div class="text-gray-300 text-sm mb-1">💵 Total P&L</div>
                <div id="totalPnL" class="text-3xl font-bold">Loading...</div>
            </div>
            <div class="bg-gradient-to-br from-purple-700 to-purple-900 rounded-lg p-4">
                <div class="text-gray-300 text-sm mb-1">📈 Total Trades</div>
                <div id="totalTrades" class="text-3xl font-bold">0</div>
            </div>
            <div class="bg-gradient-to-br from-yellow-700 to-yellow-900 rounded-lg p-4">
                <div class="text-gray-300 text-sm mb-1">✅ Active Wallets</div>
                <div id="activeWallets" class="text-3xl font-bold">0</div>
            </div>
        </div>

        <!-- Wallet Table -->
        <div class="bg-gray-800 rounded-lg p-6 shadow-2xl">
            <h2 class="text-2xl font-bold mb-4">📋 Wallet Trading Activity</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="border-b-2 border-gray-700">
                            <th class="text-left py-3">Wallet</th>
                            <th class="text-left py-3">EOA Address (Trading)</th>
                            <th class="text-left py-3">Funder/Safe</th>
                            <th class="text-right py-3">Volume</th>
                            <th class="text-right py-3">P&L</th>
                            <th class="text-right py-3">Trades</th>
                            <th class="text-center py-3">Status</th>
                        </tr>
                    </thead>
                    <tbody id="walletTableBody">
                        <tr><td colspan="7" class="text-center py-8 text-gray-500">
                            <div class="loading inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                            <div class="mt-2">Loading wallet data...</div>
                        </td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Footer -->
        <div class="mt-6 text-center text-gray-500 text-sm">
            <p>EOA = Externally Owned Account (actual trading wallet)</p>
            <p>Funder = Safe/Proxy wallet (holds funds)</p>
        </div>
    </div>

    <script>
        function formatCurrency(amount) {
            if (amount === null || amount === undefined) return '$0.00';
            const prefix = amount < 0 ? '-$' : '$';
            return prefix + Math.abs(amount).toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }

        function formatAddress(address) {
            return address.slice(0, 6) + '...' + address.slice(-4);
        }

        async function refreshData() {
            try {
                const response = await fetch('/api/wallets');
                const data = await response.json();

                // Update summary
                document.getElementById('totalVolume').textContent = formatCurrency(data.summary.total_volume);
                document.getElementById('totalPnL').textContent = formatCurrency(data.summary.total_pnl);
                document.getElementById('totalPnL').className = data.summary.total_pnl >= 0 ?
                    'text-3xl font-bold text-green-300' : 'text-3xl font-bold text-red-300';
                document.getElementById('totalTrades').textContent = data.summary.total_trades.toLocaleString();
                document.getElementById('activeWallets').textContent = data.summary.active_wallets;

                // Update table
                const tbody = document.getElementById('walletTableBody');
                tbody.innerHTML = '';

                data.wallets.forEach((wallet, index) => {
                    const row = document.createElement('tr');
                    row.className = 'border-b border-gray-700 hover:bg-gray-750 transition fade-in';

                    const pnlClass = wallet.pnl >= 0 ? 'text-green-400' : 'text-red-400';
                    const statusClass = wallet.status === 'Active' ? 'text-green-400' : 'text-gray-500';
                    const statusIcon = wallet.status === 'Active' ? '🟢' : '⚫';

                    row.innerHTML = `
                        <td class="py-3 font-semibold">
                            ${wallet.number === 1 ? '👑 ' : ''}Wallet ${wallet.number}
                        </td>
                        <td class="py-3">
                            <a href="https://polymarket.com/profile/${wallet.eoa}"
                               target="_blank"
                               class="text-blue-400 hover:text-blue-300 transition">
                                ${formatAddress(wallet.eoa)}
                            </a>
                        </td>
                        <td class="py-3 text-gray-400">
                            ${formatAddress(wallet.funder)}
                        </td>
                        <td class="text-right py-3 font-semibold">${formatCurrency(wallet.volume)}</td>
                        <td class="text-right py-3 font-bold ${pnlClass}">${formatCurrency(wallet.pnl)}</td>
                        <td class="text-right py-3">${wallet.trades.toLocaleString()}</td>
                        <td class="text-center py-3">
                            <span class="${statusClass}">${statusIcon} ${wallet.status}</span>
                        </td>
                    `;
                    tbody.appendChild(row);
                });

                // Update timestamp
                document.getElementById('lastUpdate').textContent = new Date().toLocaleString();

            } catch (error) {
                console.error('Error refreshing data:', error);
                alert('Error loading data. Check console for details.');
            }
        }

        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);

        // Initial load
        window.addEventListener('DOMContentLoaded', refreshData);
    </script>
</body>
</html>
'''

def fetch_wallet_stats(eoa_address, funder_address):
    """Fetch wallet statistics from Polymarket using EOA address"""

    stats = {
        'eoa': eoa_address,
        'funder': funder_address,
        'volume': 0,
        'pnl': 0,
        'trades': 0,
        'status': 'Inactive'
    }

    # Try fetching data for EOA address (actual trading wallet)
    try:
        # Try Graph API with EOA address
        graph_url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-5"

        query = {
            "query": f"""
            {{
                user(id: "{eoa_address.lower()}") {{
                    id
                    numTrades
                    totalVolume
                    numMarkets
                }}
            }}
            """
        }

        response = requests.post(graph_url, json=query, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get('data') and data['data'].get('user'):
                user = data['data']['user']
                stats['volume'] = float(user.get('totalVolume', 0)) / 1e6 if user.get('totalVolume') else 0
                stats['trades'] = int(user.get('numTrades', 0)) if user.get('numTrades') else 0
                stats['status'] = 'Active' if stats['trades'] > 0 else 'Inactive'

    except Exception as e:
        print(f"Error fetching EOA {eoa_address}: {e}")

    # If no data from EOA, try funder address
    if stats['trades'] == 0:
        try:
            query = {
                "query": f"""
                {{
                    user(id: "{funder_address.lower()}") {{
                        id
                        numTrades
                        totalVolume
                        numMarkets
                    }}
                }}
                """
            }

            response = requests.post(graph_url, json=query, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('data') and data['data'].get('user'):
                    user = data['data']['user']
                    stats['volume'] = float(user.get('totalVolume', 0)) / 1e6 if user.get('totalVolume') else 0
                    stats['trades'] = int(user.get('numTrades', 0)) if user.get('numTrades') else 0
                    stats['status'] = 'Active' if stats['trades'] > 0 else 'Inactive'

        except Exception as e:
            print(f"Error fetching funder {funder_address}: {e}")

    return stats

@app.route('/')
def index():
    """Serve the dashboard HTML"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/wallets')
def get_wallets():
    """API endpoint to fetch all wallet data"""

    wallets = load_wallet_addresses()
    wallet_stats = []

    total_volume = 0
    total_pnl = 0
    total_trades = 0
    active_count = 0

    for wallet in wallets:
        stats = fetch_wallet_stats(wallet['address'], wallet['funder'])
        stats['number'] = wallet['number']

        wallet_stats.append(stats)

        # Calculate totals
        total_volume += stats['volume']
        total_pnl += stats['pnl']
        total_trades += stats['trades']
        if stats['status'] == 'Active':
            active_count += 1

    return jsonify({
        'wallets': wallet_stats,
        'summary': {
            'total_volume': total_volume,
            'total_pnl': total_pnl,
            'total_trades': total_trades,
            'active_wallets': active_count
        },
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Starting Real Trading Dashboard...")
    print("📊 Dashboard: http://localhost:5555")
    print("🎯 Checking EOA addresses (actual trading wallets)")

    wallets = load_wallet_addresses()
    print(f"\n📍 Found {len(wallets)} wallets:")
    for w in wallets:
        print(f"   Wallet {w['number']}:")
        print(f"     EOA (Trading): {w['address']}")
        print(f"     Funder (Safe): {w['funder']}")

    print("\n✨ Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=5555, debug=True)