import requests

r = requests.get('https://yields.llama.fi/pools')
d = r.json()['data']

# Find all WETH-VVV Aerodrome pools
vvv = [p for p in d if 'aerodrome' in p.get('project','').lower() and 'weth' in p.get('symbol','').lower() and 'vvv' in p.get('symbol','').lower()]

print(f'{len(vvv)} WETH-VVV Aerodrome pools found:\n')

for p in vvv:
    print(f"  Symbol: {p.get('symbol')}")
    print(f"  TVL: ${p.get('tvlUsd',0)/1e6:.2f}M")
    print(f"  APY: {p.get('apy',0):.2f}%")
    print(f"  APY Base: {p.get('apyBase',0):.2f}%")
    print(f"  APY Reward: {p.get('apyReward',0):.2f}%")
    print(f"  Pool ID: {p.get('pool')}")
    print()
