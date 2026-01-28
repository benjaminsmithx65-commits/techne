from web3 import Web3
import time

time.sleep(1)
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
LP = '0x9c38b55f9a9aba91bbcedeb12bf4428f47a6a0b8'
AGENT = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

# Get all data
reserves = w3.eth.call({'to': Web3.to_checksum_address(LP), 'data': '0x0902f1ac'})
r0_usdc = int(reserves.hex()[2:66], 16) / 1e6
r1_cbbtc = int(reserves.hex()[66:130], 16) / 1e8

supply = int(w3.eth.call({'to': Web3.to_checksum_address(LP), 'data': '0x18160ddd'}).hex(), 16)
lp_bal = int(w3.eth.call({'to': Web3.to_checksum_address(LP), 'data': '0x70a08231' + AGENT[2:].lower().zfill(64)}).hex(), 16)

usdc_wallet = int(w3.eth.call({'to': Web3.to_checksum_address(USDC), 'data': '0x70a08231' + AGENT[2:].lower().zfill(64)}).hex(), 16) / 1e6

share = lp_bal / supply if supply > 0 else 0
my_usdc_lp = r0_usdc * share
my_cbbtc_lp = r1_cbbtc * share
lp_value = my_usdc_lp + my_cbbtc_lp * 100000  # cbBTC ~$100k

print('=== CURRENT AGENT VALUE ===')
print(f'USDC wallet: ${usdc_wallet:.2f}')
print(f'LP position USDC side: ${my_usdc_lp:.4f}')
print(f'LP position cbBTC side: {my_cbbtc_lp:.10f} BTC (~${my_cbbtc_lp * 100000:.4f})')
print(f'LP total value: ${lp_value:.4f}')
print('')
print(f'TOTAL: ${usdc_wallet + lp_value:.2f}')
print('')
print('=== WHERE DID $30 GO? ===')
print(f'Started with: ~$40 USDC')
print(f'Now have: ${usdc_wallet + lp_value:.2f}')
print(f'Missing: ~${40 - usdc_wallet - lp_value:.2f}')
