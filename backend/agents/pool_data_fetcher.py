"""
The Graph Integration for Pool Data
Fetches real-time TVL, APY, and pool metrics from DeFi protocol subgraphs.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Subgraph endpoints for Base
SUBGRAPHS = {
    "aave": "https://api.thegraph.com/subgraphs/name/aave/protocol-v3-base",
    "compound": "https://api.thegraph.com/subgraphs/name/compound-v3/compound-v3-base",
    "uniswap": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-base",
    "aerodrome": "https://api.thegraph.com/subgraphs/name/aerodrome-finance/aerodrome-base"
}

# Pool addresses we track
TRACKED_POOLS = {
    "aave_usdc": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    "compound_usdc": "0xb125E6687d4313864e53df431d5425969c15Eb2F",
    "moonwell_usdc": "0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22",
    "seamless_usdc": "0x616a4E1db48e22028f6bbf20444Cd3b8e3273738",
    "aerodrome_usdc_weth": "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d"
}


class PoolDataFetcher:
    """
    Fetches real-time pool data from The Graph subgraphs.
    Updates TVL, APY, and other metrics for protocol selection.
    """
    
    def __init__(self):
        self.cache: Dict[str, dict] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_fetch: Dict[str, datetime] = {}
    
    async def get_pool_data(self, protocol: str, pool_address: str) -> Optional[dict]:
        """
        Get pool data with caching.
        Returns: {tvl, apy, volume_24h, fees_24h}
        """
        cache_key = f"{protocol}_{pool_address}"
        
        # Check cache
        if cache_key in self.cache:
            if datetime.utcnow() - self.last_fetch.get(cache_key, datetime.min) < timedelta(seconds=self.cache_ttl):
                return self.cache[cache_key]
        
        # Fetch fresh data
        try:
            data = await self._fetch_from_subgraph(protocol, pool_address)
            if data:
                self.cache[cache_key] = data
                self.last_fetch[cache_key] = datetime.utcnow()
            return data
        except Exception as e:
            print(f"[PoolDataFetcher] Error fetching {protocol}: {e}")
            return self.cache.get(cache_key)  # Return stale cache if available
    
    async def _fetch_from_subgraph(self, protocol: str, pool_address: str) -> Optional[dict]:
        """Fetch data from The Graph subgraph"""
        
        subgraph_url = SUBGRAPHS.get(protocol)
        if not subgraph_url:
            return None
        
        # Protocol-specific queries
        if protocol == "aave":
            query = self._build_aave_query(pool_address)
        elif protocol == "compound":
            query = self._build_compound_query(pool_address)
        elif protocol == "aerodrome":
            query = self._build_aerodrome_query(pool_address)
        else:
            query = self._build_generic_query(pool_address)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(subgraph_url, json={"query": query}) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return self._parse_response(protocol, result)
                else:
                    print(f"[PoolDataFetcher] Subgraph returned {resp.status}")
                    return None
    
    def _build_aave_query(self, pool_address: str) -> str:
        """Build GraphQL query for Aave V3"""
        return f"""
        {{
            reserve(id: "{pool_address.lower()}") {{
                symbol
                liquidityRate
                totalLiquidity
                totalLiquidityUSD
                utilizationRate
            }}
        }}
        """
    
    def _build_compound_query(self, pool_address: str) -> str:
        """Build GraphQL query for Compound V3"""
        return f"""
        {{
            market(id: "{pool_address.lower()}") {{
                name
                totalSupply
                totalSupplyUsd
                supplyRate
                reserves
            }}
        }}
        """
    
    def _build_aerodrome_query(self, pool_address: str) -> str:
        """Build GraphQL query for Aerodrome"""
        return f"""
        {{
            pool(id: "{pool_address.lower()}") {{
                symbol
                totalValueLockedUSD
                volumeUSD
                feesUSD
                token0Price
                token1Price
            }}
        }}
        """
    
    def _build_generic_query(self, pool_address: str) -> str:
        """Generic pool query"""
        return f"""
        {{
            pool(id: "{pool_address.lower()}") {{
                id
                totalValueLockedUSD
                volumeUSD
            }}
        }}
        """
    
    def _parse_response(self, protocol: str, result: dict) -> dict:
        """Parse subgraph response into standardized format"""
        data = result.get("data", {})
        
        if protocol == "aave":
            reserve = data.get("reserve", {})
            # Aave rates are in RAY (1e27), convert to percentage
            liquidity_rate = int(reserve.get("liquidityRate", 0)) / 1e27 * 100
            return {
                "tvl": float(reserve.get("totalLiquidityUSD", 0)),
                "apy": liquidity_rate,
                "utilization": float(reserve.get("utilizationRate", 0)) * 100,
                "source": "thegraph"
            }
        
        elif protocol == "compound":
            market = data.get("market", {})
            # Compound rates are per second, annualize
            supply_rate = float(market.get("supplyRate", 0)) * 31536000 * 100
            return {
                "tvl": float(market.get("totalSupplyUsd", 0)),
                "apy": supply_rate,
                "reserves": float(market.get("reserves", 0)),
                "source": "thegraph"
            }
        
        elif protocol == "aerodrome":
            pool = data.get("pool", {})
            # Estimate APY from fees (simplified)
            tvl = float(pool.get("totalValueLockedUSD", 0))
            fees = float(pool.get("feesUSD", 0))
            apy_estimate = (fees * 365 / tvl * 100) if tvl > 0 else 0
            return {
                "tvl": tvl,
                "apy": apy_estimate,
                "volume_24h": float(pool.get("volumeUSD", 0)),
                "fees_24h": fees,
                "source": "thegraph"
            }
        
        else:
            pool = data.get("pool", {})
            return {
                "tvl": float(pool.get("totalValueLockedUSD", 0)),
                "volume_24h": float(pool.get("volumeUSD", 0)),
                "source": "thegraph"
            }
    
    async def refresh_all_pools(self) -> Dict[str, dict]:
        """Refresh data for all tracked pools"""
        results = {}
        
        for pool_name, pool_address in TRACKED_POOLS.items():
            protocol = pool_name.split("_")[0]
            data = await self.get_pool_data(protocol, pool_address)
            if data:
                results[pool_name] = data
                print(f"[PoolDataFetcher] {pool_name}: TVL=${data.get('tvl', 0)/1e6:.1f}M, APY={data.get('apy', 0):.2f}%")
        
        return results
    
    async def get_best_lending_pool(self, min_tvl: float = 0, max_volatility: float = 100) -> Optional[str]:
        """Find best lending pool based on APY and constraints"""
        await self.refresh_all_pools()
        
        best_pool = None
        best_apy = 0
        
        for pool_name, data in self.cache.items():
            if data.get("tvl", 0) < min_tvl:
                continue
            
            apy = data.get("apy", 0)
            if apy > best_apy:
                best_apy = apy
                best_pool = pool_name
        
        return best_pool


# Global instance
pool_data_fetcher = PoolDataFetcher()


async def update_protocol_data():
    """
    Background task to periodically update protocol data from The Graph.
    Called from ContractMonitor.
    """
    while True:
        try:
            await pool_data_fetcher.refresh_all_pools()
        except Exception as e:
            print(f"[PoolDataFetcher] Background refresh error: {e}")
        
        await asyncio.sleep(300)  # Every 5 minutes
