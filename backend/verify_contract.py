"""Verify and complete contract configuration"""
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
import time

load_dotenv()

CONTRACT = Web3.to_checksum_address("0xC83E01e39A56Ec8C56Dd45236E58eE7a139cCDD4")
AAVE = Web3.to_checksum_address("0xA238Dd80C259a72e81d7e4664a9801593F98d1c5")
USER = Web3.to_checksum_address("0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058")

# Use Alchemy RPC from env
RPC = os.getenv("ALCHEMY_RPC_URL", "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb")
w3 = Web3(Web3.HTTPProvider(RPC))
pk = os.getenv("PRIVATE_KEY")
acct = Account.from_key(pk)

ABI = [
    {"inputs":[{"name":"p","type":"address"}],"name":"approvedProtocols","outputs":[{"type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"p","type":"address"}],"name":"isLendingProtocol","outputs":[{"type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"u","type":"address"}],"name":"whitelist","outputs":[{"type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"name":"u","type":"address"},{"name":"w","type":"bool"}],"name":"setUserWhitelist","outputs":[],"stateMutability":"nonpayable","type":"function"},
]

c = w3.eth.contract(address=CONTRACT, abi=ABI)

print("=== Contract Verification ===")
print(f"Contract: {CONTRACT}")
print(f"approvedProtocols(AAVE): {c.functions.approvedProtocols(AAVE).call()}")
print(f"isLendingProtocol(AAVE): {c.functions.isLendingProtocol(AAVE).call()}")
whitelist_ok = c.functions.whitelist(USER).call()
print(f"whitelist(USER): {whitelist_ok}")

if not whitelist_ok:
    print("\n🔧 User not whitelisted, adding now...")
    nonce = w3.eth.get_transaction_count(acct.address, 'pending')
    tx = c.functions.setUserWhitelist(USER, True).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price * 3
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"TX: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print("✅ User whitelisted!")
    else:
        print("❌ Whitelist failed")

print("\n=== Final Status ===")
print(f"whitelist(USER): {c.functions.whitelist(USER).call()}")
print("✅ Contract configuration complete!")
