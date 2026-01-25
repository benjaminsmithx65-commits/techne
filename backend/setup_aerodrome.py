"""
Setup Aerodrome on new TechneAgentWalletV43

1. Approve Aerodrome Router as protocol
2. Whitelist swapExactTokensForTokens selector
3. Whitelist addLiquidity selector
"""

import os
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv
import time

# Load .env
load_dotenv(Path(__file__).parent / ".env")

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# NEW V4.3 Contract
TECHNE_WALLET = "0x1ff18a7b56d7fd3b07ce789e47ac587de2f14e0d"
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"

# Selectors to whitelist
SELECTORS = {
    "swapExactTokensForTokens": "0xcac88ea9",
    "addLiquidity": "0x5a47ddc3",
}

WALLET_ABI = [
    {
        "inputs": [{"name": "protocol", "type": "address"}, {"name": "approved", "type": "bool"}, {"name": "_isLending", "type": "bool"}],
        "name": "approveProtocol",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "protocol", "type": "address"}, {"name": "selector", "type": "bytes4"}, {"name": "allowed", "type": "bool"}],
        "name": "setAllowedSelector",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "approvedProtocols",
        "outputs": [{"type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "address"}, {"name": "", "type": "bytes4"}],
        "name": "allowedSelectors",
        "outputs": [{"type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def send_tx(w3, account, tx_data, description):
    """Send transaction with EIP-1559"""
    base_fee = w3.eth.get_block('latest')['baseFeePerGas']
    priority_fee = w3.to_wei(0.1, 'gwei')
    
    tx = tx_data.build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 150000,
        "maxFeePerGas": base_fee * 2 + priority_fee,
        "maxPriorityFeePerGas": priority_fee,
        "chainId": 8453
    })
    
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"   TX: {tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    status = "✅ SUCCESS" if receipt['status'] == 1 else "❌ FAILED"
    print(f"   Status: {status}")
    return receipt['status'] == 1


def main():
    print("=" * 60)
    print("🔧 Setup Aerodrome on TechneAgentWalletV43")
    print("=" * 60)
    
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    
    print(f"\n📍 Contract: {TECHNE_WALLET}")
    print(f"👤 Admin: {account.address}")
    print(f"🔄 Router: {AERODROME_ROUTER}")
    
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(TECHNE_WALLET),
        abi=WALLET_ABI
    )
    
    # Step 1: Check if protocol is approved
    is_approved = contract.functions.approvedProtocols(
        Web3.to_checksum_address(AERODROME_ROUTER)
    ).call()
    print(f"\n🔍 Protocol approved: {is_approved}")
    
    if not is_approved:
        print("\n📝 Step 1: Approving Aerodrome Router...")
        tx_data = contract.functions.approveProtocol(
            Web3.to_checksum_address(AERODROME_ROUTER),
            True,
            False  # is_lending = false
        )
        if not send_tx(w3, account, tx_data, "approveProtocol"):
            print("❌ Failed to approve protocol!")
            return
        time.sleep(2)  # Wait for state to update
    else:
        print("✅ Protocol already approved")
    
    # Step 2: Whitelist selectors
    for name, selector in SELECTORS.items():
        selector_bytes = bytes.fromhex(selector[2:])
        
        is_whitelisted = contract.functions.allowedSelectors(
            Web3.to_checksum_address(AERODROME_ROUTER),
            selector_bytes
        ).call()
        
        if is_whitelisted:
            print(f"✅ {name} ({selector}) already whitelisted")
            continue
        
        print(f"\n📝 Whitelisting {name} ({selector})...")
        tx_data = contract.functions.setAllowedSelector(
            Web3.to_checksum_address(AERODROME_ROUTER),
            selector_bytes,
            True
        )
        if not send_tx(w3, account, tx_data, f"whitelist {name}"):
            print(f"❌ Failed to whitelist {name}!")
            continue
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print("🎉 Aerodrome setup complete!")
    print(f"   Contract: {TECHNE_WALLET}")
    print(f"   Router: {AERODROME_ROUTER}")
    print("=" * 60)


if __name__ == "__main__":
    main()
