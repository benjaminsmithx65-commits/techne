"""
Generate raw calldata for addSessionKey transaction
User can paste this into MetaMask Send > Advanced > Hex data
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from eth_abi import encode
from api.session_key_signer import get_session_key_address
from web3 import Web3

# Agent info
AGENT_ID = "agent_1_1769892693"
USER_ADDRESS = "0xba9d6947c0ad6ea2aaa99507355cf83b4d098058"
SMART_ACCOUNT = "0x5E047DeB5eb22F4E4A7f2207087369468575e3EF"

# Get session key address
session_key_addr = get_session_key_address(AGENT_ID, USER_ADDRESS)

# Parameters
max_uint48 = (1 << 48) - 1  # No expiration
daily_limit = 100000 * 10**8  # $100,000 with 8 decimals

# Function selector for addSessionKey(address,uint48,uint256)
# keccak256("addSessionKey(address,uint48,uint256)")[:4]
selector = Web3.keccak(text="addSessionKey(address,uint48,uint256)")[:4]

# Encode parameters
params = encode(
    ['address', 'uint48', 'uint256'],
    [Web3.to_checksum_address(session_key_addr), max_uint48, daily_limit]
)

calldata = "0x" + selector.hex() + params.hex()

print("=" * 70)
print("ADD SESSION KEY - METAMASK TRANSACTION")
print("=" * 70)
print()
print(f"To:     {SMART_ACCOUNT}")
print(f"Value:  0")
print(f"Data:   {calldata}")
print()
print("=" * 70)
print("STEPS:")
print("=" * 70)
print("""
1. Open MetaMask
2. Click "Send"
3. Paste this address: """ + SMART_ACCOUNT + """
4. Amount: 0 ETH
5. Click "Hex data" / "Add data" (advanced)
6. Paste this calldata:
""")
print(calldata)
print()
print("7. Confirm and send the transaction")
print()
print(f"Session key to be registered: {session_key_addr}")
