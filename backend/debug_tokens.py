import requests

WETH = "0x4200000000000000000000000000000000000006"
VVV = "0xacfe6019ed1a7dc6f7b508c02d1b04ec88cc21bf"

r = requests.get('https://yields.llama.fi/pools')
data = r.json()['data']

# Find aerodrome WETH-VVV pool and check its structure
for p in data:
    if 'aerodrome' in p.get('project', '').lower() and 'weth' in p.get('symbol', '').lower() and 'vvv' in p.get('symbol', '').lower():
        print(f"Found: {p.get('project')} - {p.get('symbol')}")
        print(f"  Pool ID: {p.get('pool')}")
        print(f"  Chain: {p.get('chain')}")
        print(f"  underlyingTokens: {p.get('underlyingTokens')}")
        print()
        
        # Check if tokens are in underlyingTokens
        underlying = p.get('underlyingTokens') or []
        t0 = WETH.lower()
        t1 = VVV.lower()
        
        for i, token in enumerate(underlying):
            token_lower = str(token).lower()
            print(f"  Token {i}: {token_lower}")
            print(f"    Contains WETH ({t0})? {t0 in token_lower}")
            print(f"    Contains VVV ({t1})? {t1 in token_lower}")
