from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
agent = "0x8bfb3693E1d09e9C2F07Fb59A75120ED3B4617f5"

# ETH balance
eth_bal = w3.eth.get_balance(agent)
print(f"ETH: {eth_bal/1e18:.6f}")

# USDC balance
usdc = w3.eth.contract(
    address='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    abi=[{
        'name': 'balanceOf',
        'inputs': [{'name': 'account', 'type': 'address'}],
        'outputs': [{'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function'
    }]
)
usdc_bal = usdc.functions.balanceOf(agent).call()
print(f"USDC: ${usdc_bal/1e6:.2f}")

# Check session key status
sk_abi = [{
    'name': 'getSessionKeyInfo',
    'type': 'function',
    'stateMutability': 'view',
    'inputs': [{'name': 'key', 'type': 'address'}],
    'outputs': [
        {'name': 'active', 'type': 'bool'},
        {'name': 'validUntil', 'type': 'uint48'},
        {'name': 'dailyLimitUSD', 'type': 'uint256'},
        {'name': 'spentTodayUSD', 'type': 'uint256'}
    ]
}]
sa = w3.eth.contract(address=agent, abi=sk_abi)
sk_info = sa.functions.getSessionKeyInfo('0x7B878CaB79285b9B512B39Da6fe4706A804ce2Fe').call()
print(f"\nSession Key Status:")
print(f"  Active: {sk_info[0]}")
print(f"  Valid Until: {sk_info[1]}")
print(f"  Daily Limit: ${sk_info[2]/1e8:.0f}")
print(f"  Spent Today: ${sk_info[3]/1e8:.2f}")
