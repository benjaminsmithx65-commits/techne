import requests

r = requests.get('https://yields.llama.fi/pools')
data = r.json()['data']

# Search for VVV pools
vvv = [p for p in data if 'vvv' in p.get('symbol', '').lower()]
print(f'{len(vvv)} VVV pools found')
for p in vvv[:15]:
    print(f"  {p.get('project')} - {p.get('symbol')} - {p.get('chain')} - TVL: ${p.get('tvlUsd', 0)/1e6:.2f}M")

# Check if VVV on Aerodrome Base exists
aero_vvv = [p for p in vvv if 'aerodrome' in p.get('project', '').lower()]
print(f'\n{len(aero_vvv)} Aerodrome VVV pools')
for p in aero_vvv:
    print(f"  {p.get('symbol')} - {p.get('chain')} - {p.get('pool')[:60]}...")
