"""
Dual LP Swap Simulation - WETH-First Strategy
Always route through WETH for better liquidity

Flow for WETH/VIRTUALS LP:
1. 100% USDC → WETH (deep liquidity)
2. 50% WETH → VIRTUALS (for LP pair)
3. addLiquidity(50% WETH + VIRTUALS)
"""

import asyncio
import os
from web3 import Web3
from dotenv import load_dotenv
load_dotenv()

# Base RPC
RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")

# Token addresses on Base
TOKENS = {
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH": "0x4200000000000000000000000000000000000006",
    "VIRTUALS": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
}

# Aerodrome on Base
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"

# Router ABI
ROUTER_ABI = [
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"components": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "stable", "type": "bool"},
                {"name": "factory", "type": "address"}
            ], "name": "routes", "type": "tuple[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def get_swap_quote(w3: Web3, router, from_token: str, to_token: str, amount: int) -> int:
    """Get swap quote via Aerodrome Router"""
    try:
        route = [{
            "from": Web3.to_checksum_address(from_token),
            "to": Web3.to_checksum_address(to_token),
            "stable": False,
            "factory": Web3.to_checksum_address(AERODROME_FACTORY)
        }]
        amounts = router.functions.getAmountsOut(amount, route).call()
        return amounts[-1]
    except Exception as e:
        print(f"   [Router] Quote error: {e}")
        return 0


async def simulate_weth_first_lp(usdc_amount: int):
    """
    WETH-First LP Strategy:
    1. Swap ALL USDC → WETH (max liquidity)
    2. Swap HALF of WETH → target token
    3. Add liquidity with remaining WETH + target token
    """
    print("\n" + "="*60)
    print(f"🔄 WETH-First LP Strategy")
    print(f"   Pool: WETH/VIRTUALS on Aerodrome")
    print(f"   Total USDC: ${usdc_amount / 1e6:.2f}")
    print("="*60)
    
    # Connect
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    print(f"\n🔗 Connected to Base: {w3.is_connected()}")
    
    router = w3.eth.contract(
        address=Web3.to_checksum_address(AERODROME_ROUTER),
        abi=ROUTER_ABI
    )
    
    # =============================================
    # STEP 1: Swap 100% USDC → WETH (deep liquidity)
    # =============================================
    print(f"\n📥 Step 1: 100% USDC → WETH (deep liquidity pool)")
    
    total_weth = get_swap_quote(w3, router, TOKENS["USDC"], TOKENS["WETH"], usdc_amount)
    
    if total_weth > 0:
        print(f"   ✅ Quote received!")
        print(f"   - Input: ${usdc_amount / 1e6:.2f} USDC")
        print(f"   - Output: {total_weth / 1e18:.6f} WETH")
        eth_price = usdc_amount / total_weth * 1e12
        print(f"   - ETH Price: ${eth_price:.2f}")
    else:
        print(f"   ❌ Quote failed")
        return False
    
    # Split WETH 50/50
    weth_to_keep = total_weth // 2  # For LP
    weth_to_swap = total_weth - weth_to_keep  # To swap for VIRTUALS
    
    print(f"\n📊 WETH Allocation:")
    print(f"   - Keep 50%: {weth_to_keep / 1e18:.6f} WETH (for LP)")
    print(f"   - Swap 50%: {weth_to_swap / 1e18:.6f} WETH → VIRTUALS")
    
    # =============================================
    # STEP 2: Swap 50% WETH → VIRTUALS
    # =============================================
    print(f"\n📥 Step 2: 50% WETH → VIRTUALS")
    
    virtuals_amount = get_swap_quote(w3, router, TOKENS["WETH"], TOKENS["VIRTUALS"], weth_to_swap)
    
    if virtuals_amount > 0:
        print(f"   ✅ Quote received!")
        print(f"   - Input: {weth_to_swap / 1e18:.6f} WETH")
        print(f"   - Output: {virtuals_amount / 1e18:.4f} VIRTUALS")
        virtual_price = weth_to_swap / virtuals_amount
        print(f"   - Rate: 1 VIRTUAL = {virtual_price:.6f} ETH")
    else:
        print(f"   ❌ Quote failed - WETH/VIRTUALS pool may not exist")
        return False
    
    # =============================================
    # STEP 3: Add Liquidity
    # =============================================
    print(f"\n🏊 Step 3: Add Liquidity to WETH/VIRTUALS")
    
    slippage = 0.005  # 0.5%
    
    print(f"   Pool: WETH/VIRTUALS (volatile)")
    print(f"   Token A: {weth_to_keep / 1e18:.6f} WETH")
    print(f"   Token B: {virtuals_amount / 1e18:.4f} VIRTUALS")
    print(f"   Slippage: {slippage * 100}%")
    
    print(f"\n   📝 addLiquidity calldata:")
    print(f"      tokenA: {TOKENS['WETH']}")
    print(f"      tokenB: {TOKENS['VIRTUALS']}")
    print(f"      stable: false")
    print(f"      amountADesired: {weth_to_keep}")
    print(f"      amountBDesired: {virtuals_amount}")
    print(f"      amountAMin: {int(weth_to_keep * (1-slippage))}")
    print(f"      amountBMin: {int(virtuals_amount * (1-slippage))}")
    
    # =============================================
    # SUMMARY
    # =============================================
    print(f"\n" + "="*60)
    print(f"📋 SIMULATION SUMMARY")
    print("="*60)
    print(f"   ✅ Status: SUCCESS")
    print(f"\n   💰 Input: ${usdc_amount / 1e6:.2f} USDC")
    print(f"\n   🔄 Swap Flow (WETH-First):")
    print(f"      USDC ─────────→ WETH ─────────→ LP")
    print(f"      ${usdc_amount/1e6:.2f}     {total_weth/1e18:.4f}ETH")
    print(f"                          │")
    print(f"                          └──────→ VIRTUALS")
    print(f"                              {virtuals_amount/1e18:.2f}")
    print(f"\n   🏊 Final LP Position:")
    print(f"      - {weth_to_keep / 1e18:.6f} WETH")
    print(f"      - {virtuals_amount / 1e18:.4f} VIRTUALS")
    
    # Value check
    value_in_weth = weth_to_keep + weth_to_swap  # Original value
    total_value_usd = usdc_amount / 1e6
    print(f"\n   💵 Position Value: ~${total_value_usd:.2f}")
    
    print(f"\n   ⚡ Benefits of WETH-First:")
    print(f"      - Better liquidity (USDC/WETH = deepest)")
    print(f"      - Lower slippage")
    print(f"      - Works for ANY token paired with WETH")
    
    return True


async def main():
    print("🚀 WETH-First LP Strategy Simulation")
    print("   Logic: Always route through WETH for max liquidity")
    
    # Simulate $500 USDC
    result = await simulate_weth_first_lp(500_000_000)  # $500
    
    print(f"\n{'='*60}")
    if result:
        print("✅ WETH-First strategy is OPERATIONAL")
    else:
        print("⚠️ Quotes failed - check pool availability")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
