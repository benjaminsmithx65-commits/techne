"""Check user investments in contract"""
from web3 import Web3

TECHNE_WALLET = Web3.to_checksum_address("0x323f98c4e05073c2f76666944d95e39b78024efd")
AAVE_POOL = Web3.to_checksum_address("0xA238Dd80C259a72e81d7e4664a9801593F98d1c5")
USER = Web3.to_checksum_address("0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058")

w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

ABI = [
    {"inputs": [{"name": "user", "type": "address"}], "name": "balances", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "user", "type": "address"}], "name": "totalInvested", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "user", "type": "address"}, {"name": "protocol", "type": "address"}], "name": "investments", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
]

contract = w3.eth.contract(address=TECHNE_WALLET, abi=ABI)

balance = contract.functions.balances(USER).call()
total_invested = contract.functions.totalInvested(USER).call()
aave_investment = contract.functions.investments(USER, AAVE_POOL).call()

print(f"User: {USER}")
print(f"Idle balance: {balance / 1e6} USDC")
print(f"Total invested: {total_invested / 1e6} USDC")
print(f"Aave investment: {aave_investment / 1e6} USDC")

if aave_investment == 0:
    print("\n⚠️ User has NO recorded investment in Aave in the contract!")
    print("The $10 showing in UI may be from Supabase, not on-chain.")
