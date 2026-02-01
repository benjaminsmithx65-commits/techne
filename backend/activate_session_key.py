"""
Activate Session Key for Existing Agent

This script helps activate the session key for an agent that was deployed
before automatic session key activation was implemented.

User must sign a transaction via frontend to call addSessionKey() on their smart account.
"""

import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from api.session_key_signer import get_session_key_address

# Agent info
AGENT_ID = "agent_1_1769892693"
USER_ADDRESS = "0xba9d6947c0ad6ea2aaa99507355cf83b4d098058"
SMART_ACCOUNT = "0x5E047DeB5eb22F4E4A7f2207087369468575e3EF"

print("=" * 60)
print("SESSION KEY ACTIVATION FOR EXISTING AGENT")
print("=" * 60)
print()
print(f"Agent ID:       {AGENT_ID}")
print(f"User Address:   {USER_ADDRESS}")
print(f"Smart Account:  {SMART_ACCOUNT}")
print()

# Get session key address
session_key_addr = get_session_key_address(AGENT_ID, USER_ADDRESS)
print(f"Session Key:    {session_key_addr}")
print()

print("=" * 60)
print("ACTION REQUIRED")
print("=" * 60)
print()
print("To enable autonomous trading, you need to register the session key.")
print()
print("Option 1: Use Frontend")
print("-" * 40)
print("Go to Agent Settings > Session Key > Activate")
print()
print("Option 2: Direct Contract Call")
print("-" * 40)
print(f"""
Call on Smart Account ({SMART_ACCOUNT}):

addSessionKey(
    key: {session_key_addr},
    validUntil: 281474976710655,  // max uint48 (no expiration)
    dailyLimitUSD: 10000000000000  // $100,000 * 10^8
)

You can do this via:
1. Basescan Write Contract: https://basescan.org/address/{SMART_ACCOUNT}#writeContract
2. MetaMask direct call
3. The /api/agent-config/setup-auto-trading endpoint
""")
