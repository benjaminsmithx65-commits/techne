"""Check what functions exist in deployed smart account"""
import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from web3 import Web3

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
SMART_ACCOUNT = "0x8bfb3693E1d09e9C2F07Fb59A75120ED3B4617f5"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Get bytecode
code = w3.eth.get_code(SMART_ACCOUNT)
code_hex = code.hex()

print(f"Contract code length: {len(code)} bytes")
print()

# Check for known function selectors
selectors = {
    "executeWithSessionKey": "9914a946",  # Guess - need to compute actual
    "getSessionKeyCallHash": "f1da9a90",  # Guess  
    "execute": "b61d27f6",
    "addSessionKey": "73a0c609",
    "getSessionKeyInfo": "9c52c4a4",
}

print("Checking function selectors in bytecode:")
for name, selector in selectors.items():
    found = selector.lower() in code_hex.lower()
    status = "✅" if found else "❌"
    print(f"  {status} {name}: {selector}")
