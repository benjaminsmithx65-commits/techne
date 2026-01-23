"""Check aUSDC balance of Techne contract"""
from web3 import Web3

TECHNE_WALLET = Web3.to_checksum_address("0x323f98c4e05073c2f76666944d95e39b78024efd")
# Base Aave aUSDC token
AUSDC = Web3.to_checksum_address("0x4e65fE4DbA92790696d040ac24Aa414708D1C66E")

# Use different RPC
w3 = Web3(Web3.HTTPProvider("https://base-mainnet.g.alchemy.com/v2/demo"))

ABI = [{"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}]
ausdc = w3.eth.contract(address=AUSDC, abi=ABI)

balance = ausdc.functions.balanceOf(TECHNE_WALLET).call()
print(f"Techne contract aUSDC balance: {balance / 1e6} USDC")

if balance > 0:
    print("✅ Kontrakt MA aUSDC - można zrobić withdraw!")
else:
    print("❌ Kontrakt nie ma aUSDC")
