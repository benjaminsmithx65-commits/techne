"""
Register backend PRIVATE_KEY as session key on smart account.

The old factory session key was lost (0x7B878...).
We're now using the backend's PRIVATE_KEY (0xa30A689...) as session key.

This script calls addSessionKey on the smart account.
"""
import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from web3 import Web3
from eth_account import Account

# Config
RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
BACKEND_PK = os.getenv("PRIVATE_KEY")
SMART_ACCOUNT = "0x8bfb3693E1d09e9C2F07Fb59A75120ED3B4617f5"

# Derive backend address
backend_account = Account.from_key(BACKEND_PK)
NEW_SESSION_KEY = backend_account.address

print("=== REGISTER BACKEND KEY AS SESSION KEY ===")
print(f"Smart Account: {SMART_ACCOUNT}")
print(f"New Session Key: {NEW_SESSION_KEY}")
print()

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Check if already registered
SESSION_KEY_ABI = [{
    'name': 'getSessionKeyInfo',
    'type': 'function',
    'stateMutability': 'view',
    'inputs': [{'name': 'key', 'type': 'address'}],
    'outputs': [
        {'name': 'active', 'type': 'bool'},
        {'name': 'validUntil', 'type': 'uint48'},
        {'name': 'dailyLimitUSD', 'type': 'uint256'},
        {'name': 'spentTodayUSD', 'type': 'uint256'}
    ]
}]

sa = w3.eth.contract(address=Web3.to_checksum_address(SMART_ACCOUNT), abi=SESSION_KEY_ABI)
try:
    info = sa.functions.getSessionKeyInfo(NEW_SESSION_KEY).call()
    print(f"Current status for {NEW_SESSION_KEY}:")
    print(f"  Active: {info[0]}")
    print(f"  Valid Until: {info[1]}")
    
    if info[0]:
        print()
        print("✅ Backend key is ALREADY registered as session key!")
        print("No action needed.")
        sys.exit(0)
except Exception as e:
    print(f"Error checking: {e}")

print()
print("⚠️  Backend key is NOT registered!")
print()
print("To register, the smart account OWNER must call:")
print()
print(f"  addSessionKey({NEW_SESSION_KEY}, validUntil, dailyLimitUSD)")
print()
print("Building calldata...")

# ABI for addSessionKey
ADD_SK_ABI = [{
    'name': 'addSessionKey',
    'type': 'function',
    'stateMutability': 'nonpayable',
    'inputs': [
        {'name': 'key', 'type': 'address'},
        {'name': 'validUntil', 'type': 'uint48'},
        {'name': 'dailyLimitUSD', 'type': 'uint256'}
    ],
    'outputs': []
}]

sa_add = w3.eth.contract(address=Web3.to_checksum_address(SMART_ACCOUNT), abi=ADD_SK_ABI)

# 1 year validity, $100k daily limit
VALID_UNTIL = 2**48 - 1  # Max uint48 = practically never expires
DAILY_LIMIT = 100000 * 10**8  # $100k with 8 decimals

calldata = sa_add.functions.addSessionKey(
    NEW_SESSION_KEY,
    VALID_UNTIL,
    DAILY_LIMIT
).build_transaction({
    'from': '0x0000000000000000000000000000000000000000',
    'gas': 100000,
    'nonce': 0
})['data']

print()
print("Transaction calldata:")
print(calldata)
print()
print("=== USER ACTION REQUIRED ===")
print(f"Go to Basescan, connect wallet, and call addSessionKey on {SMART_ACCOUNT}")
print(f"  - key: {NEW_SESSION_KEY}")
print(f"  - validUntil: {VALID_UNTIL}")  
print(f"  - dailyLimitUSD: {DAILY_LIMIT} (= $100,000)")
