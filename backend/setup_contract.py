"""Configure new TechneAgentWalletV43 contract"""
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

# Config - correct contract at nonce 60
NEW_CONTRACT = Web3.to_checksum_address("0xC83E01e39A56Ec8C56Dd45236E58eE7a139cCDD4")
AAVE_POOL = Web3.to_checksum_address("0xA238Dd80C259a72e81d7e4664a9801593F98d1c5")
USER_ADDRESS = Web3.to_checksum_address("0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058")

# Use Alchemy RPC
RPC = os.getenv("ALCHEMY_RPC_URL", "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb")
w3 = Web3(Web3.HTTPProvider(RPC))
private_key = os.getenv("PRIVATE_KEY")
account = Account.from_key(private_key)

print(f"Configuring contract: {NEW_CONTRACT}")
print(f"Using account: {account.address}")
print(f"Balance: {w3.eth.get_balance(account.address) / 1e18:.6f} ETH")

# CORRECT ABI for V4.3.4
ABI = [
    # approveProtocol(address protocol, bool approved, bool _isLending)
    {"inputs": [{"name": "protocol", "type": "address"}, {"name": "approved", "type": "bool"}, {"name": "_isLending", "type": "bool"}], "name": "approveProtocol", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    # whitelistUser(address user)
    {"inputs": [{"name": "user", "type": "address"}], "name": "whitelistUser", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    # View functions
    {"inputs": [{"name": "protocol", "type": "address"}], "name": "approvedProtocols", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "protocol", "type": "address"}], "name": "isLendingProtocol", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "role", "type": "bytes32"}, {"name": "account", "type": "address"}], "name": "hasRole", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "WHITELISTED_ROLE", "outputs": [{"type": "bytes32"}], "stateMutability": "view", "type": "function"},
]

contract = w3.eth.contract(address=NEW_CONTRACT, abi=ABI)

def send_tx(func):
    nonce = w3.eth.get_transaction_count(account.address, 'pending')
    tx = func.build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 150000,
        'gasPrice': w3.eth.gas_price * 2
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"   TX: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt.status == 1

# Check current state
print(f"\n--- Current State ---")
print(f"approvedProtocols(AAVE): {contract.functions.approvedProtocols(AAVE_POOL).call()}")
print(f"isLendingProtocol(AAVE): {contract.functions.isLendingProtocol(AAVE_POOL).call()}")

if not contract.functions.approvedProtocols(AAVE_POOL).call():
    print("\n1. Approving AAVE as protocol + lending...")
    if send_tx(contract.functions.approveProtocol(AAVE_POOL, True, True)):
        print("   ✅ Done")
    else:
        print("   ❌ Failed")
else:
    print("\n1. AAVE already approved ✅")

# Check whitelist
WHITELISTED_ROLE = contract.functions.WHITELISTED_ROLE().call()
is_whitelisted = contract.functions.hasRole(WHITELISTED_ROLE, USER_ADDRESS).call()
print(f"\nUser whitelisted: {is_whitelisted}")

if not is_whitelisted:
    print("\n2. Whitelisting user...")
    if send_tx(contract.functions.whitelistUser(USER_ADDRESS)):
        print("   ✅ Done")
    else:
        print("   ❌ Failed")
else:
    print("\n2. User already whitelisted ✅")

# Final verification
print("\n--- Final State ---")
print(f"approvedProtocols(AAVE): {contract.functions.approvedProtocols(AAVE_POOL).call()}")
print(f"isLendingProtocol(AAVE): {contract.functions.isLendingProtocol(AAVE_POOL).call()}")
print(f"User whitelisted: {contract.functions.hasRole(WHITELISTED_ROLE, USER_ADDRESS).call()}")
print("\n✅ Configuration complete!")
