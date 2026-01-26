"""
Cancel pending TX for agent by sending 0-value TX with same nonce + higher gas
"""
import os
import sys
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3
from dotenv import load_dotenv
from services.agent_keys import decrypt_private_key

load_dotenv()

# Agent addresses
AGENT_EOA = "0x8FE9c7b9a195D37C789D3529E6903394a52b5e82"
USER_ADDRESS = "0xba9d6947c0ad6ea2aaa99507355cf83b4d098058"

# Get agent's encrypted key from deployed_agents.json
import json
agents_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api', 'deployed_agents.json')
with open(agents_file, 'r') as f:
    all_agents = json.load(f)

user_agents = all_agents.get(USER_ADDRESS.lower(), [])
if not user_agents:
    print("❌ No agents found for user")
    exit(1)

agent = user_agents[0]
encrypted_pk = agent.get("encrypted_private_key")

if not encrypted_pk:
    print("❌ Agent has no private key")
    exit(1)

# Decrypt key
private_key = decrypt_private_key(encrypted_pk)

# Connect to Base
RPC_URL = os.getenv("ALCHEMY_RPC_URL") or "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

from eth_account import Account
account = Account.from_key(private_key)

print(f"🔑 Agent: {account.address}")
print(f"💰 ETH Balance: {w3.eth.get_balance(account.address) / 1e18:.6f}")

# Get pending and confirmed nonce
pending_nonce = w3.eth.get_transaction_count(account.address, 'pending')
confirmed_nonce = w3.eth.get_transaction_count(account.address)

print(f"📊 Confirmed nonce: {confirmed_nonce}, Pending nonce: {pending_nonce}")

if pending_nonce == confirmed_nonce:
    print("✅ No pending transactions! Nonces match.")
    exit(0)

# There's a stuck TX - cancel it with 0-value TX at same nonce but higher gas
stuck_nonce = confirmed_nonce
print(f"⚠️ Stuck TX at nonce {stuck_nonce} - cancelling with higher gas...")

gas_price = w3.eth.gas_price
high_gas = int(gas_price * 10)  # 10x gas price to guarantee replacement

tx = {
    'nonce': stuck_nonce,
    'to': account.address,  # Send to self
    'value': 0,
    'gas': 21000,
    'gasPrice': high_gas,
    'chainId': 8453
}

signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

print(f"🚀 Cancel TX sent: {tx_hash.hex()}")
print(f"🔗 https://basescan.org/tx/{tx_hash.hex()}")

print("⏳ Waiting...")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

if receipt.status == 1:
    print("✅ Pending TX cancelled!")
else:
    print("❌ Cancel TX failed")
