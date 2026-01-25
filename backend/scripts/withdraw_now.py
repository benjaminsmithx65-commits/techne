"""
Direct withdrawal to Smart Account - needs more gas
"""

import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

DESTINATION = "0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058"

PRIVATE_KEY = os.getenv("AGENT_PRIVATE_KEY")
w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

account = w3.eth.account.from_key(PRIVATE_KEY)
balance = w3.eth.get_balance(account.address)

print(f"From: {account.address}")
print(f"Balance: {balance / 1e18:.6f} ETH")

# Higher gas for smart contract receive
GAS_LIMIT = 50000
gas_price = w3.eth.gas_price
gas_cost = GAS_LIMIT * gas_price

send_amount = balance - gas_cost - w3.to_wei(0.0001, 'ether')

if send_amount <= 0:
    print("Not enough!")
    exit(1)

print(f"Gas limit: {GAS_LIMIT}")
print(f"Gas price: {gas_price / 1e9:.4f} gwei")
print(f"Max gas cost: {gas_cost / 1e18:.6f} ETH")
print(f"Sending: {send_amount / 1e18:.6f} ETH")

tx = {
    'nonce': w3.eth.get_transaction_count(account.address),
    'to': Web3.to_checksum_address(DESTINATION),
    'value': send_amount,
    'gas': GAS_LIMIT,
    'gasPrice': gas_price,
    'chainId': 8453
}

signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

print(f"TX Hash: {tx_hash.hex()}")
print(f"Link: https://basescan.org/tx/{tx_hash.hex()}")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
if receipt.status == 1:
    print("✅ SUCCESS!")
    print(f"Sent {send_amount / 1e18:.6f} ETH to {DESTINATION}")
    print(f"Gas used: {receipt.gasUsed}")
else:
    print("❌ FAILED")
    print(f"Gas used: {receipt.gasUsed}")
