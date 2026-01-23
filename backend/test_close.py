"""Test emergencyDeleverage with PRIVATE_KEY"""
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

# Use PRIVATE_KEY which should have AGENT_ROLE
agent_key = os.getenv("PRIVATE_KEY")
print(f"Using PRIVATE_KEY: {bool(agent_key)}")

TECHNE_WALLET = "0x323f98c4e05073c2f76666944d95e39b78024efd"
AAVE_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
USER_ADDRESS = "0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058"

w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
print(f"Connected: {w3.is_connected()}")

account = Account.from_key(agent_key)
print(f"Signer address: {account.address}")

# Check ETH balance
eth_balance = w3.eth.get_balance(account.address)
print(f"Signer ETH: {eth_balance / 1e18:.6f}")

# Check if this address has AGENT_ROLE
AGENT_ROLE = Web3.keccak(text="AGENT_ROLE")
ABI_HAS_ROLE = [{"inputs": [{"name": "role", "type": "bytes32"}, {"name": "account", "type": "address"}], "name": "hasRole", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"}]
contract_check = w3.eth.contract(address=Web3.to_checksum_address(TECHNE_WALLET), abi=ABI_HAS_ROLE)
has_role = contract_check.functions.hasRole(AGENT_ROLE, account.address).call()
print(f"Has AGENT_ROLE: {has_role}")

if not has_role:
    print("ERROR: This key does NOT have AGENT_ROLE!")
    exit(1)

# emergencyDeleverage ABI
ABI = [{
    "inputs": [
        {"name": "user", "type": "address"},
        {"name": "lendingProtocol", "type": "address"},
        {"name": "debtToRepay", "type": "uint256"}
    ],
    "name": "emergencyDeleverage",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
}]

contract = w3.eth.contract(
    address=Web3.to_checksum_address(TECHNE_WALLET),
    abi=ABI
)

print("Trying to estimate gas...")

try:
    gas_estimate = contract.functions.emergencyDeleverage(
        Web3.to_checksum_address(USER_ADDRESS),
        Web3.to_checksum_address(AAVE_POOL),
        1  # 1 wei
    ).estimate_gas({'from': account.address})
    print(f"✅ Gas estimate: {gas_estimate}")
except Exception as e:
    print(f"❌ Gas estimation failed: {e}")
