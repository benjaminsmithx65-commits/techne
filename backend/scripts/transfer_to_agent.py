"""
Transfer ETH from shared executor to agent EOA - automated
"""
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Addresses
SHARED_EXECUTOR = "0xEe95B8114b144f48A742BA96Dc6c167a35829Fe1"
AGENT_EOA = "0x8FE9c7b9a195D37C789D3529E6903394a52b5e82"  # User's agent

# Get private key
PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY")
if not PRIVATE_KEY:
    print("❌ AGENT_PRIVATE_KEY not found in .env")
    exit(1)

# Connect to Base
RPC_URL = os.getenv("ALCHEMY_RPC_URL") or os.getenv("BASE_RPC_URL") or "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    print("❌ Cannot connect to Base network")
    exit(1)

# Check balance
balance = w3.eth.get_balance(SHARED_EXECUTOR)
print(f"\n📊 Shared Executor Balance: {balance / 1e18:.6f} ETH")

if balance == 0:
    print("❌ Account is empty!")
    exit(1)

# Calculate gas cost
gas_price = w3.eth.gas_price
gas_limit = 21000
gas_cost = gas_price * gas_limit * 20  # Much higher to speed up pending TX
amount_to_send = balance - gas_cost

if amount_to_send <= 0:
    print(f"⚠️ Balance too low to cover gas")
    exit(1)

print(f"⛽ Gas cost: {gas_cost / 1e18:.6f} ETH")
print(f"💸 Amount to transfer: {amount_to_send / 1e18:.6f} ETH")
print(f"📮 To Agent: {AGENT_EOA}")

# Build transaction
account = w3.eth.account.from_key(PRIVATE_KEY)
print(f"🔑 Signer: {account.address}")

# Verify signer matches executor
if account.address.lower() != SHARED_EXECUTOR.lower():
    print(f"❌ AGENT_PRIVATE_KEY is for {account.address}, not {SHARED_EXECUTOR}")
    exit(1)

nonce = w3.eth.get_transaction_count(account.address)

tx = {
    'nonce': nonce,
    'to': Web3.to_checksum_address(AGENT_EOA),
    'value': amount_to_send,
    'gas': gas_limit,
    'gasPrice': gas_price,
    'chainId': 8453
}

# Sign and send
signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

print(f"\n🚀 TX sent: {tx_hash.hex()}")
print(f"🔗 https://basescan.org/tx/{tx_hash.hex()}")

# Wait
print("\n⏳ Waiting...")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

if receipt.status == 1:
    print(f"✅ SUCCESS! Transferred {amount_to_send / 1e18:.6f} ETH to agent")
else:
    print("❌ TX failed!")
