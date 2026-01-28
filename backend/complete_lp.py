"""
Complete LP: approve + addLiquidity with higher gas
"""
from web3 import Web3
from eth_account import Account
from services.agent_keys import decrypt_private_key
from api.agent_config_router import DEPLOYED_AGENTS
import time

AGENT_ADDR = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
ROUTER = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43'

w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

ERC20_ABI = [{'inputs':[{'name':'spender','type':'address'},{'name':'amount','type':'uint256'}],'name':'approve','outputs':[{'type':'bool'}],'stateMutability':'nonpayable','type':'function'},{'inputs':[{'name':'account','type':'address'}],'name':'balanceOf','outputs':[{'type':'uint256'}],'stateMutability':'view','type':'function'}]

ROUTER_ABI = [{'inputs':[{'name':'tokenA','type':'address'},{'name':'tokenB','type':'address'},{'name':'stable','type':'bool'},{'name':'amountADesired','type':'uint256'},{'name':'amountBDesired','type':'uint256'},{'name':'amountAMin','type':'uint256'},{'name':'amountBMin','type':'uint256'},{'name':'to','type':'address'},{'name':'deadline','type':'uint256'}],'name':'addLiquidity','outputs':[{'name':'amountA','type':'uint256'},{'name':'amountB','type':'uint256'},{'name':'liquidity','type':'uint256'}],'stateMutability':'nonpayable','type':'function'}]

cbbtc = w3.eth.contract(address=Web3.to_checksum_address(CBBTC), abi=ERC20_ABI)
usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ERC20_ABI)
router = w3.eth.contract(address=Web3.to_checksum_address(ROUTER), abi=ROUTER_ABI)

agent = DEPLOYED_AGENTS.get('0xba9d6947c0ad6ea2aaa99507355cf83b4d098058'.lower(), [])[0]
pk = decrypt_private_key(agent.get('encrypted_private_key'))
account = Account.from_key(pk)

cbbtc_bal = cbbtc.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
usdc_bal = usdc.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
print(f'cbBTC: {cbbtc_bal / 1e8:.8f}, USDC: {usdc_bal / 1e6:.6f}')

def send_tx(contract_call, gas=100000):
    nonce = w3.eth.get_transaction_count(account.address, 'latest')
    tx = contract_call.build_transaction({
        'from': account.address, 'nonce': nonce, 'gas': gas,
        'maxFeePerGas': w3.to_wei(5, 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei(1, 'gwei'),
        'chainId': 8453
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    short_hash = tx_hash.hex()[:20]
    print(f'TX: {short_hash}... nonce={nonce}')
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    status = 'OK' if receipt.status == 1 else 'FAIL'
    print(f'Status: {status}')
    return receipt.status == 1, tx_hash.hex()

# Approve cbBTC
print('Approve cbBTC...')
send_tx(cbbtc.functions.approve(ROUTER, cbbtc_bal), 60000)

# Approve USDC
print('Approve USDC...')
send_tx(usdc.functions.approve(ROUTER, usdc_bal), 60000)

# addLiquidity
print('addLiquidity...')
deadline = int(time.time()) + 1200
ok, tx = send_tx(router.functions.addLiquidity(CBBTC, USDC, False, cbbtc_bal, usdc_bal, 0, 0, account.address, deadline), 400000)

if ok:
    print(f'SUCCESS! https://basescan.org/tx/{tx}')
else:
    print('FAILED')
