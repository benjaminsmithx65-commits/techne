"""Check contract roles"""
import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

TECHNE_WALLET = "0x323f98c4e05073c2f76666944d95e39b78024efd"
AGENT_ROLE = Web3.keccak(text="AGENT_ROLE")

w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

ABI = [
    {"inputs": [{"name": "role", "type": "bytes32"}, {"name": "account", "type": "address"}], "name": "hasRole", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
]

contract = w3.eth.contract(address=Web3.to_checksum_address(TECHNE_WALLET), abi=ABI)

# Check various addresses
AGENT_EXECUTOR = Web3.to_checksum_address("0xEe95B8114b144f48A742BA96Dc6c167a35829Fe1")
AGENT_CONTRACT = Web3.to_checksum_address("0x1bba1860fe4f300ed5534bcf6fc807d298ba7dc3")

print(f"AGENT_ROLE: {AGENT_ROLE.hex()}")
print(f"Agent executor ({AGENT_EXECUTOR}) has AGENT_ROLE: {contract.functions.hasRole(AGENT_ROLE, AGENT_EXECUTOR).call()}")
print(f"Agent contract ({AGENT_CONTRACT}) has AGENT_ROLE: {contract.functions.hasRole(AGENT_ROLE, AGENT_CONTRACT).call()}")

# Check admin role
DEFAULT_ADMIN = bytes(32)
print(f"Agent executor has DEFAULT_ADMIN_ROLE: {contract.functions.hasRole(DEFAULT_ADMIN, AGENT_EXECUTOR).call()}")
