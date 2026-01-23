"""Approve USDC and transfer to user"""
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from eth_abi import encode
load_dotenv()

OLD = Web3.to_checksum_address('0x323f98c4e05073c2f76666944d95e39b78024efd')
USER = Web3.to_checksum_address('0xbA9D6947C0aD6eA2AaA99507355cf83B4D098058')
USDC = Web3.to_checksum_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')

w3 = Web3(Web3.HTTPProvider('https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb'))
acct = Account.from_key(os.getenv('PRIVATE_KEY'))

# Check USDC balance
USDC_ABI = [{'inputs':[{'name':'a','type':'address'}],'name':'balanceOf','outputs':[{'type':'uint256'}],'stateMutability':'view','type':'function'}]
usdc_token = w3.eth.contract(address=USDC, abi=USDC_ABI)
balance = usdc_token.functions.balanceOf(OLD).call()
print(f'Contract USDC balance: {balance / 1e6}')
print(f'User USDC before: {usdc_token.functions.balanceOf(USER).call() / 1e6}')

# Step 1: Approve USDC as protocol (if not already)
APPROVE_CHECK = [{'inputs':[{'name':'p','type':'address'}],'name':'approvedProtocols','outputs':[{'type':'bool'}],'stateMutability':'view','type':'function'}]
c_check = w3.eth.contract(address=OLD, abi=APPROVE_CHECK)
if not c_check.functions.approvedProtocols(USDC).call():
    print('\nApproving USDC as protocol...')
    APPROVE_ABI = [{'inputs':[{'name':'p','type':'address'},{'name':'a','type':'bool'},{'name':'l','type':'bool'}],'name':'approveProtocol','outputs':[],'stateMutability':'nonpayable','type':'function'}]
    c = w3.eth.contract(address=OLD, abi=APPROVE_ABI)
    nonce = w3.eth.get_transaction_count(acct.address, 'pending')
    tx = c.functions.approveProtocol(USDC, True, False).build_transaction({
        'from': acct.address, 'nonce': nonce, 'gas': 100000, 'gasPrice': w3.eth.gas_price * 2
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f'TX: {tx_hash.hex()}')
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print('Approve OK!')
    else:
        print('Approve FAILED')
        exit(1)
else:
    print('USDC already approved as protocol')

# Step 2: Transfer via executeRebalance
print('\nTransferring USDC to user...')
EXEC_ABI = [{'inputs':[{'name':'u','type':'address'},{'name':'p','type':'address'},{'name':'d','type':'bytes'}],'name':'executeRebalance','outputs':[{'type':'bool'}],'stateMutability':'nonpayable','type':'function'}]
c2 = w3.eth.contract(address=OLD, abi=EXEC_ABI)

# transfer(address,uint256) = 0xa9059cbb
selector = bytes.fromhex('a9059cbb')
data = selector + encode(['address', 'uint256'], [USER, balance])

nonce = w3.eth.get_transaction_count(acct.address, 'pending')
tx = c2.functions.executeRebalance(USER, USDC, data).build_transaction({
    'from': acct.address, 'nonce': nonce, 'gas': 200000, 'gasPrice': w3.eth.gas_price * 2
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f'TX: {tx_hash.hex()}')
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
if receipt.status == 1:
    print('Transfer SUCCESS!')
else:
    print('Transfer FAILED')

print(f'\nFinal balances:')
print(f'Contract USDC: {usdc_token.functions.balanceOf(OLD).call() / 1e6}')
print(f'User USDC: {usdc_token.functions.balanceOf(USER).call() / 1e6}')
