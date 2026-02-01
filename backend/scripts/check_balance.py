"""Check remaining ETH balance"""
import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from web3 import Web3

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
DEPLOYER = "0xa30A689ec0F9D717C5bA1098455B031b868B720f"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
bal = w3.eth.get_balance(DEPLOYER)
eth = w3.from_wei(bal, 'ether')
print(f"Remaining balance: {eth} ETH")
print(f"~ ${float(eth) * 3000:.2f} USD")
