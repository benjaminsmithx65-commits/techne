"""
Continue LP: Swap cbBTC->USDC (approve done), then addLiquidity
"""
from web3 import Web3
from eth_account import Account
from services.agent_keys import decrypt_private_key
from api.agent_config_router import DEPLOYED_AGENTS
import time

# Config
AGENT_ADDR = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
ROUTER = '0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43'
FACTORY = '0x420DD381b31aEf6683db6B902084cB0FFECe40Da'

w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

# ABIs
ERC20_ABI = [{"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"}]

ROUTER_ABI = [
    {"inputs":[{"name":"amountIn","type":"uint256"},{"name":"amountOutMin","type":"uint256"},{"components":[{"name":"from","type":"address"},{"name":"to","type":"address"},{"name":"stable","type":"bool"},{"name":"factory","type":"address"}],"name":"routes","type":"tuple[]"},{"name":"to","type":"address"},{"name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"name":"tokenA","type":"address"},{"name":"tokenB","type":"address"},{"name":"stable","type":"bool"},{"name":"amountADesired","type":"uint256"},{"name":"amountBDesired","type":"uint256"},{"name":"amountAMin","type":"uint256"},{"name":"amountBMin","type":"uint256"},{"name":"to","type":"address"},{"name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"name":"amountA","type":"uint256"},{"name":"amountB","type":"uint256"},{"name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}
]

# Contracts
cbbtc_contract = w3.eth.contract(address=Web3.to_checksum_address(CBBTC), abi=ERC20_ABI)
usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ERC20_ABI)
router = w3.eth.contract(address=Web3.to_checksum_address(ROUTER), abi=ROUTER_ABI)

# Load private key
agent = DEPLOYED_AGENTS.get('0xba9d6947c0ad6ea2aaa99507355cf83b4d098058'.lower(), [])[0]
encrypted_pk = agent.get('encrypted_private_key')
pk = decrypt_private_key(encrypted_pk)
account = Account.from_key(pk)
print(f'Wallet: {account.address}')

# Get current balances
cbbtc_bal = cbbtc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
usdc_bal = usdc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
print(f'cbBTC: {cbbtc_bal / 1e8:.8f}')
print(f'USDC: {usdc_bal / 1e6:.6f}')

def send_tx(contract_call, gas=100000):
    """Build and send transaction"""
    tx = contract_call.build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address, 'latest'),
        'gas': gas,
        'gasPrice': int(w3.eth.gas_price * 3),
        'chainId': 8453
    })
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f'TX: {tx_hash.hex()}')
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    print(f'Status: {"✅" if receipt.status == 1 else "❌"}')
    return receipt.status == 1, tx_hash.hex()

# Step 1: Swap half cbBTC -> USDC (approval already done!)
half_cbbtc = cbbtc_bal // 2
print(f'\n--- Swapping {half_cbbtc / 1e8:.8f} cbBTC -> USDC ---')
deadline = int(time.time()) + 1200
routes = [(Web3.to_checksum_address(CBBTC), Web3.to_checksum_address(USDC), False, Web3.to_checksum_address(FACTORY))]
success, tx = send_tx(router.functions.swapExactTokensForTokens(half_cbbtc, 0, routes, account.address, deadline), gas=300000)
if not success:
    print('Swap failed!')
    exit(1)

# Refresh balances
time.sleep(3)
cbbtc_bal = cbbtc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
usdc_bal = usdc_contract.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDR)).call()
print(f'\nNew balances:')
print(f'cbBTC: {cbbtc_bal / 1e8:.8f}')
print(f'USDC: {usdc_bal / 1e6:.6f}')

# Step 2: Approve both for LP
print('\n--- Approving for LP ---')
send_tx(cbbtc_contract.functions.approve(Web3.to_checksum_address(ROUTER), cbbtc_bal))
send_tx(usdc_contract.functions.approve(Web3.to_checksum_address(ROUTER), usdc_bal))

# Step 3: addLiquidity
print('\n--- Adding Liquidity ---')
slippage = 0.05  # 5%
min_cbbtc = int(cbbtc_bal * (1 - slippage))
min_usdc = int(usdc_bal * (1 - slippage))
deadline = int(time.time()) + 1200

success, tx = send_tx(router.functions.addLiquidity(
    Web3.to_checksum_address(CBBTC),
    Web3.to_checksum_address(USDC),
    False,  # stable
    cbbtc_bal,
    usdc_bal,
    min_cbbtc,
    min_usdc,
    account.address,
    deadline
), gas=400000)

if success:
    print(f'\n🎉 LP Position Created!')
    print(f'https://basescan.org/tx/{tx}')
else:
    print('\n❌ addLiquidity failed')
