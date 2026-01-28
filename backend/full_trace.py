"""
Full token transfer trace - get all transfers ever
"""
from web3 import Web3
import time

AGENT = '0x8FE9c7b9a195D37C789D3529E6903394a52b5e82'
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
CBBTC = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf'
LP = '0x9c38b55f9a9aba91bbcedeb12bf4428f47a6a0b8'

w3 = Web3(Web3.HTTPProvider('https://base-mainnet.public.blastapi.io'))
TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

print("=== FULL TOKEN TRANSFER HISTORY ===\n")

# Current balances
usdc_now = int(w3.eth.call({'to': Web3.to_checksum_address(USDC), 'data': '0x70a08231' + AGENT[2:].lower().zfill(64)}).hex(), 16) / 1e6
cbbtc_now = int(w3.eth.call({'to': Web3.to_checksum_address(CBBTC), 'data': '0x70a08231' + AGENT[2:].lower().zfill(64)}).hex(), 16) / 1e8
lp_now = int(w3.eth.call({'to': Web3.to_checksum_address(LP), 'data': '0x70a08231' + AGENT[2:].lower().zfill(64)}).hex(), 16)

print(f"Current balances:")
print(f"  USDC: ${usdc_now:.2f}")
print(f"  cbBTC: {cbbtc_now:.8f}")
print(f"  LP tokens: {lp_now}")
print("")

# Get all USDC transfers from agent creation (use wide range)
start_block = 40000000  # ~Jan 2025
latest = w3.eth.block_number

print("=== USDC FLOWS ===")
time.sleep(1)
try:
    # IN
    usdc_in = w3.eth.get_logs({
        'address': Web3.to_checksum_address(USDC),
        'topics': [TRANSFER_TOPIC, None, '0x' + AGENT[2:].lower().zfill(64)],
        'fromBlock': start_block, 'toBlock': latest
    })
    total_in = sum(int(log['data'].hex(), 16) for log in usdc_in) / 1e6
    print(f"USDC IN: {len(usdc_in)} transfers, total: ${total_in:.2f}")
    for log in usdc_in:
        amt = int(log['data'].hex(), 16) / 1e6
        from_addr = '0x' + log['topics'][1].hex()[-40:]
        print(f"  +${amt:.6f} from {from_addr[:10]}...")
except Exception as e:
    print(f"Error IN: {e}")

time.sleep(1)
try:
    # OUT
    usdc_out = w3.eth.get_logs({
        'address': Web3.to_checksum_address(USDC),
        'topics': [TRANSFER_TOPIC, '0x' + AGENT[2:].lower().zfill(64), None],
        'fromBlock': start_block, 'toBlock': latest
    })
    total_out = sum(int(log['data'].hex(), 16) for log in usdc_out) / 1e6
    print(f"\nUSDC OUT: {len(usdc_out)} transfers, total: ${total_out:.2f}")
    for log in usdc_out:
        amt = int(log['data'].hex(), 16) / 1e6
        to_addr = '0x' + log['topics'][2].hex()[-40:]
        print(f"  -${amt:.6f} to {to_addr[:10]}...")
except Exception as e:
    print(f"Error OUT: {e}")

print(f"\n=== NET USDC FLOW ===")
print(f"Total IN: ${total_in:.2f}")
print(f"Total OUT: ${total_out:.2f}")
print(f"Net: ${total_in - total_out:.2f}")
print(f"Current balance: ${usdc_now:.2f}")
print(f"Difference: ${(total_in - total_out) - usdc_now:.2f}")

# cbBTC flows
print("\n=== cbBTC FLOWS ===")
time.sleep(1)
try:
    cbbtc_in = w3.eth.get_logs({
        'address': Web3.to_checksum_address(CBBTC),
        'topics': [TRANSFER_TOPIC, None, '0x' + AGENT[2:].lower().zfill(64)],
        'fromBlock': start_block, 'toBlock': latest
    })
    cb_in = sum(int(log['data'].hex(), 16) for log in cbbtc_in) / 1e8
    print(f"cbBTC IN: {len(cbbtc_in)} transfers, total: {cb_in:.8f}")
except Exception as e:
    print(f"Error: {e}")

time.sleep(1)
try:
    cbbtc_out = w3.eth.get_logs({
        'address': Web3.to_checksum_address(CBBTC),
        'topics': [TRANSFER_TOPIC, '0x' + AGENT[2:].lower().zfill(64), None],
        'fromBlock': start_block, 'toBlock': latest
    })
    cb_out = sum(int(log['data'].hex(), 16) for log in cbbtc_out) / 1e8
    print(f"cbBTC OUT: {len(cbbtc_out)} transfers, total: {cb_out:.8f}")
    print(f"Net cbBTC: {cb_in - cb_out:.8f}")
except Exception as e:
    print(f"Error: {e}")

# LP tokens
print("\n=== LP TOKEN FLOWS ===")
time.sleep(1)
try:
    lp_in = w3.eth.get_logs({
        'address': Web3.to_checksum_address(LP),
        'topics': [TRANSFER_TOPIC, None, '0x' + AGENT[2:].lower().zfill(64)],
        'fromBlock': start_block, 'toBlock': latest
    })
    lp_total_in = sum(int(log['data'].hex(), 16) for log in lp_in)
    print(f"LP IN: {len(lp_in)} mints, total: {lp_total_in}")
    for log in lp_in:
        amt = int(log['data'].hex(), 16)
        print(f"  +{amt} LP")
except Exception as e:
    print(f"Error: {e}")

print("\n=== SUMMARY ===")
print(f"USDC deposited: ${total_in:.2f}")
print(f"USDC withdrawn: ${total_out:.2f}")
print(f"cbBTC net (went to LP): {cb_in - cb_out:.8f}")
print(f"LP tokens received: {lp_total_in}")
print(f"Current USDC: ${usdc_now:.2f}")
