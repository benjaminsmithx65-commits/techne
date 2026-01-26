"""Find pools matching agent allocation criteria - output to file"""
import httpx
import asyncio

async def find_matching_pools():
    output = []
    output.append("=" * 70)
    output.append("Finding Aerodrome pools for Agent Allocation")
    output.append("Criteria: TVL $500k+, APY >50%, contains WETH or USDC")
    output.append("=" * 70)
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.get("https://yields.llama.fi/pools")
            data = r.json()
            
            pools = [p for p in data.get("data", []) 
                     if p.get("chain") == "Base" 
                     and "aerodrome" in p.get("project", "").lower()]
            
            output.append(f"\nTotal Aerodrome pools on Base: {len(pools)}")
            
            matching = []
            for p in pools:
                tvl = p.get("tvlUsd", 0) or 0
                apy = p.get("apy", 0) or 0
                symbol = p.get("symbol", "").upper()
                pool_addr = p.get("pool", "")
                
                has_weth = "WETH" in symbol or "ETH" in symbol
                has_usdc = "USDC" in symbol
                tvl_ok = tvl >= 500000
                apy_ok = apy >= 50
                
                if (has_weth or has_usdc) and tvl_ok and apy_ok:
                    matching.append({
                        "symbol": symbol,
                        "tvl": tvl,
                        "apy": apy,
                        "pool": pool_addr
                    })
            
            matching.sort(key=lambda x: x["apy"], reverse=True)
            
            output.append(f"\n{'='*70}")
            output.append(f"MATCHING POOLS: {len(matching)}")
            output.append(f"{'='*70}")
            
            for i, p in enumerate(matching, 1):
                output.append(f"{i:2}. {p['symbol']:<40} TVL: ${p['tvl']:>12,.0f} | APY: {p['apy']:>6.1f}%")
                output.append(f"    Pool: {p['pool']}")
            
            if not matching:
                output.append("\n⚠️ NO POOLS MATCH STRICT CRITERIA!")
                output.append("\nRelaxed criteria (TVL>=$100k, APY>=20%, WETH/USDC):")
                
                relaxed = []
                for p in pools:
                    tvl = p.get("tvlUsd", 0) or 0
                    apy = p.get("apy", 0) or 0
                    symbol = p.get("symbol", "").upper()
                    has_weth = "WETH" in symbol or "ETH" in symbol
                    has_usdc = "USDC" in symbol
                    
                    if (has_weth or has_usdc) and tvl >= 100000 and apy >= 20:
                        relaxed.append({"symbol": symbol, "tvl": tvl, "apy": apy, "pool": p.get("pool", "")})
                
                relaxed.sort(key=lambda x: x["apy"], reverse=True)
                for i, p in enumerate(relaxed[:20], 1):
                    output.append(f"{i:2}. {p['symbol']:<40} TVL: ${p['tvl']:>10,.0f} | APY: {p['apy']:>5.1f}%")
                    
        except Exception as e:
            output.append(f"Error: {e}")
    
    result = "\n".join(output)
    print(result)
    
    with open("pool_results.txt", "w") as f:
        f.write(result)
    print("\n\n>>> Results saved to pool_results.txt")

asyncio.run(find_matching_pools())
