"""
Whitelist Aerodrome swapExactTokensForTokens selector on TechneAgentWallet

This script calls setAllowedSelector() to whitelist the correct Aerodrome swap selector.
Aerodrome uses Route[] struct which gives different selector than Uniswap V2.

Run with: python whitelist_aerodrome_swap.py
"""

import os
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv

# Load .env from script directory
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"Loaded .env from: {env_path}")

# ============================================
# CONFIGURATION
# ============================================

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb")
PRIVATE_KEY = os.getenv("PRIVATE_KEY") or os.getenv("AGENT_PRIVATE_KEY")

# TechneAgentWallet V4.3 on Base (deployed 2026-01-25)
TECHNE_WALLET = "0x1ff18a7b56d7fd3b07ce789e47ac587de2f14e0d"

# Aerodrome Router on Base
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"

# Selector for swapExactTokensForTokens with Aerodrome's Route[] struct
# Signature: swapExactTokensForTokens(uint256,uint256,(address,address,bool,address)[],address,uint256)
AERODROME_SWAP_SELECTOR = "0xcac88ea9"

# Minimal ABI for setAllowedSelector
WALLET_ABI = [
    {
        "inputs": [
            {"name": "protocol", "type": "address"},
            {"name": "selector", "type": "bytes4"},
            {"name": "allowed", "type": "bool"}
        ],
        "name": "setAllowedSelector",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "", "type": "address"},
            {"name": "", "type": "bytes4"}
        ],
        "name": "allowedSelectors",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "protocol", "type": "address"},
            {"name": "approved", "type": "bool"},
            {"name": "_isLending", "type": "bool"}
        ],
        "name": "approveProtocol",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "approvedProtocols",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def main():
    print("=" * 60)
    print("🔐 Whitelist Aerodrome Swap Selector")
    print("=" * 60)
    
    if not RPC_URL or not PRIVATE_KEY:
        print("❌ Error: ALCHEMY_RPC_URL and PRIVATE_KEY must be set in .env")
        return
    
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    
    print(f"\n📍 Network: Base (chainId {w3.eth.chain_id})")
    print(f"👤 Caller: {account.address}")
    print(f"📜 Contract: {TECHNE_WALLET}")
    print(f"🔄 Router: {AERODROME_ROUTER}")
    print(f"🔢 Selector: {AERODROME_SWAP_SELECTOR}")
    
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(TECHNE_WALLET),
        abi=WALLET_ABI
    )
    
    # Check if protocol is approved (optional - may fail on some contract versions)
    try:
        is_approved = contract.functions.approvedProtocols(
            Web3.to_checksum_address(AERODROME_ROUTER)
        ).call()
        print(f"\n🔍 Protocol approved: {is_approved}")
    except Exception as e:
        print(f"\n⚠️ Could not check approvedProtocols: {e}")
        is_approved = None
    
    # Check current selector status
    try:
        selector_bytes = bytes.fromhex(AERODROME_SWAP_SELECTOR[2:])
        is_whitelisted = contract.functions.allowedSelectors(
            Web3.to_checksum_address(AERODROME_ROUTER),
            selector_bytes
        ).call()
        print(f"🔍 Selector whitelisted: {is_whitelisted}")
        
        if is_whitelisted:
            print("\n✅ Selector already whitelisted! No action needed.")
            return
    except Exception as e:
        print(f"⚠️ Could not check allowedSelectors: {e}")
        is_whitelisted = False
        selector_bytes = bytes.fromhex(AERODROME_SWAP_SELECTOR[2:])
        print(f"\n📝 Step 1: Approving Aerodrome Router as protocol...")
        
        tx1 = contract.functions.approveProtocol(
            Web3.to_checksum_address(AERODROME_ROUTER),
            True,   # approved
            False   # is_lending = false (LP protocol)
        ).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 100000,
            "gasPrice": int(w3.eth.gas_price * 1.5),  # 50% higher to avoid underpriced
            "chainId": 8453
        })
        
        signed1 = account.sign_transaction(tx1)
        tx_hash1 = w3.eth.send_raw_transaction(signed1.raw_transaction)
        print(f"   TX: {tx_hash1.hex()}")
        receipt1 = w3.eth.wait_for_transaction_receipt(tx_hash1)
        print(f"   Status: {'✅ SUCCESS' if receipt1['status'] == 1 else '❌ FAILED'}")
        
        if receipt1['status'] != 1:
            print("❌ Failed to approve protocol. Aborting.")
            return
    else:
        print("\n✅ Step 1: Protocol already approved, skipping...")
    
    # Step 2: Whitelist selector
    print(f"\n📝 Step 2: Whitelisting swap selector...")
    
    # Get latest gas prices
    base_fee = w3.eth.get_block('latest')['baseFeePerGas']
    priority_fee = w3.to_wei(0.1, 'gwei')  # 0.1 gwei tip
    max_fee = base_fee * 2 + priority_fee
    
    tx2 = contract.functions.setAllowedSelector(
        Web3.to_checksum_address(AERODROME_ROUTER),
        selector_bytes,
        True  # allowed
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 100000,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
        "chainId": 8453
    })
    
    signed2 = account.sign_transaction(tx2)
    tx_hash2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
    print(f"   TX: {tx_hash2.hex()}")
    receipt2 = w3.eth.wait_for_transaction_receipt(tx_hash2)
    print(f"   Status: {'✅ SUCCESS' if receipt2['status'] == 1 else '❌ FAILED'}")
    
    if receipt2['status'] == 1:
        print(f"\n🎉 Done! Aerodrome swapExactTokensForTokens is now whitelisted.")
        print(f"   BaseScan: https://basescan.org/tx/{tx_hash2.hex()}")
    else:
        print("\n❌ Failed to whitelist selector.")


if __name__ == "__main__":
    main()
