from web3 import Web3
import requests
from datetime import datetime

w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

SMART_ACCOUNT = '0x8bfb3693E1d09e9C2F07Fb59A75120ED3B4617f5'
FACTORY = '0x9192DC52445E3d6e85EbB53723cFC2Eb9dD6e02A'

# Check factory transactions
print("=== FACTORY TRANSACTIONS ===")
url = f'https://api.basescan.org/api?module=account&action=txlist&address={FACTORY}&startblock=0&endblock=99999999&sort=asc'
resp = requests.get(url, timeout=10)
data = resp.json()

for tx in data.get('result', []):
    block = tx['blockNumber']
    func = tx.get('functionName', '')[:50] or 'deploy'
    ts = datetime.fromtimestamp(int(tx['timeStamp']))
    print(f"Block {block} | {ts} | {func}")

print()

# Check smart account internal TX (creation)
print("=== SMART ACCOUNT CREATION ===")  
url2 = f'https://api.basescan.org/api?module=account&action=txlistinternal&address={SMART_ACCOUNT}&startblock=0&endblock=99999999&sort=asc'
resp2 = requests.get(url2, timeout=10)
data2 = resp2.json()
for tx in data2.get('result', [])[:3]:
    block = tx['blockNumber']
    ts = datetime.fromtimestamp(int(tx['timeStamp']))
    print(f"Internal TX at block {block} | {ts}")
