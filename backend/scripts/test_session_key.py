"""
Direct test of session key execution with approve.
Simulates what strategy_executor does.
"""
import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from web3 import Web3
from eth_account import Account
from artisan.aerodrome_dual import AerodromeDualLPBuilder, AERODROME_ROUTER, TOKENS

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
BACKEND_PK = os.getenv("PRIVATE_KEY")
SMART_ACCOUNT = "0x8bfb3693E1d09e9C2F07Fb59A75120ED3B4617f5"

print("=== DIRECT SESSION KEY TEST ===")
print()

w3 = Web3(Web3.HTTPProvider(RPC_URL))
backend = Account.from_key(BACKEND_PK)

print(f"Backend signer: {backend.address}")
print(f"Smart Account: {SMART_ACCOUNT}")
print()

# Build approve calldata
builder = AerodromeDualLPBuilder()
usdc_amount = 1 * 10**6  # $1 USDC
approve_calldata = builder.build_approve_calldata("USDC", AERODROME_ROUTER, usdc_amount)

# Handle both bytes and HexBytes
if hasattr(approve_calldata, 'hex'):
    calldata_hex = approve_calldata.hex()
else:
    calldata_hex = approve_calldata if isinstance(approve_calldata, str) else str(approve_calldata)

print(f"Target (USDC): {TOKENS['USDC']}")
print(f"Approve calldata: {calldata_hex[:80]}...")
print()

# Test the contract call manually
ACCOUNT_ABI = [
    {
        "name": "getSessionKeyCallHash",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"}
        ],
        "outputs": [{"name": "", "type": "bytes32"}]
    },
    {
        "name": "executeWithSessionKey",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
            {"name": "estimatedValueUSD", "type": "uint256"},
            {"name": "signature", "type": "bytes"}
        ],
        "outputs": [{"name": "", "type": "bytes"}]
    }
]

contract = w3.eth.contract(
    address=Web3.to_checksum_address(SMART_ACCOUNT),
    abi=ACCOUNT_ABI
)

try:
    # Get call hash
    call_hash = contract.functions.getSessionKeyCallHash(
        Web3.to_checksum_address(TOKENS["USDC"]),
        0,
        approve_calldata
    ).call()
    print(f"✅ Call hash: {call_hash.hex()}")
    
    # Sign with session key
    from eth_account.messages import encode_defunct
    message = encode_defunct(call_hash)
    signature = backend.sign_message(message)
    print(f"✅ Signature: {signature.signature.hex()[:40]}...")
    
    # Estimate gas
    print("\nEstimating gas...")
    
    tx = contract.functions.executeWithSessionKey(
        Web3.to_checksum_address(TOKENS["USDC"]),
        0,
        approve_calldata,
        0,  # estimatedValueUSD
        signature.signature
    ).build_transaction({
        "from": backend.address,
        "nonce": w3.eth.get_transaction_count(backend.address),
        "gas": 500000,
        "maxFeePerGas": w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(0.01, 'gwei'),
        "chainId": 8453
    })
    
    try:
        estimate = w3.eth.estimate_gas(tx)
        print(f"✅ Gas estimate: {estimate}")
        print()
        print("Ready to send transaction!")
    except Exception as e:
        print(f"❌ Gas estimate failed: {e}")
        print()
        print("This means the transaction would revert.")
        print("Possible reasons:")
        print("1. Session key not registered for this address")
        print("2. Target not whitelisted")
        print("3. Signature verification fails")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
