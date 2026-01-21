"""
Debug NOCK/USDC pool APY discrepancy
Techne: 10253%
Aerodrome: 50.63%
"""
import asyncio
import sys
sys.path.insert(0, '.')

from data_sources.aerodrome import aerodrome_client

NOCK_USDC_POOL = "0x85f1aa3a70fedd1c52705c15baed143e675cd626"

async def main():
    print("=" * 60)
    print("   NOCK/USDC APY DEBUG")
    print("=" * 60)
    
    # Test multicall
    print("\n[1] MULTICALL APY:")
    result = await aerodrome_client.get_real_time_apy_multicall(NOCK_USDC_POOL)
    for k, v in result.items():
        print(f"   {k}: {v}")
    
    # Test sequential (original)
    print("\n[2] SEQUENTIAL APY:")
    result2 = await aerodrome_client.get_real_time_apy(NOCK_USDC_POOL)
    for k, v in result2.items():
        print(f"   {k}: {v}")
    
    # Check TVL from GeckoTerminal
    print("\n[3] GECKOTERMINAL TVL:")
    from data_sources.geckoterminal import gecko_client
    gecko_data = await gecko_client.get_pool_by_address("base", NOCK_USDC_POOL)
    if gecko_data:
        print(f"   TVL: ${gecko_data.get('tvl', 0):,.0f}")
        print(f"   Symbol: {gecko_data.get('symbol')}")
    
    # Manual calculation
    print("\n[4] MANUAL CALCULATION:")
    yearly_rewards = result.get("yearly_rewards_usd", 0)
    total_staked = result.get("total_staked_usd", 0)
    gecko_tvl = gecko_data.get("tvl", 0) if gecko_data else 0
    
    print(f"   Yearly Rewards USD: ${yearly_rewards:,.0f}")
    print(f"   Multicall total_staked_usd: ${total_staked:,.0f}")
    print(f"   GeckoTerminal TVL: ${gecko_tvl:,.0f}")
    
    if gecko_tvl > 0:
        correct_apy = (yearly_rewards / gecko_tvl) * 100
        print(f"\n   ✅ CORRECT APY (using Gecko TVL): {correct_apy:.2f}%")
    
    if total_staked > 0:
        current_apy = (yearly_rewards / total_staked) * 100
        print(f"   ❌ CURRENT APY (using staked): {current_apy:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
