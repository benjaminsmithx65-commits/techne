"""Find who has admin role"""
from web3 import Web3

TECHNE_WALLET = Web3.to_checksum_address("0x323f98c4e05073c2f76666944d95e39b78024efd")

w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))

# Check RoleGranted events to find who has roles
ABI = [
    {"anonymous": False, "inputs": [
        {"indexed": True, "name": "role", "type": "bytes32"},
        {"indexed": True, "name": "account", "type": "address"},
        {"indexed": True, "name": "sender", "type": "address"}
    ], "name": "RoleGranted", "type": "event"}
]

contract = w3.eth.contract(address=TECHNE_WALLET, abi=ABI)

# Get all RoleGranted events
events = contract.events.RoleGranted.get_logs(from_block=0, to_block='latest')

AGENT_ROLE = Web3.keccak(text="AGENT_ROLE").hex()
DEFAULT_ADMIN = "0x" + "00" * 32

print(f"AGENT_ROLE hash: {AGENT_ROLE}")
print(f"DEFAULT_ADMIN hash: {DEFAULT_ADMIN}")
print(f"\nRoleGranted events found: {len(events)}")

for e in events:
    role = e.args.role.hex() if hasattr(e.args.role, 'hex') else e.args.role
    print(f"  Role: {role[:20]}... granted to: {e.args.account}")
