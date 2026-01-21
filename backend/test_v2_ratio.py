"""
Debug: Calculate staked ratio for V2 to match Aerodrome's APY
Aerodrome = 50%, We = 22% -> ratio should be ~0.45
"""
import asyncio
import sys
sys.path.insert(0, '.')

from web3 import Web3
from data_sources.aerodrome import aerodrome_client, GAUGE_ABI, POOL_ABI

NOCK_USDC_POOL = "0x85f1aa3a70fedd1c52705c15baed143e675cd626"

async def main():
    w3 = aerodrome_client.w3
    pool_address = Web3.to_checksum_address(NOCK_USDC_POOL)
    
    print("=" * 60)
    print("   V2 STAKED RATIO DEBUG")
    print("=" * 60)
    
    # Get gauge address
    gauge_address = aerodrome_client.voter.functions.gauges(pool_address).call()
    print(f"\nGauge: {gauge_address}")
    
    gauge = w3.eth.contract(address=gauge_address, abi=GAUGE_ABI)
    pool = w3.eth.contract(address=pool_address, abi=POOL_ABI)
    
    # Get staked LP (gauge.totalSupply)
    staked_lp = gauge.functions.totalSupply().call()
    print(f"Staked LP (gauge.totalSupply): {staked_lp}")
    print(f"Staked LP (human): {staked_lp / 1e18:.4f}")
    
    # Get total LP (pool.totalSupply)
    total_lp = pool.functions.totalSupply().call()
    print(f"\nTotal LP (pool.totalSupply): {total_lp}")
    print(f"Total LP (human): {total_lp / 1e18:.4f}")
    
    # Calculate ratio
    if total_lp > 0:
        staked_ratio = staked_lp / total_lp
        print(f"\n✅ Staked Ratio: {staked_ratio:.4f} ({staked_ratio*100:.2f}%)")
        
        # Expected APY calculation
        yearly_rewards = 243015  # From previous test
        gecko_tvl = 1087403  # From previous test
        
        staked_tvl = gecko_tvl * staked_ratio
        staker_apy = (yearly_rewards / staked_tvl) * 100 if staked_tvl > 0 else 0
        
        print(f"\n📊 APY Calculations:")
        print(f"   Total TVL: ${gecko_tvl:,.0f}")
        print(f"   Staked TVL: ${staked_tvl:,.0f}")
        print(f"   Yearly Rewards: ${yearly_rewards:,.0f}")
        print(f"   APY (total TVL): {(yearly_rewards/gecko_tvl)*100:.2f}%")
        print(f"   APY (staked TVL): {staker_apy:.2f}%  <- Should match Aerodrome's 50%")

if __name__ == "__main__":
    asyncio.run(main())
