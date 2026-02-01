"""Check implementation contract selectors"""
import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from web3 import Web3

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
IMPLEMENTATION = Web3.to_checksum_address("0xde70b3300f5fe05F4D698FEFe231cf8d874a6575")  # V3

w3 = Web3(Web3.HTTPProvider(RPC_URL))
code = w3.eth.get_code(IMPLEMENTATION).hex()

print(f"Implementation code length: {len(code)//2} bytes")
print()

# Compute actual selectors
from web3 import Web3 as W3
selectors = {
    "executeWithSessionKey(address,uint256,bytes,uint256,bytes)": W3.keccak(text="executeWithSessionKey(address,uint256,bytes,uint256,bytes)")[:4].hex(),
    "getSessionKeyCallHash(address,uint256,bytes)": W3.keccak(text="getSessionKeyCallHash(address,uint256,bytes)")[:4].hex(),
    "execute(address,uint256,bytes)": W3.keccak(text="execute(address,uint256,bytes)")[:4].hex(),
    "addSessionKey(address,uint48,uint256)": W3.keccak(text="addSessionKey(address,uint48,uint256)")[:4].hex(),
}

print("Checking function selectors in bytecode:")
for fn, selector in selectors.items():
    found = selector[2:].lower() in code.lower()  # Skip 0x
    status = "✅" if found else "❌"
    print(f"  {status} {fn.split('(')[0]}: {selector}")
