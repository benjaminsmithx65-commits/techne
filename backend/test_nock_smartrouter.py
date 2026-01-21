"""
Test NOCK/USDC through full SmartRouter flow 
Expected: ~22% APY (using Gecko TVL)
"""
import asyncio
import sys
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.WARNING)

from api.smart_router import SmartRouter

NOCK_USDC_POOL = "0x85f1aa3a70fedd1c52705c15baed143e675cd626"

async def main():
    router = SmartRouter()
    
    print("=" * 60)
    print("   NOCK/USDC FULL SMARTROUTER TEST")
    print("=" * 60)
    
    result = await router.smart_route_pool_check(NOCK_USDC_POOL, "base")
    
    pool = result.get("pool", {})
    
    print(f"\n📊 Result:")
    print(f"   Symbol: {pool.get('symbol')}")
    print(f"   APY: {pool.get('apy', 'N/A')}%")
    print(f"   APY Status: {pool.get('apy_status')}")
    print(f"   APY Source: {pool.get('apy_source')}")
    print(f"   TVL: ${pool.get('tvl', 0):,.0f}")
    print(f"   Yearly Emissions: ${pool.get('yearly_emissions_usd', 0):,.0f}")
    
    # Verify calculation
    tvl = pool.get('tvl', 0)
    yearly = pool.get('yearly_emissions_usd', 0)
    if tvl > 0 and yearly > 0:
        calculated = (yearly / tvl) * 100
        print(f"\n✅ Verification: ${yearly:,.0f} / ${tvl:,.0f} = {calculated:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
