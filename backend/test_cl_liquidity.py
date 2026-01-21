"""
Debug: Check actual CL pool liquidity values
"""
import asyncio
import sys
sys.path.insert(0, '.')

from web3 import Web3
from data_sources.aerodrome import aerodrome_client, CL_GAUGE_ABI

GHST_USDC_POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"

CL_POOL_ABI = [
    {'name': 'liquidity', 'inputs': [], 'outputs': [{'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'},
    {'name': 'stakedLiquidity', 'inputs': [], 'outputs': [{'type': 'uint128'}], 'stateMutability': 'view', 'type': 'function'},
    {'name': 'slot0', 'inputs': [], 'outputs': [
        {'type': 'uint160', 'name': 'sqrtPriceX96'},
        {'type': 'int24', 'name': 'tick'},
        {'type': 'uint16', 'name': 'observationIndex'},
        {'type': 'uint16', 'name': 'observationCardinality'},
        {'type': 'uint16', 'name': 'observationCardinalityNext'},
        {'type': 'bool', 'name': 'unlocked'}
    ], 'stateMutability': 'view', 'type': 'function'},
]

async def main():
    w3 = aerodrome_client.w3
    pool_address = Web3.to_checksum_address(GHST_USDC_POOL)
    
    print("=" * 60)
    print("   CL POOL LIQUIDITY DEBUG")
    print("=" * 60)
    
    # Get gauge
    gauge_address = aerodrome_client.voter.functions.gauges(pool_address).call()
    print(f"\nGauge: {gauge_address}")
    
    # Create contracts
    pool = w3.eth.contract(address=pool_address, abi=CL_POOL_ABI)
    gauge = w3.eth.contract(address=gauge_address, abi=CL_GAUGE_ABI)
    
    # Get values
    liquidity = pool.functions.liquidity().call()
    staked_liquidity = pool.functions.stakedLiquidity().call()
    
    print(f"\nPool liquidity(): {liquidity}")
    print(f"Pool stakedLiquidity(): {staked_liquidity}")
    print(f"Ratio staked/liquidity: {staked_liquidity/liquidity if liquidity > 0 else 0:.4f}")
    
    # Get gauge reward rate
    reward_rate = gauge.functions.rewardRate().call()
    print(f"\nGauge rewardRate: {reward_rate}")
    print(f"Reward per second: {reward_rate / 1e18:.6f} AERO")
    
    # Calculate APR based on staked liquidity
    # This is what Aerodrome does
    yearly_rewards = (reward_rate / 1e18) * 31536000 * 0.491  # AERO price ~$0.49
    print(f"\nYearly rewards USD: ${yearly_rewards:,.0f}")
    
    # The key insight: for CL pools, APR is calculated PER UNIT of staked liquidity
    # Not per total TVL
    gecko_tvl = 1189318  # From previous test
    
    # What ratio should give 96.63% APY?
    implied_staked_tvl = yearly_rewards / 0.9663
    implied_ratio = implied_staked_tvl / gecko_tvl
    
    print(f"\nTo match Aerodrome's 96.63%:")
    print(f"  Implied staked TVL: ${implied_staked_tvl:,.0f}")
    print(f"  Implied ratio: {implied_ratio:.4f} ({implied_ratio*100:.2f}%)")
    
    # CL pool staked ratio should use DIFFERENT calculation
    # stakedLiquidity is NOT directly comparable to liquidity
    # Instead we should use: stakedLiquidity / totalLiquidityInAllTicks or similar

if __name__ == "__main__":
    asyncio.run(main())
