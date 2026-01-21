"""Deep timing analysis - profile EVERY section of SmartRouter"""
import asyncio
import time
import sys
sys.path.insert(0, '.')

POOL = "0x56c11053159a24c0731b4b12356bc1f0578fb474"
CHAIN = "base"

async def main():
    print("Deep SmartRouter Timing Analysis\n" + "=" * 50)
    
    # Import and time module loading
    t0 = time.time()
    from data_sources.geckoterminal import gecko_client
    t1 = time.time()
    print(f"1. Import gecko_client: {(t1-t0)*1000:.0f}ms")
    
    from data_sources.aerodrome import aerodrome_client
    t2 = time.time()
    print(f"2. Import aerodrome_client: {(t2-t1)*1000:.0f}ms")
    
    from data_sources.dexscreener import dexscreener_client
    t3 = time.time()
    print(f"3. Import dexscreener: {(t3-t2)*1000:.0f}ms")
    
    from api.security_module import security_checker
    t4 = time.time()
    print(f"4. Import security_checker: {(t4-t3)*1000:.0f}ms")
    
    from data_sources.holder_analysis import holder_analyzer
    t5 = time.time()
    print(f"5. Import holder_analyzer: {(t5-t4)*1000:.0f}ms")
    
    print(f"\nTotal import time: {(t5-t0)*1000:.0f}ms")
    
    # GeckoTerminal fetch
    print("\n--- API Calls ---")
    t_start = time.time()
    pool_data = await gecko_client.get_pool_by_address(CHAIN, POOL)
    t_gecko = time.time()
    print(f"6. GeckoTerminal pool: {(t_gecko-t_start)*1000:.0f}ms")
    
    # Parallel gather 1
    async def fetch_ohlcv():
        return await gecko_client.get_pool_ohlcv(CHAIN, POOL, "day", 7)
    
    async def fetch_apy():
        return await aerodrome_client.get_real_time_apy_multicall(POOL, "cl")
    
    async def fetch_security():
        tokens = [pool_data.get("token0"), pool_data.get("token1")]
        tokens = [t for t in tokens if t]
        return await security_checker.check_security(tokens, CHAIN)
    
    async def fetch_dex():
        return await dexscreener_client.get_token_volatility(CHAIN, POOL)
    
    t_parallel1_start = time.time()
    results = await asyncio.gather(
        fetch_ohlcv(), fetch_apy(), fetch_security(), fetch_dex(),
        return_exceptions=True
    )
    t_parallel1_end = time.time()
    print(f"7. Parallel gather (OHLCV+APY+Security+Dex): {(t_parallel1_end-t_parallel1_start)*1000:.0f}ms")
    
    # Parallel gather 2 - peg, lock, whale
    async def fetch_peg():
        return await security_checker.check_stablecoin_peg(pool_data, CHAIN)
    
    async def fetch_whale():
        return await holder_analyzer.get_holder_analysis(pool_data.get("token0"), CHAIN)
    
    t_parallel2_start = time.time()
    results2 = await asyncio.gather(fetch_peg(), fetch_whale(), return_exceptions=True)
    t_parallel2_end = time.time()
    print(f"8. Parallel gather (Peg+Whale): {(t_parallel2_end-t_parallel2_start)*1000:.0f}ms")
    
    # Risk calculation
    t_risk_start = time.time()
    risk = security_checker.calculate_risk_score(pool_data, results[2], {}, None)
    t_risk_end = time.time()
    print(f"9. Risk calculation: {(t_risk_end-t_risk_start)*1000:.0f}ms")
    
    total = time.time() - t0
    print(f"\n{'='*50}")
    print(f"TOTAL: {total*1000:.0f}ms ({total:.2f}s)")

if __name__ == "__main__":
    asyncio.run(main())
