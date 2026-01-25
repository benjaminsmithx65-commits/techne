"""
Withdraw ETH from shared executor account to your wallet.
This cleans up the old architecture - funds go back to owner.
"""

import os
import sys
from web3 import Web3
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Shared executor address
SHARED_EXECUTOR = "0xEe95B8114b144f48A742BA96Dc6c167a35829Fe1"

# Your destination wallet - change this!
DESTINATION = input("Enter destination wallet address: ").strip()

if not DESTINATION or not DESTINATION.startswith("0x"):
    print("❌ Invalid destination address")
    sys.exit(1)

# Get private key
PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY")
if not PRIVATE_KEY:
    print("❌ AGENT_PRIVATE_KEY not found in .env")
    sys.exit(1)

# Connect to Base
RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    print("❌ Cannot connect to Base network")
    sys.exit(1)

# Check balance
balance = w3.eth.get_balance(SHARED_EXECUTOR)
print(f"\n📊 Shared Executor Balance: {balance / 1e18:.6f} ETH")

if balance == 0:
    print("✅ Account is already empty!")
    sys.exit(0)

# Calculate gas cost (leave some for gas)
gas_price = w3.eth.gas_price
gas_limit = 21000  # Simple ETH transfer
gas_cost = gas_price * gas_limit
amount_to_send = balance - gas_cost

if amount_to_send <= 0:
    print(f"⚠️ Balance too low to cover gas ({gas_cost / 1e18:.6f} ETH needed)")
    sys.exit(1)

print(f"⛽ Gas cost: {gas_cost / 1e18:.6f} ETH")
print(f"💸 Amount to withdraw: {amount_to_send / 1e18:.6f} ETH")
print(f"📮 Destination: {DESTINATION}")

# Confirm
confirm = input("\n⚠️ Confirm withdrawal? (yes/no): ").strip().lower()
if confirm != "yes":
    print("❌ Cancelled")
    sys.exit(0)

# Build transaction
account = w3.eth.account.from_key(PRIVATE_KEY)
nonce = w3.eth.get_transaction_count(account.address)

tx = {
    'nonce': nonce,
    'to': Web3.to_checksum_address(DESTINATION),
    'value': amount_to_send,
    'gas': gas_limit,
    'gasPrice': gas_price,
    'chainId': 8453  # Base mainnet
}

# Sign and send
signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

print(f"\n🚀 Transaction sent!")
print(f"📝 TX Hash: {tx_hash.hex()}")
print(f"🔗 https://basescan.org/tx/{tx_hash.hex()}")

# Wait for confirmation
print("\n⏳ Waiting for confirmation...")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

if receipt.status == 1:
    print(f"✅ Success! Withdrew {amount_to_send / 1e18:.6f} ETH to {DESTINATION}")
else:
    print("❌ Transaction failed!")
