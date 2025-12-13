#!/usr/bin/env python3
"""
Final Working Dashboard - Using polymarket-apis library
Based on Grok Expert's solution
"""

import json
import time
from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
from datetime import datetime
from polymarket_apis.clients import PolymarketDataClient
from collections import defaultdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

# Load wallet addresses from config
def load_wallet_addresses():
    """Load Funder addresses from config.json"""
    with open('../config.json', 'r') as f:
        config = json.load(f)

    wallets = []
    wallet_configs = [
        ('wallet', 1), ('wallet2', 2), ('wallet3', 3), ('wallet4', 4),
        ('wallet5', 5), ('wallet6', 6), ('wallet7', 7), ('wallet8', 8),
        ('wallet9', 9), ('wallet10', 10), ('wallet11', 11), ('wallet12', 12)
    ]

    for wallet_key, number in wallet_configs:
        if wallet_key in config:
            wallets.append({
                'number': number,
                'funder': config[wallet_key]['funder'],
                'address': config[wallet_key]['address']
            })

    return wallets

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Polymarket Up Down Bot - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .loading { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    </style>
</head>
<body class="bg-gray-900 text-white">
    <div class="container mx-auto p-4">
        <!-- Header -->
        <div class="bg-gradient-to-r from-green-700 to-blue-700 rounded-lg p-6 mb-6">
            <h1 class="text-4xl font-bold mb-2">🎯 Polymarket Up Down Bot Dashboard</h1>
            <p class="text-gray-200">Automated trading bot for crypto UP/DOWN markets - Real-time monitoring across 12 wallets</p>
            <div class="mt-3 text-sm text-gray-100">
                <p>🤖 Auto-trading BTC, ETH, SOL, XRP UP/DOWN markets | 📊 Live data every 30 seconds | ⚡ 24/7 Operation</p>
            </div>
            <div class="mt-4">
                <button onclick="refreshData()" class="bg-white text-blue-700 hover:bg-gray-100 px-6 py-3 rounded-lg text-lg font-semibold">
                    🔄 Refresh Data
                </button>
                <span class="ml-4 text-sm">Last updated: <span id="lastUpdate">Never</span></span>
            </div>
        </div>

        <!-- Summary -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">📊 Total Volume</div>
                <div id="totalVolume" class="text-3xl font-bold">Loading...</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">💵 Total P&L</div>
                <div id="totalPnL" class="text-3xl font-bold">Loading...</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">📈 Total Trades</div>
                <div id="totalTrades" class="text-3xl font-bold">0</div>
            </div>
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="text-gray-400 text-sm">✅ Active Wallets</div>
                <div id="activeWallets" class="text-3xl font-bold">0</div>
            </div>
        </div>

        <!-- Wallets Table -->
        <div class="bg-gray-800 rounded-lg p-6">
            <h2 class="text-2xl font-bold mb-4">📋 All 12 Wallets</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-sm">
                    <thead>
                        <tr class="border-b-2 border-gray-700">
                            <th class="text-left py-3">Wallet</th>
                            <th class="text-left py-3">Funder Address</th>
                            <th class="text-right py-3">Volume</th>
                            <th class="text-right py-3">P&L</th>
                            <th class="text-right py-3">Trades</th>
                            <th class="text-center py-3">Status</th>
                        </tr>
                    </thead>
                    <tbody id="walletTableBody">
                        <tr><td colspan="6" class="text-center py-8">
                            <div class="loading inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                            <div class="mt-2">Loading from Polymarket API...</div>
                        </td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Contact Section -->
        <div class="mt-6 bg-gradient-to-r from-purple-800 to-blue-800 rounded-lg p-6">
            <h2 class="text-2xl font-bold mb-3 text-center">💬 Contact for Try Market UP/DOWN</h2>
            <p class="text-center text-gray-200 mb-4">Interested in automated crypto trading? Send us your details!</p>

            <form id="contactForm" class="max-w-lg mx-auto" onsubmit="return false;">
                <div class="mb-4">
                    <label class="block text-sm font-semibold mb-2">Your Email</label>
                    <input type="email" id="userEmail" required
                           class="w-full px-4 py-2 rounded-lg bg-gray-700 border border-gray-600 text-white focus:outline-none focus:border-blue-500"
                           placeholder="your.email@example.com">
                </div>
                <div class="mb-4">
                    <label class="block text-sm font-semibold mb-2">Message (Optional)</label>
                    <textarea id="userMessage" rows="3"
                              class="w-full px-4 py-2 rounded-lg bg-gray-700 border border-gray-600 text-white focus:outline-none focus:border-blue-500"
                              placeholder="Tell us about your trading needs..."></textarea>
                </div>
                <button type="submit"
                        class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition">
                    📧 Send Contact Request
                </button>
            </form>

            <div class="mt-4 text-center text-sm text-gray-300">
                <p>📬 Direct Email: <a href="mailto:polymarket.up.down@gmail.com" class="text-blue-300 hover:text-blue-200">polymarket.up.down@gmail.com</a></p>
            </div>
        </div>

        <!-- Footer -->
        <div class="mt-6 text-center text-gray-400 text-sm">
            <p>📡 Data from: data-api.polymarket.com | Using polymarket-apis v0.4.2</p>
            <p class="mt-2">🤖 Automated Bot Trading BTC/ETH/SOL/XRP UP/DOWN Markets</p>
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
                    'text-3xl font-bold text-green-400' : 'text-3xl font-bold text-red-400';
                document.getElementById('totalTrades').textContent = data.summary.total_trades.toLocaleString();
                document.getElementById('activeWallets').textContent = data.summary.active_wallets;

                // Update table
                const tbody = document.getElementById('walletTableBody');
                tbody.innerHTML = '';

                data.wallets.forEach((wallet) => {
                    const row = document.createElement('tr');
                    row.className = 'border-b border-gray-700 hover:bg-gray-750';

                    const pnlClass = wallet.pnl >= 0 ? 'text-green-400' : 'text-red-400';
                    const statusClass = wallet.status === 'Active' ? 'text-green-400' : 'text-gray-500';
                    const statusIcon = wallet.status === 'Active' ? '🟢' : '⚫';

                    row.innerHTML = `
                        <td class="py-3 font-semibold">
                            ${wallet.number === 1 ? '👑 ' : ''}Wallet ${wallet.number}
                        </td>
                        <td class="py-3">
                            <a href="https://polymarket.com/profile/${wallet.funder}"
                               target="_blank"
                               class="text-blue-400 hover:text-blue-300">
                                ${formatAddress(wallet.funder)}
                            </a>
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

                document.getElementById('lastUpdate').textContent = new Date().toLocaleString();

            } catch (error) {
                console.error('Error:', error);
                alert('Error loading data: ' + error.message);
            }
        }

        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);

        // Initial load
        window.addEventListener('DOMContentLoaded', refreshData);

        // Contact Form Handler - Using Web3Forms
        const contactForm = document.getElementById('contactForm');
        if (contactForm) {
            contactForm.addEventListener('submit', async function(e) {
                e.preventDefault();

                const userEmail = document.getElementById('userEmail').value;
                const userMessage = document.getElementById('userMessage').value;
                const submitButton = this.querySelector('button[type="submit"]');

                // Disable button and show loading
                submitButton.disabled = true;
                submitButton.textContent = '📧 Sending...';

                try {
                    // Send via Web3Forms (free email service)
                    const formData = new FormData();
                    formData.append('access_key', 'YOUR_WEB3FORMS_ACCESS_KEY'); // Replace with your key
                    formData.append('subject', 'Contact Request - Market UP/DOWN Bot');
                    formData.append('name', userEmail);
                    formData.append('email', userEmail);
                    formData.append('message', userMessage || 'No message provided');

                    const response = await fetch('https://api.web3forms.com/submit', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();

                    if (result.success) {
                        alert('✅ Contact request sent successfully!\\n\\nWe will get back to you at: ' + userEmail);
                        contactForm.reset();
                    } else {
                        throw new Error(result.message || 'Failed to send');
                    }

                } catch (error) {
                    console.error('Error:', error);
                    alert('❌ Failed to send. Please email us directly at:\\npolymarket.up.down@gmail.com');
                } finally {
                    submitButton.disabled = false;
                    submitButton.textContent = '📧 Send Contact Request';
                }
            });
        } else {
            console.error('Contact form not found!');
        }
    </script>
</body>
</html>
'''

def fetch_wallet_stats(funder_address):
    """Fetch wallet statistics using polymarket-apis"""

    try:
        print(f"Fetching {funder_address[:10]}...")

        data_client = PolymarketDataClient()

        # Get user metrics (includes P&L)
        user_metric = data_client.get_user_metric(funder_address)
        total_pnl = user_metric.amount

        # Get total markets traded
        markets_traded = data_client.get_total_markets_traded(funder_address)

        # Get total volume from leaderboard (this is the "Volume / All" value!)
        leaderboard_data = data_client.get_leaderboard_user_rank(funder_address)
        total_volume = leaderboard_data.amount  # This is the accurate total volume

        status = 'Active' if markets_traded > 0 else 'Inactive'

        print(f"  ✅ Volume: ${total_volume:,.2f}, P&L: ${total_pnl:,.2f}, Markets: {markets_traded}")

        return {
            'funder': funder_address,
            'volume': total_volume,
            'pnl': total_pnl,
            'trades': markets_traded,
            'status': status
        }

    except Exception as e:
        import traceback
        print(f"  ❌ Error: {type(e).__name__}: {str(e)}")
        traceback.print_exc()

        return {
            'funder': funder_address,
            'volume': 0,
            'pnl': 0,
            'trades': 0,
            'status': 'Error'
        }

@app.route('/')
def index():
    """Serve the dashboard"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/send-contact', methods=['POST'])
def send_contact():
    """Save contact request to file"""
    try:
        data = request.get_json()
        user_email = data.get('email')
        user_message = data.get('message', 'No message provided')

        # Save to file
        with open('contact_requests.txt', 'a') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Email: {user_email}\n")
            f.write(f"Message: {user_message}\n")

        print(f"✅ Contact request saved from {user_email}")

        return jsonify({
            'success': True,
            'message': 'Thank you! Your request has been saved. We will contact you soon!'
        })

    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

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
    print("="*70)
    print("🤖 Polymarket Up Down Bot - Dashboard")
    print("="*70)
    print("\n📊 Dashboard URL: http://localhost:4444")
    print("🔗 API Library: polymarket-apis v0.4.2")
    print("📍 Data Source: data-api.polymarket.com")

    wallets = load_wallet_addresses()
    print(f"\n✅ Trading Wallets: {len(wallets)} wallets")
    print("\n📝 Bot Features:")
    print("   • Automated trading in BTC/ETH/SOL/XRP UP/DOWN markets")
    print("   • Real-time P&L monitoring across all wallets")
    print("   • Live data refresh every 30 seconds")
    print("   • Displays Volume, P&L, and Trade count")
    print("   • 24/7 automated operation")

    print("\n" + "="*70)
    print("✨ Press Ctrl+C to stop")
    print("="*70 + "\n")

    app.run(host='0.0.0.0', port=4444, debug=True)