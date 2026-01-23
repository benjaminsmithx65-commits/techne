"""
Gap Analysis: The Graph vs DefiLlama
Compares detection speed between real-time subgraph and aggregator API

Purpose: Prove that pool discovery via The Graph is faster than DefiLlama
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Set, List
import json

# DefiLlama API
DEFILLAMA_YIELDS_URL = "https://yields.llama.fi/pools"

# The Graph endpoints
AERODROME_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/aerodrome-finance/aerodrome-base"

# Query for Aerodrome pools
AERODROME_QUERY = """
{
  pairs(first: 100, orderBy: timestamp, orderDirection: desc) {
    id
    token0 { symbol }
    token1 { symbol }
    timestamp
    reserveUSD
  }
}
"""


class GapAnalyzer:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.graph_pools: Dict[str, dict] = {}
        self.defillama_pools: Dict[str, dict] = {}
        self.detection_log: List[dict] = []
    
    async def fetch_graph_pools(self) -> Set[str]:
        """Fetch pools from The Graph (Aerodrome)."""
        try:
            response = await self.client.post(
                AERODROME_SUBGRAPH,
                json={"query": AERODROME_QUERY}
            )
            
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("data", {}).get("pairs", [])
                
                pools = set()
                for pair in pairs:
                    pool_id = pair.get("id", "").lower()
                    symbol = f"{pair.get('token0', {}).get('symbol', '?')}/{pair.get('token1', {}).get('symbol', '?')}"
                    
                    if pool_id not in self.graph_pools:
                        self.graph_pools[pool_id] = {
                            "id": pool_id,
                            "symbol": symbol,
                            "first_seen_graph": datetime.utcnow().isoformat(),
                            "timestamp": pair.get("timestamp"),
                            "tvl": float(pair.get("reserveUSD", 0) or 0)
                        }
                    
                    pools.add(pool_id)
                
                return pools
            
        except Exception as e:
            print(f"[Graph] Error: {e}")
        
        return set()
    
    async def fetch_defillama_pools(self) -> Set[str]:
        """Fetch pools from DefiLlama."""
        try:
            response = await self.client.get(DEFILLAMA_YIELDS_URL)
            
            if response.status_code == 200:
                data = response.json()
                pools = data.get("data", [])
                
                # Filter for Aerodrome on Base
                aerodrome_pools = set()
                for pool in pools:
                    if pool.get("chain", "").lower() == "base" and "aerodrome" in pool.get("project", "").lower():
                        pool_id = pool.get("pool", "").lower()
                        
                        if pool_id not in self.defillama_pools:
                            self.defillama_pools[pool_id] = {
                                "id": pool_id,
                                "symbol": pool.get("symbol", "?"),
                                "first_seen_defillama": datetime.utcnow().isoformat(),
                                "tvl": pool.get("tvlUsd", 0),
                                "apy": pool.get("apy", 0)
                            }
                        
                        aerodrome_pools.add(pool_id)
                
                return aerodrome_pools
        
        except Exception as e:
            print(f"[DefiLlama] Error: {e}")
        
        return set()
    
    async def analyze_gap(self, duration_minutes: int = 30, interval_seconds: int = 30):
        """
        Run gap analysis for specified duration.
        
        Compares which pools appear first in The Graph vs DefiLlama.
        """
        print("="*70)
        print("GAP ANALYSIS: The Graph vs DefiLlama")
        print(f"Duration: {duration_minutes} min | Check interval: {interval_seconds}s")
        print("="*70)
        print()
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        check_count = 0
        graph_first_count = 0
        defillama_first_count = 0
        
        while datetime.utcnow() < end_time:
            check_count += 1
            print(f"\n[Check #{check_count}] {datetime.utcnow().strftime('%H:%M:%S')}")
            
            # Fetch from both sources
            graph_pools, defillama_pools = await asyncio.gather(
                self.fetch_graph_pools(),
                self.fetch_defillama_pools()
            )
            
            print(f"  The Graph: {len(graph_pools)} pools")
            print(f"  DefiLlama: {len(defillama_pools)} pools")
            
            # Find pools in Graph but not in DefiLlama (Graph is faster)
            graph_only = graph_pools - defillama_pools
            if graph_only:
                graph_first_count += len(graph_only)
                print(f"  🚀 GRAPH FIRST: {len(graph_only)} pools")
                for pool_id in list(graph_only)[:3]:  # Show first 3
                    info = self.graph_pools.get(pool_id, {})
                    print(f"      - {info.get('symbol', '?')} (TVL: ${info.get('tvl', 0):,.0f})")
                    
                    # Log detection
                    self.detection_log.append({
                        "pool_id": pool_id,
                        "symbol": info.get("symbol"),
                        "detected_by": "the_graph",
                        "timestamp": datetime.utcnow().isoformat(),
                        "tvl": info.get("tvl", 0)
                    })
            
            # Find pools in DefiLlama but not in Graph (unusual)
            defillama_only = defillama_pools - graph_pools
            if defillama_only:
                defillama_first_count += len(defillama_only)
                print(f"  📊 DefiLlama only: {len(defillama_only)} pools")
            
            # Wait for next check
            await asyncio.sleep(interval_seconds)
        
        # Summary
        print("\n" + "="*70)
        print("GAP ANALYSIS SUMMARY")
        print("="*70)
        print(f"  Total Checks: {check_count}")
        print(f"  Pools detected by Graph first: {graph_first_count}")
        print(f"  Pools detected by DefiLlama first: {defillama_first_count}")
        
        if graph_first_count > defillama_first_count:
            print(f"\n  ✅ CONCLUSION: The Graph is faster for pool detection!")
            advantage = graph_first_count - defillama_first_count
            print(f"     Advantage: +{advantage} pools detected earlier")
        else:
            print(f"\n  ⚠ INCONCLUSIVE: Need more data or new pools created")
        
        # Save log
        log_file = f"gap_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump({
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "checks": check_count,
                "graph_first": graph_first_count,
                "defillama_first": defillama_first_count,
                "detections": self.detection_log
            }, f, indent=2)
        
        print(f"\n  📝 Log saved to: {log_file}")
        print("="*70)
    
    async def close(self):
        await self.client.aclose()


async def main():
    analyzer = GapAnalyzer()
    
    try:
        # Run for 30 minutes with checks every 30 seconds
        await analyzer.analyze_gap(duration_minutes=30, interval_seconds=30)
    finally:
        await analyzer.close()


if __name__ == "__main__":
    print("\n🔍 Starting Gap Analysis: The Graph vs DefiLlama\n")
    print("This compares real-time pool detection speed.\n")
    print("Press Ctrl+C to stop early\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹ Analysis stopped by user")
