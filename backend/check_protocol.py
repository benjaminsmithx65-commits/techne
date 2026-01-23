"""Check protocol status"""
from web3 import Web3

TECHNE_WALLET = Web3.to_checksum_address("0x323f98c4e05073c2f76666944d95e39b78024efd")
AAVE_POOL = Web3.to_checksum_address("0xA238Dd80C259a72e81d7e4664a9801593F98d1c5")

w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

ABI = [
    {"inputs": [{"name": "protocol", "type": "address"}], "name": "isLendingProtocol", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "protocol", "type": "address"}], "name": "approvedProtocols", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
]

contract = w3.eth.contract(address=TECHNE_WALLET, abi=ABI)

is_lending = contract.functions.isLendingProtocol(AAVE_POOL).call()
is_approved = contract.functions.approvedProtocols(AAVE_POOL).call()

print(f"AAVE_POOL: {AAVE_POOL}")
print(f"isLendingProtocol: {is_lending}")
print(f"approvedProtocols: {is_approved}")

if not is_lending:
    print("\n⚠️ AAVE_POOL is NOT marked as lending protocol!")
    print("emergencyDeleverage requires isLendingProtocol[lendingProtocol] == true")
