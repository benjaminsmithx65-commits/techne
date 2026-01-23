"""FINAL RECOVERY - Aave withdraw via executeRebalance"""
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_abi import encode
load_dotenv()

OLD = Web3.to_checksum_address('0x323f98c4e05073c2f76666944d95e39b78024efd')
AAVE = Web3.to_checksum_address('0xA238Dd80C259a72e81d7e4664a9801593F98d1c5')
USER = Web3.to_checksum_address('0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058')
USDC = Web3.to_checksum_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')

w3 = Web3(Web3.HTTPProvider('https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb'))
acct = Account.from_key(os.getenv('PRIVATE_KEY'))

ABI = [
    {'inputs':[{'name':'u','type':'address'},{'name':'p','type':'address'},{'name':'d','type':'bytes'}],'name':'executeRebalance','outputs':[{'type':'bool'}],'stateMutability':'nonpayable','type':'function'},
    {'inputs':[{'name':'u','type':'address'},{'name':'p','type':'address'}],'name':'investments','outputs':[{'type':'uint256'}],'stateMutability':'view','type':'function'},
    {'inputs':[{'name':'u','type':'address'}],'name':'balances','outputs':[{'type':'uint256'}],'stateMutability':'view','type':'function'},
]
c = w3.eth.contract(address=OLD, abi=ABI)

# Build withdraw calldata: withdraw(USDC, max, OLD_CONTRACT)
selector = bytes.fromhex('69328dec')
data = selector + encode(['address', 'uint256', 'address'], [USDC, 2**256-1, OLD])

print('BEFORE:')
print(f'  investments: {c.functions.investments(USER, AAVE).call() / 1e6} USDC')
print(f'  balances: {c.functions.balances(USER).call() / 1e6} USDC')

print('\nExecuting Aave withdraw via executeRebalance...')
nonce = w3.eth.get_transaction_count(acct.address, 'pending')
tx = c.functions.executeRebalance(USER, AAVE, data).build_transaction({
    'from': acct.address, 'nonce': nonce, 'gas': 400000, 'gasPrice': w3.eth.gas_price * 2
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f'TX: {tx_hash.hex()}')
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

if receipt.status == 1:
    print('Status: SUCCESS!')
else:
    print('Status: FAILED')

print('\nAFTER:')
print(f'  investments: {c.functions.investments(USER, AAVE).call() / 1e6} USDC')
print(f'  balances: {c.functions.balances(USER).call() / 1e6} USDC')
print('\nDone! Check BaseScan for details.')
