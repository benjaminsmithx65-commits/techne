"""Find recently deployed contracts"""
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
import rlp

load_dotenv()

w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
deployer = "0xa30A689ec0F9D717C5bA1098455B031b868B720f"

# Calculate contract addresses for recent nonces
print(f"Deployer: {deployer}")
print(f"Current nonce: {w3.eth.get_transaction_count(deployer)}")
print("\nRecent contract deployments:")

for nonce in range(58, 64):
    # Contract address = keccak256(rlp([sender, nonce]))[12:]
    encoded = rlp.encode([bytes.fromhex(deployer[2:]), nonce])
    contract_addr = Web3.keccak(encoded)[-20:]
    addr = Web3.to_checksum_address("0x" + contract_addr.hex())
    
    # Check if it's a contract
    code = w3.eth.get_code(addr)
    is_contract = len(code) > 0
    
    print(f"  Nonce {nonce}: {addr} {'✅ CONTRACT' if is_contract else ''}")
