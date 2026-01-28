"""
Step by step LP - USDC approve only
"""
from web3 import Web3
from eth_account import Account
from services.agent_keys import decrypt_private_key
from api.agent_config_router import DEPLOYED_AGENTS

AGENT_ADDR = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
ROUTER = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43'

w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

ERC20_ABI = [{'inputs':[{'name':'spender','type':'address'},{'name':'amount','type':'uint256'}],'name':'approve','outputs':[{'type':'bool'}],'stateMutability':'nonpayable','type':'function'},{'inputs':[{'name':'account','type':'address'}],'name':'balanceOf','outputs':[{'type':'uint256'}],'stateMutability':'view','type':'function'}]

usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ERC20_ABI)

agent = DEPLOYED_AGENTS.get('0xba9d6947c0ad6ea2aaa99507355cf83b4d098058'.lower(), [])[0]
pk = decrypt_private_key(agent.get('encrypted_private_key'))
account = Account.from_key(pk)

usdc_bal = usdc.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
nonce = w3.eth.get_transaction_count(account.address, 'latest')
print(f'USDC: {usdc_bal / 1e6:.6f}, Nonce: {nonce}')

tx = usdc.functions.approve(ROUTER, usdc_bal).build_transaction({
    'from': account.address,
    'nonce': nonce,
    'gas': 60000,
    'maxFeePerGas': w3.to_wei(10, 'gwei'),  # Much higher
    'maxPriorityFeePerGas': w3.to_wei(2, 'gwei'),
    'chainId': 8453
})
signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f'TX: {tx_hash.hex()}')
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
print(f'Status: OK' if receipt.status == 1 else 'FAIL')
