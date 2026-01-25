"""
Setup protocol whitelist for a user's Smart Account.

This script is called after a user creates their Smart Account
to configure the allowed protocols and selectors for their session key.
"""

import os
import sys
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

RPC_URL = os.getenv("ALCHEMY_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # User's wallet (owner of Smart Account)

# Protocol addresses on Base mainnet
PROTOCOLS = {
    "aave_pool": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    "aerodrome_router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
    "cowswap_settlement": "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",
    "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "weth": "0x4200000000000000000000000000000000000006",
}

# Allowed selectors per protocol
ALLOWED_SELECTORS = {
    "aave_pool": [
        "0xe8eda9df",  # supply(address,uint256,address,uint16)
        "0x69328dec",  # withdraw(address,uint256,address)
    ],
    "aerodrome_router": [
        "0x5a47ddc3",  # addLiquidity(address,address,bool,uint256,uint256,uint256,uint256,address,uint256)
        "0xbaa2abde",  # removeLiquidity(address,address,bool,uint256,uint256,uint256,address,uint256)
        "0xcac88ea9",  # swapExactTokensForTokens - Aerodrome uses (address,address,bool,address)[] routes
    ],
    "cowswap_settlement": [
        "0x13d79a0b",  # settle
    ],
    "usdc": [
        "0x095ea7b3",  # approve(address,uint256)
        "0xa9059cbb",  # transfer(address,uint256)
    ],
    "weth": [
        "0x095ea7b3",  # approve(address,uint256)
        "0xd0e30db0",  # deposit()
        "0x2e1a7d4d",  # withdraw(uint256)
    ],
}

# Smart Account ABI (partial)
SMART_ACCOUNT_ABI = [
    {
        "inputs": [
            {"name": "protocols", "type": "address[]"},
            {"name": "selectors", "type": "bytes4[][]"}
        ],
        "name": "batchWhitelist",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "key", "type": "address"},
            {"name": "validUntil", "type": "uint48"},
            {"name": "dailyLimitUSD", "type": "uint256"}
        ],
        "name": "addSessionKey",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def setup_smart_account(smart_account_address: str, session_key_address: str):
    """
    Configure a Smart Account with protocol whitelists and session key.
    
    Must be called by the account owner.
    """
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    
    print(f"Setting up Smart Account: {smart_account_address}")
    print(f"Owner (caller): {account.address}")
    print(f"Session Key: {session_key_address}")
    
    # Get contract
    contract = w3.eth.contract(address=smart_account_address, abi=SMART_ACCOUNT_ABI)
    
    # Verify we're the owner
    owner = contract.functions.owner().call()
    if owner.lower() != account.address.lower():
        raise ValueError(f"Not the owner! Owner is {owner}")
    
    # Step 1: Batch whitelist protocols and selectors
    print("\n1. Whitelisting protocols...")
    
    protocol_addrs = []
    selector_lists = []
    
    for name, addr in PROTOCOLS.items():
        protocol_addrs.append(addr)
        selectors = [bytes.fromhex(s[2:]) for s in ALLOWED_SELECTORS.get(name, [])]
        selector_lists.append(selectors)
        print(f"   {name}: {addr} ({len(selectors)} selectors)")
    
    # Build and send tx
    tx = contract.functions.batchWhitelist(
        protocol_addrs,
        selector_lists
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 500000,
        "gasPrice": w3.eth.gas_price * 2,
        "chainId": 8453
    })
    
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"   TX: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"   Status: {'SUCCESS' if receipt['status'] == 1 else 'FAILED'}")
    
    # Step 2: Add session key
    print("\n2. Adding session key...")
    
    import time
    valid_until = int(time.time()) + (365 * 24 * 60 * 60)  # 1 year
    daily_limit_usd = 100000 * 10**8  # $100,000 daily limit (8 decimals)
    
    tx2 = contract.functions.addSessionKey(
        session_key_address,
        valid_until,
        daily_limit_usd
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 100000,
        "gasPrice": w3.eth.gas_price * 2,
        "chainId": 8453
    })
    
    signed2 = account.sign_transaction(tx2)
    tx_hash2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
    print(f"   TX: {tx_hash2.hex()}")
    receipt2 = w3.eth.wait_for_transaction_receipt(tx_hash2)
    print(f"   Status: {'SUCCESS' if receipt2['status'] == 1 else 'FAILED'}")
    
    print("\n✅ Smart Account setup complete!")
    print(f"   Session key {session_key_address} can now execute DeFi operations")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python setup_smart_account.py <smart_account_address> <session_key_address>")
        sys.exit(1)
    
    setup_smart_account(sys.argv[1], sys.argv[2])
