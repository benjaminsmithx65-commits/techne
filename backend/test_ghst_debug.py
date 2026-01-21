"""
Debug GHST/USDC CL pool APY discrepancy
Techne: 4.78%
Aerodrome: 96.63%
"""
import asyncio
import sys
sys.path.insert(0, '.')

from data_sources.aerodrome import aerodrome_client
from data_sources.geckoterminal import gecko_client

GHST_USDC_POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"

async def main():
    print("=" * 60)
    print("   GHST/USDC CL POOL APY DEBUG")
    print("=" * 60)
    
    # Test multicall
    print("\n[1] MULTICALL APY:")
    result = await aerodrome_client.get_real_time_apy_multicall(GHST_USDC_POOL)
    for k, v in result.items():
        print(f"   {k}: {v}")
    
    # Check TVL from GeckoTerminal
    print("\n[2] GECKOTERMINAL DATA:")
    gecko_data = await gecko_client.get_pool_by_address("base", GHST_USDC_POOL)
    if gecko_data:
        print(f"   TVL: ${gecko_data.get('tvl', 0):,.0f}")
        print(f"   Symbol: {gecko_data.get('symbol')}")
    
    # Manual calculation
    print("\n[3] APY CALCULATION:")
    yearly_rewards = result.get("yearly_rewards_usd", 0)
    staked_ratio = result.get("staked_ratio", 1.0)
    gecko_tvl = gecko_data.get("tvl", 0) if gecko_data else 0
    
    print(f"   Yearly Rewards USD: ${yearly_rewards:,.0f}")
    print(f"   GeckoTerminal TVL: ${gecko_tvl:,.0f}")
    print(f"   Staked Ratio: {staked_ratio:.4f} ({staked_ratio*100:.2f}%)")
    
    if gecko_tvl > 0:
        # APY using total TVL (wrong for stakers)
        apy_total = (yearly_rewards / gecko_tvl) * 100
        print(f"\n   APY (total TVL): {apy_total:.2f}%")
        
        # APY using staked TVL (correct for stakers)
        staked_tvl = gecko_tvl * staked_ratio
        if staked_tvl > 0:
            apy_staked = (yearly_rewards / staked_tvl) * 100
            print(f"   APY (staked TVL): {apy_staked:.2f}%")
        
        # What Aerodrome shows (96.63%)
        # Backwards calculation: what ratio would give 96.63%?
        aerodrome_apy = 96.63
        implied_staked_tvl = yearly_rewards / (aerodrome_apy / 100)
        implied_ratio = implied_staked_tvl / gecko_tvl if gecko_tvl > 0 else 0
        print(f"\n   ⚠️ Aerodrome shows: {aerodrome_apy}%")
        print(f"   Implied staked TVL: ${implied_staked_tvl:,.0f}")
        print(f"   Implied staked ratio: {implied_ratio:.4f} ({implied_ratio*100:.2f}%)")

if __name__ == "__main__":
    asyncio.run(main())
