from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

FACTORY = '0x420DD381b31aEf6683db6B902084cB0FFECe40Da'
CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

data = '0x1698ee82'
data += CBBTC[2:].lower().zfill(64)
data += USDC[2:].lower().zfill(64)
data += '0'.zfill(64)

result = w3.eth.call({'to': Web3.to_checksum_address(FACTORY), 'data': data})
pool_addr = '0x' + result.hex()[-40:]
print(f'Pool address: {pool_addr}')
print(f'Length: {len(pool_addr)}')

# Verify
AGENT = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
bal = int(w3.eth.call({
    'to': Web3.to_checksum_address(pool_addr),
    'data': '0x70a08231' + AGENT[2:].lower().zfill(64)
}).hex(), 16)
print(f'Balance: {bal} wei')
print(f'Balance: {bal / 1e18} LP tokens')
