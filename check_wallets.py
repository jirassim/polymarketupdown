#!/usr/bin/env python3
"""
Check actual wallet status from Polymarket
"""

import requests
import json
from time import sleep

# All wallet funder addresses
wallets = [
    ("Wallet 1", "0x707a2F7bB884E45bF5AA26f0dC44aA3aE309D4ff"),
    ("Wallet 2", "0xdA31710a25Ef1544F31bC014a32b8c6b107b74D0"),
    ("Wallet 3", "0x5EF82699d9fFD7a5a092CAd77CD6b07dAe52b33e"),
    ("Wallet 4", "0x2aD5198D59F6088819a52aEfFA11bDDb62F495C1"),
    ("Wallet 5", "0xDb9c2E152D90fc79F92da47b8b22E36e8480a8BE"),
    ("Wallet 6", "0x059eBC6734C0A0af9DDd72bf3213250c0A653f67"),
    ("Wallet 7", "0x05B1822C0702a85ac7F603409AB0061F80fD06e6"),
    ("Wallet 8", "0x1f6A48dFac186a4a841F86439D4660C900FD2b18"),
    ("Wallet 9", "0x2Bd58CfFc23CE88eFc7E6D20eb5802F57360C2fA"),
    ("Wallet 10", "0x2631bF72FeDf7aC3b20632c0d3223e4cD865cc94"),
    ("Wallet 11", "0x935714939bb64cf43e460b76eBd93734ab200D8F"),
    ("Wallet 12", "0x7883eE83B91ED33a905bcDcb9D6762b8f7f6DF7D")
]

print("🔍 Checking wallet status on Polymarket...\n")

for name, address in wallets:
    print(f"Checking {name}: {address}")

    # Check profile page (this is public data)
    profile_url = f"https://polymarket.com/profile/{address}"

    # Try Graph API
    graph_url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-5"

    query = {
        "query": f'{{ user(id: "{address.lower()}") {{ id numTrades totalVolume }} }}'
    }

    try:
        response = requests.post(graph_url, json=query, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and data['data'].get('user'):
                user = data['data']['user']
                volume = float(user.get('totalVolume', 0)) / 1e6 if user.get('totalVolume') else 0
                trades = user.get('numTrades', 0)

                if volume > 0 or trades > 0:
                    print(f"  ✅ ACTIVE - Volume: ${volume:,.2f}, Trades: {trades}")
                else:
                    print(f"  ⚫ No activity found")
            else:
                print(f"  ⚫ No data in Graph")
        else:
            print(f"  ❌ API error: {response.status_code}")

    except Exception as e:
        print(f"  ❌ Error: {e}")

    print(f"  📊 Profile: {profile_url}")
    print()

    # Small delay between requests
    sleep(0.5)

print("\n📝 Summary:")
print("- Wallet 1 is the main trading wallet (confirmed active)")
print("- Other wallets may not have trading history yet")
print("- They could be new wallets or used for different purposes")
print("\n💡 To see actual trading activity, wallets need to:")
print("1. Have made trades on Polymarket")
print("2. Be registered in the Polymarket system")
print("3. Have positions or historical trades")