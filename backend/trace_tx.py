"""
Trace all transactions for the agent wallet to find where funds went
"""
from web3 import Web3
import requests
import json
from datetime import datetime

AGENT = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
ROUTER = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43'

w3 = Web3(Web3.HTTPProvider('https://base-mainnet.public.blastapi.io'))

# ERC20 Transfer event signature
TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

# Get last transactions - use smaller range
print("=== FETCHING AGENT TRANSACTIONS ===")
print(f"Agent: {AGENT}")
print(f"Total TX count: {w3.eth.get_transaction_count(AGENT)}")
print("")

# Get recent blocks - smaller range
latest_block = w3.eth.block_number
start_block = latest_block - 10000  # ~6 hours

# Get USDC transfers TO agent
print("=== USDC TRANSFERS ===")
try:
    usdc_logs = w3.eth.get_logs({
        'address': Web3.to_checksum_address(USDC),
        'topics': [
            TRANSFER_TOPIC,
            None,  # from
            '0x' + AGENT[2:].lower().zfill(64)  # to = agent
        ],
        'fromBlock': start_block,
        'toBlock': 'latest'
    })
    print(f"USDC received: {len(usdc_logs)} transfers")
    for log in usdc_logs[-5:]:  # Last 5
        amount = int(log['data'].hex(), 16) / 1e6
        print(f"  +${amount:.2f} USDC in block {log['blockNumber']}")
except Exception as e:
    print(f"Error: {e}")

# Get USDC transfers FROM agent
print("")
try:
    usdc_out_logs = w3.eth.get_logs({
        'address': Web3.to_checksum_address(USDC),
        'topics': [
            TRANSFER_TOPIC,
            '0x' + AGENT[2:].lower().zfill(64),  # from = agent
            None  # to
        ],
        'fromBlock': start_block,
        'toBlock': 'latest'
    })
    print(f"USDC sent: {len(usdc_out_logs)} transfers")
    for log in usdc_out_logs[-10:]:
        amount = int(log['data'].hex(), 16) / 1e6
        to_addr = '0x' + log['topics'][2].hex()[-40:]
        print(f"  -${amount:.2f} USDC to {to_addr[:10]}... in block {log['blockNumber']}")
except Exception as e:
    print(f"Error: {e}")

# Get cbBTC transfers
print("")
print("=== cbBTC TRANSFERS ===")
try:
    cbbtc_in = w3.eth.get_logs({
        'address': Web3.to_checksum_address(CBBTC),
        'topics': [TRANSFER_TOPIC, None, '0x' + AGENT[2:].lower().zfill(64)],
        'fromBlock': start_block,
        'toBlock': 'latest'
    })
    print(f"cbBTC received: {len(cbbtc_in)} transfers")
    for log in cbbtc_in[-5:]:
        amount = int(log['data'].hex(), 16) / 1e8
        print(f"  +{amount:.8f} cbBTC in block {log['blockNumber']}")
except Exception as e:
    print(f"Error: {e}")

print("")
try:
    cbbtc_out = w3.eth.get_logs({
        'address': Web3.to_checksum_address(CBBTC),
        'topics': [TRANSFER_TOPIC, '0x' + AGENT[2:].lower().zfill(64), None],
        'fromBlock': start_block,
        'toBlock': 'latest'
    })
    print(f"cbBTC sent: {len(cbbtc_out)} transfers")
    for log in cbbtc_out[-5:]:
        amount = int(log['data'].hex(), 16) / 1e8
        to_addr = '0x' + log['topics'][2].hex()[-40:]
        print(f"  -{amount:.8f} cbBTC to {to_addr[:10]}... in block {log['blockNumber']}")
except Exception as e:
    print(f"Error: {e}")

# Summary
print("")
print("=== FUND FLOW SUMMARY ===")
print("Check Basescan for full history:")
print(f"https://basescan.org/address/{AGENT}#tokentxns")
