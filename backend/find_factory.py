import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

w = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))
deployer = "0xa30A689ec0F9D717C5bA1098455B031b868B720f"

print(f"Connected: {w.is_connected()}")
nonce = w.eth.get_transaction_count(deployer)
print(f"Current nonce: {nonce}")

# Calculate contract addresses for recent nonces
import rlp

def get_contract_address(sender, nonce):
    sender_bytes = bytes.fromhex(sender[2:])
    raw = rlp.encode([sender_bytes, nonce])
    addr = w.keccak(raw)[12:]
    return w.to_checksum_address(addr.hex())

print("\nRecent deployments:")
for n in range(60, nonce + 1):
    addr = get_contract_address(deployer, n)
    code = w.eth.get_code(addr)
    has_code = len(code) > 2
    print(f"  Nonce {n}: {addr} {'[CONTRACT]' if has_code else ''}")
