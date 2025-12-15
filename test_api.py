#!/usr/bin/env python3
"""
Test Polymarket API directly to see which addresses have data
"""

import requests
import json

# Test addresses
test_addresses = [
    ("Wallet 1 Funder", "0x707a2F7bB884E45bF5AA26f0dC44aA3aE309D4ff"),
    ("Wallet 1 EOA", "0xa58A6c6e96f76010420d99e91f8111B28bD087B6"),
    ("Wallet 2 Funder", "0xdA31710a25Ef1544F31bC014a32b8c6b107b74D0"),
    ("Wallet 2 EOA", "0xC63e3BCB7c23fBF5bF819179B2374E7596d06A8D"),
]

print("🔍 Testing Polymarket API responses...\n")

for name, address in test_addresses:
    print(f"Testing {name}: {address}")

    # Test Graph API
    graph_url = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets-5"

    query = {
        "query": f'''
        {{
            user(id: "{address.lower()}") {{
                id
                numTrades
                totalVolume
                numMarkets
            }}
        }}
        '''
    }

    try:
        response = requests.post(graph_url, json=query, timeout=10)
        print(f"  Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
        else:
            print(f"  Error: {response.text}")

    except Exception as e:
        print(f"  Exception: {e}")

    print()

print("\n" + "="*60)
print("Testing alternative endpoint - CLOB Leaderboard")
print("="*60 + "\n")

# Try leaderboard endpoint
for name, address in test_addresses[:2]:  # Test first 2 only
    print(f"Checking {name} on leaderboard...")

    try:
        # Try to get from public leaderboard data
        url = f"https://clob.polymarket.com/user/{address.lower()}"
        response = requests.get(url, timeout=5)

        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  Data: {response.text[:200]}...")
        else:
            print(f"  Error: {response.text[:200]}")
    except Exception as e:
        print(f"  Exception: {e}")

    print()

print("\n💡 Recommendation:")
print("If all APIs return null/empty, it means:")
print("1. These wallets haven't made ANY trades yet on Polymarket")
print("2. OR the Graph API is not indexing these addresses")
print("3. OR we need to use a different API/method to get the data")