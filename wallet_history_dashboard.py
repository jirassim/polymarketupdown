#!/usr/bin/env python3
"""
Polymarket Wallet History Dashboard
Fetches complete trading history from Polymarket Subgraph
"""

import json
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Flask, render_template_string, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Main wallet address from leaderboard
MAIN_WALLET = "0x707a2F7b8884E45bF5AA26f0dC44aA3aE309D4ff"

# Polymarket Subgraph endpoint
SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-5"

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Wallet History Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-4">
        <!-- Header -->
        <div class="bg-gray-800 rounded-lg p-6 mb-6">
            <h1 class="text-3xl font-bold mb-2">Polymarket Trading History</h1>
            <p class="text-gray-400">Complete trading history from Polymarket Subgraph</p>
            <div class="mt-4">
                <input type="text" id="walletInput"
                       placeholder="Enter wallet address (0x...)"
                       value="{{ main_wallet }}"
                       class="bg-gray-700 text-white px-4 py-2 rounded-lg w-96 mr-2">
                <button onclick="loadWallet()" class="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg">
                    📊 Load History
                </button>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">Total Volume</div>
                <div id="totalVolume" class="text-2xl font-bold">Loading...</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">Total P&L</div>
                <div id="totalPnL" class="text-2xl font-bold">Loading...</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">Win Rate</div>
                <div id="winRate" class="text-2xl font-bold">0%</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">Total Trades</div>
                <div id="totalTrades" class="text-2xl font-bold">0</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">Active Markets</div>
                <div id="activeMarkets" class="text-2xl font-bold">0</div>
            </div>
        </div>

        <!-- Charts -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div class="bg-gray-800 rounded-lg p-6">
                <h3 class="text-xl font-bold mb-4">Volume Over Time</h3>
                <canvas id="volumeChart"></canvas>
            </div>
            <div class="bg-gray-800 rounded-lg p-6">
                <h3 class="text-xl font-bold mb-4">P&L Over Time</h3>
                <canvas id="pnlChart"></canvas>
            </div>
        </div>

        <!-- Trade History Table -->
        <div class="bg-gray-800 rounded-lg p-6">
            <h2 class="text-xl font-bold mb-4">Recent Trades</h2>
            <div class="overflow-x-auto">
                <table class="w-full">
                    <thead>
                        <tr class="border-b border-gray-700">
                            <th class="text-left py-2">Date</th>
                            <th class="text-left py-2">Market</th>
                            <th class="text-center py-2">Side</th>
                            <th class="text-right py-2">Size</th>
                            <th class="text-right py-2">Price</th>
                            <th class="text-right py-2">Value</th>
                            <th class="text-right py-2">P&L</th>
                        </tr>
                    </thead>
                    <tbody id="tradesTableBody">
                        <tr><td colspan="7" class="text-center py-4">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let volumeChart = null;
        let pnlChart = null;

        function formatCurrency(amount) {
            if (amount === null || amount === undefined) return '$0.00';
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount);
        }

        function formatDate(timestamp) {
            return new Date(timestamp * 1000).toLocaleDateString();
        }

        async function loadWallet() {
            const address = document.getElementById('walletInput').value;
            if (!address) return;

            try {
                const response = await fetch(`/api/wallet/${address}`);
                const data = await response.json();

                // Update summary
                document.getElementById('totalVolume').textContent = formatCurrency(data.summary.total_volume);
                document.getElementById('totalPnL').textContent = formatCurrency(data.summary.total_pnl);
                document.getElementById('totalPnL').className = data.summary.total_pnl >= 0 ?
                    'text-2xl font-bold text-green-400' : 'text-2xl font-bold text-red-400';
                document.getElementById('winRate').textContent = data.summary.win_rate + '%';
                document.getElementById('totalTrades').textContent = data.summary.total_trades;
                document.getElementById('activeMarkets').textContent = data.summary.active_markets;

                // Update charts
                updateCharts(data.charts);

                // Update trades table
                const tbody = document.getElementById('tradesTableBody');
                tbody.innerHTML = '';

                data.trades.slice(0, 50).forEach(trade => {
                    const row = document.createElement('tr');
                    row.className = 'border-b border-gray-700';

                    const sideClass = trade.side === 'BUY' ? 'text-green-400' : 'text-red-400';
                    const pnlClass = trade.pnl >= 0 ? 'text-green-400' : 'text-red-400';

                    row.innerHTML = `
                        <td class="py-2">${formatDate(trade.timestamp)}</td>
                        <td class="py-2 text-sm">${trade.market.substring(0, 50)}...</td>
                        <td class="text-center py-2">
                            <span class="${sideClass}">${trade.side}</span>
                        </td>
                        <td class="text-right py-2">${trade.size.toFixed(2)}</td>
                        <td class="text-right py-2">${trade.price.toFixed(2)}</td>
                        <td class="text-right py-2">${formatCurrency(trade.value)}</td>
                        <td class="text-right py-2 ${pnlClass}">${formatCurrency(trade.pnl)}</td>
                    `;
                    tbody.appendChild(row);
                });

            } catch (error) {
                console.error('Error loading wallet data:', error);
                alert('Error loading wallet data. Check console for details.');
            }
        }

        function updateCharts(chartData) {
            // Volume Chart
            const volumeCtx = document.getElementById('volumeChart').getContext('2d');
            if (volumeChart) volumeChart.destroy();

            volumeChart = new Chart(volumeCtx, {
                type: 'line',
                data: {
                    labels: chartData.dates,
                    datasets: [{
                        label: 'Daily Volume',
                        data: chartData.volume,
                        borderColor: 'rgb(59, 130, 246)',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: 'rgb(156, 163, 175)' }
                        },
                        x: {
                            ticks: { color: 'rgb(156, 163, 175)' }
                        }
                    }
                }
            });

            // P&L Chart
            const pnlCtx = document.getElementById('pnlChart').getContext('2d');
            if (pnlChart) pnlChart.destroy();

            pnlChart = new Chart(pnlCtx, {
                type: 'line',
                data: {
                    labels: chartData.dates,
                    datasets: [{
                        label: 'Cumulative P&L',
                        data: chartData.pnl,
                        borderColor: chartData.pnl[chartData.pnl.length - 1] >= 0 ?
                            'rgb(34, 197, 94)' : 'rgb(239, 68, 68)',
                        backgroundColor: chartData.pnl[chartData.pnl.length - 1] >= 0 ?
                            'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            ticks: { color: 'rgb(156, 163, 175)' }
                        },
                        x: {
                            ticks: { color: 'rgb(156, 163, 175)' }
                        }
                    }
                }
            });
        }

        // Load on page load
        window.addEventListener('DOMContentLoaded', loadWallet);
    </script>
</body>
</html>
'''

def fetch_wallet_history(address):
    """Fetch complete trading history from Polymarket Subgraph"""

    # GraphQL query for all trades
    query = """
    query GetWalletHistory($user: String!) {
        user(id: $user) {
            id
            numTrades
            numMarkets
            totalVolume
            trades(first: 1000, orderBy: timestamp, orderDirection: desc) {
                id
                timestamp
                market {
                    id
                    question
                }
                outcome
                side
                size
                price
                feeRate
            }
            positions(first: 100) {
                id
                market {
                    id
                    question
                }
                outcome
                quantityBought
                quantitySold
                valueBought
                valueSold
            }
        }
    }
    """

    try:
        response = requests.post(
            SUBGRAPH_URL,
            json={
                'query': query,
                'variables': {'user': address.lower()}
            },
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()

            if 'data' in data and data['data'] and 'user' in data['data']:
                user = data['data']['user']

                # Process trades
                trades = []
                total_volume = 0
                total_pnl = 0
                buy_value = 0
                sell_value = 0

                if user and 'trades' in user:
                    for trade in user['trades']:
                        size = float(trade['size']) / 1e6  # Convert from wei
                        price = float(trade['price'])
                        value = size * price

                        trade_data = {
                            'timestamp': int(trade['timestamp']),
                            'market': trade['market']['question'] if 'market' in trade else 'Unknown',
                            'side': trade['side'],
                            'size': size,
                            'price': price,
                            'value': value,
                            'pnl': 0  # Will calculate based on positions
                        }

                        if trade['side'] == 'BUY':
                            buy_value += value
                        else:
                            sell_value += value

                        trades.append(trade_data)
                        total_volume += value

                # Calculate P&L from positions
                positions_pnl = 0
                if user and 'positions' in user:
                    for position in user['positions']:
                        bought = float(position.get('valueBought', 0)) / 1e6
                        sold = float(position.get('valueSold', 0)) / 1e6
                        positions_pnl += (sold - bought)

                total_pnl = positions_pnl

                # Calculate win rate
                wins = sum(1 for t in trades if t['side'] == 'SELL' and t['value'] > 0)
                total_closed = sum(1 for t in trades if t['side'] == 'SELL')
                win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

                # Prepare chart data (daily aggregation)
                daily_data = {}
                for trade in trades:
                    date = datetime.fromtimestamp(trade['timestamp']).strftime('%Y-%m-%d')
                    if date not in daily_data:
                        daily_data[date] = {'volume': 0, 'pnl': 0}
                    daily_data[date]['volume'] += trade['value']

                # Sort dates and create chart arrays
                sorted_dates = sorted(daily_data.keys())
                cumulative_pnl = 0
                chart_data = {
                    'dates': sorted_dates[-30:],  # Last 30 days
                    'volume': [daily_data[d]['volume'] for d in sorted_dates[-30:]],
                    'pnl': []
                }

                # Calculate cumulative P&L
                for date in sorted_dates[-30:]:
                    cumulative_pnl += daily_data[date]['pnl']
                    chart_data['pnl'].append(cumulative_pnl)

                return {
                    'summary': {
                        'total_volume': total_volume,
                        'total_pnl': total_pnl,
                        'win_rate': round(win_rate, 1),
                        'total_trades': len(trades),
                        'active_markets': user.get('numMarkets', 0) if user else 0
                    },
                    'trades': trades,
                    'charts': chart_data
                }

    except Exception as e:
        print(f"Error fetching wallet history: {e}")

    # Return empty data on error
    return {
        'summary': {
            'total_volume': 0,
            'total_pnl': 0,
            'win_rate': 0,
            'total_trades': 0,
            'active_markets': 0
        },
        'trades': [],
        'charts': {
            'dates': [],
            'volume': [],
            'pnl': []
        }
    }

@app.route('/')
def index():
    """Serve the dashboard HTML"""
    return render_template_string(HTML_TEMPLATE, main_wallet=MAIN_WALLET)

@app.route('/api/wallet/<address>')
def get_wallet_history(address):
    """API endpoint to fetch wallet history"""
    return jsonify(fetch_wallet_history(address))

if __name__ == '__main__':
    print("🚀 Starting Wallet History Dashboard...")
    print("📊 Dashboard: http://localhost:9999")
    print(f"📍 Default wallet: {MAIN_WALLET}")
    print("\n✨ Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=9999, debug=True)