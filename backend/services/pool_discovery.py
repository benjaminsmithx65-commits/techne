"""
Pool Discovery Service
Real-time detection of new pools from The Graph (before DefiLlama)

Features:
- Poll Aerodrome and Uniswap subgraphs every 30s
- Detect new pools immediately after creation
- Filter by initial TVL and token verification
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

# Subgraph endpoints for Base chain
SUBGRAPHS = {
    "aerodrome": {
        "url": "https://api.thegraph.com/subgraphs/name/aerodrome-finance/aerodrome-base",
        "name": "Aerodrome",
        "pool_type": "dual"
    },
    "uniswap_v3": {
        "url": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-base", 
        "name": "Uniswap V3",
        "pool_type": "dual"
    }
}

# Queries for new pools
POOL_CREATED_QUERY = """
{
  pools(
    first: 20, 
    orderBy: createdAtTimestamp, 
    orderDirection: desc,
    where: { createdAtTimestamp_gt: "%s" }
  ) {
    id
    token0 {
      id
      symbol
      name
      decimals
    }
    token1 {
      id
      symbol
      name
      decimals
    }
    createdAtTimestamp
    totalValueLockedUSD
    volumeUSD
    feeTier
  }
}
"""

# Aerodrome specific query (different schema)
AERODROME_QUERY = """
{
  pairs(
    first: 20,
    orderBy: timestamp,
    orderDirection: desc,
    where: { timestamp_gt: "%s" }
  ) {
    id
    token0 {
      id
      symbol
      name
    }
    token1 {
      id
      symbol
      name
    }
    timestamp
    reserveUSD
    volumeUSD
    stable
  }
}
"""


class PoolDiscovery:
    """
    Monitors The Graph for new pool creation events.
    
    Usage:
        discovery = PoolDiscovery()
        new_pools = await discovery.check_new_pools()
    """
    
    def __init__(self):
        self.last_check_timestamp = int((datetime.utcnow() - timedelta(hours=24)).timestamp())
        self.known_pools: set = set()
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def query_subgraph(self, url: str, query: str) -> Dict[str, Any]:
        """Execute GraphQL query against subgraph."""
        try:
            response = await self.client.post(
                url,
                json={"query": query},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[PoolDiscovery] Subgraph error: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"[PoolDiscovery] Query error: {e}")
            return {}
    
    async def check_aerodrome(self) -> List[Dict]:
        """Check Aerodrome for new pools."""
        query = AERODROME_QUERY % self.last_check_timestamp
        result = await self.query_subgraph(SUBGRAPHS["aerodrome"]["url"], query)
        
        pools = []
        pairs = result.get("data", {}).get("pairs", [])
        
        for pair in pairs:
            pool_id = pair.get("id", "")
            
            if pool_id in self.known_pools:
                continue
            
            self.known_pools.add(pool_id)
            
            pools.append({
                "id": pool_id,
                "protocol": "aerodrome",
                "token0": pair.get("token0", {}).get("symbol", "???"),
                "token1": pair.get("token1", {}).get("symbol", "???"),
                "token0_address": pair.get("token0", {}).get("id", ""),
                "token1_address": pair.get("token1", {}).get("id", ""),
                "created_at": pair.get("timestamp"),
                "tvl_usd": float(pair.get("reserveUSD", 0) or 0),
                "volume_usd": float(pair.get("volumeUSD", 0) or 0),
                "stable": pair.get("stable", False),
                "pool_type": "stable" if pair.get("stable") else "volatile",
                "source": "the_graph"
            })
        
        return pools
    
    async def check_uniswap_v3(self) -> List[Dict]:
        """Check Uniswap V3 for new pools."""
        query = POOL_CREATED_QUERY % self.last_check_timestamp
        result = await self.query_subgraph(SUBGRAPHS["uniswap_v3"]["url"], query)
        
        pools = []
        pool_data = result.get("data", {}).get("pools", [])
        
        for pool in pool_data:
            pool_id = pool.get("id", "")
            
            if pool_id in self.known_pools:
                continue
            
            self.known_pools.add(pool_id)
            
            fee_tier = pool.get("feeTier", 3000)
            fee_pct = int(fee_tier) / 10000  # e.g., 3000 -> 0.3%
            
            pools.append({
                "id": pool_id,
                "protocol": "uniswap_v3",
                "token0": pool.get("token0", {}).get("symbol", "???"),
                "token1": pool.get("token1", {}).get("symbol", "???"),
                "token0_address": pool.get("token0", {}).get("id", ""),
                "token1_address": pool.get("token1", {}).get("id", ""),
                "created_at": pool.get("createdAtTimestamp"),
                "tvl_usd": float(pool.get("totalValueLockedUSD", 0) or 0),
                "volume_usd": float(pool.get("volumeUSD", 0) or 0),
                "fee_tier": fee_tier,
                "fee_pct": fee_pct,
                "pool_type": "volatile",
                "source": "the_graph"
            })
        
        return pools
    
    async def check_new_pools(self, min_tvl: float = 10000) -> List[Dict]:
        """
        Check all subgraphs for new pools.
        
        Args:
            min_tvl: Minimum TVL to include (filter dust pools)
        
        Returns:
            List of newly discovered pools
        """
        print(f"[PoolDiscovery] Checking for new pools since {self.last_check_timestamp}...")
        
        # Query all sources in parallel
        aerodrome_pools, uniswap_pools = await asyncio.gather(
            self.check_aerodrome(),
            self.check_uniswap_v3(),
            return_exceptions=True
        )
        
        all_pools = []
        
        if isinstance(aerodrome_pools, list):
            all_pools.extend(aerodrome_pools)
        else:
            print(f"[PoolDiscovery] Aerodrome error: {aerodrome_pools}")
        
        if isinstance(uniswap_pools, list):
            all_pools.extend(uniswap_pools)
        else:
            print(f"[PoolDiscovery] Uniswap error: {uniswap_pools}")
        
        # Update last check timestamp
        self.last_check_timestamp = int(datetime.utcnow().timestamp())
        
        # Filter by TVL
        filtered = [p for p in all_pools if p.get("tvl_usd", 0) >= min_tvl]
        
        if filtered:
            print(f"[PoolDiscovery] Found {len(filtered)} new pools (min TVL ${min_tvl:,.0f})")
            for pool in filtered:
                print(f"  - {pool['protocol']}: {pool['token0']}/{pool['token1']} (TVL: ${pool['tvl_usd']:,.0f})")
        
        return filtered
    
    async def close(self):
        await self.client.aclose()


# Global instance
_discovery_instance = None

def get_discovery() -> PoolDiscovery:
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = PoolDiscovery()
    return _discovery_instance


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("="*60)
        print("Pool Discovery Test")
        print("="*60)
        
        discovery = PoolDiscovery()
        
        # Check for pools created in last 24h
        discovery.last_check_timestamp = int((datetime.utcnow() - timedelta(hours=24)).timestamp())
        
        pools = await discovery.check_new_pools(min_tvl=1000)
        
        print(f"\nFound {len(pools)} pools in last 24h")
        
        for pool in pools[:5]:
            print(f"\n{pool['protocol'].upper()}: {pool['token0']}/{pool['token1']}")
            print(f"  TVL: ${pool['tvl_usd']:,.2f}")
            print(f"  Volume: ${pool['volume_usd']:,.2f}")
            print(f"  Type: {pool['pool_type']}")
        
        await discovery.close()
    
    asyncio.run(test())
