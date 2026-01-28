"""
Swap cbBTC -> USDC using EIP-1559
"""
from web3 import Web3
from eth_account import Account
from services.agent_keys import decrypt_private_key
from api.agent_config_router import DEPLOYED_AGENTS
import time

# Config
AGENT_ADDR = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
ROUTER = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43'
FACTORY = '0x420DD381b31aEf6683db6B902084cB0FFECe40Da'

w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

ROUTER_ABI = [{'inputs':[{'name':'amountIn','type':'uint256'},{'name':'amountOutMin','type':'uint256'},{'components':[{'name':'from','type':'address'},{'name':'to','type':'address'},{'name':'stable','type':'bool'},{'name':'factory','type':'address'}],'name':'routes','type':'tuple[]'},{'name':'to','type':'address'},{'name':'deadline','type':'uint256'}],'name':'swapExactTokensForTokens','outputs':[{'name':'amounts','type':'uint256[]'}],'stateMutability':'nonpayable','type':'function'}]

router = w3.eth.contract(address=Web3.to_checksum_address(ROUTER), abi=ROUTER_ABI)

# Load key
agent = DEPLOYED_AGENTS.get('0xba9d6947c0ad6ea2aaa99507355cf83b4d098058'.lower(), [])[0]
pk = decrypt_private_key(agent.get('encrypted_private_key'))
account = Account.from_key(pk)

# Get balance
cbbtc_bal = int(w3.eth.call({'to': Web3.to_checksum_address(CBBTC), 'data': '0x70a08231' + AGENT_ADDR[2:].lower().zfill(64)}).hex(), 16)
half = cbbtc_bal // 2
print(f'Swapping {half / 1e8:.8f} cbBTC')

# Build swap TX
deadline = int(time.time()) + 1200
routes = [(Web3.to_checksum_address(CBBTC), Web3.to_checksum_address(USDC), False, Web3.to_checksum_address(FACTORY))]

call = router.functions.swapExactTokensForTokens(half, 0, routes, account.address, deadline)
tx = call.build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address, 'pending'),
    'gas': 300000,
    'maxFeePerGas': w3.to_wei(1, 'gwei'),
    'maxPriorityFeePerGas': w3.to_wei(0.1, 'gwei'),
    'chainId': 8453
})

signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f'TX: {tx_hash.hex()}')
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
status = 'OK' if receipt.status == 1 else 'FAILED'
print(f'Status: {status}')
print(f'https://basescan.org/tx/{tx_hash.hex()}')
