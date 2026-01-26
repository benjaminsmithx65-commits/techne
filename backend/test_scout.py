"""Direct test of scout to see what pools it returns"""
import asyncio
import sys
sys.path.insert(0, '.')

async def test_scout():
    from artisan.scout_agent import get_scout_pools, ScoutAgent
    
    print("=" * 70)
    print("Testing Scout Agent - get_scout_pools()")
    print("=" * 70)
    
    # Agent config matching yours
    print("\nAgent config:")
    print("  min_apy: 50%")
    print("  min_tvl: $500,000")
    print("  protocols: aerodrome")
    print("  chain: Base")
    
    print("\n[*] Calling get_scout_pools()...")
    
    try:
        pools = await get_scout_pools(
            chain="Base",
            min_tvl=500000,
            max_tvl=100000000,
            min_apy=50,
            max_apy=50000,
            protocols=["aerodrome"]
        )
        
        print(f"\n[OK] get_scout_pools returned {len(pools)} pools")
        
        # Filter for WETH/USDC
        weth_usdc = [p for p in pools if "WETH" in p.get("symbol", "").upper() or "USDC" in p.get("symbol", "").upper()]
        
        print(f"\n[MATCH] With WETH or USDC: {len(weth_usdc)}")
        print("-" * 70)
        
        for i, p in enumerate(weth_usdc[:15], 1):
            print(f"{i:2}. {p.get('symbol', 'N/A'):<35} TVL: ${p.get('tvl', 0):>12,.0f} | APY: {p.get('apy', 0):>6.1f}%")
            
        if not weth_usdc and pools:
            print("\nNo WETH/USDC pools, showing top 10 returned:")
            for i, p in enumerate(pools[:10], 1):
                print(f"{i:2}. {p.get('symbol', 'N/A'):<35} TVL: ${p.get('tvl', 0):>12,.0f} | APY: {p.get('apy', 0):>6.1f}%")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(test_scout())
