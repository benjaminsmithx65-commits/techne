"""
The Graph Client for Aerodrome Subgraph
Queries pool data, APY, TVL, and historical metrics from Aerodrome Base subgraph.
"""

import httpx
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Aerodrome Base Subgraph endpoints
AERODROME_SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/aerodrome-finance/aerodrome-base"
# Backup: Gateway API (requires API key)
GRAPH_GATEWAY_URL = "https://gateway.thegraph.com/api/[api-key]/subgraphs/id/GENunS—1Av1UM"


class TheGraphClient:
    """
    Client for querying Aerodrome data from The Graph subgraph.
    
    Provides:
    - Pool APY data
    - Historical APY tracking
    - TVL and volume metrics
    - Gauge emissions data
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = AERODROME_SUBGRAPH_URL
        self.timeout = 10.0
        self._client: Optional[httpx.AsyncClient] = None
        
        # Cache for reducing queries
        self._pool_cache: Dict[str, Dict] = {}
        self._cache_ttl = 60  # 1 minute cache
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def _query(self, query: str, variables: Dict = None) -> Dict:
        """Execute GraphQL query"""
        client = await self._get_client()
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = await client.post(
                self.base_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                logger.warning(f"[TheGraph] Query errors: {data['errors']}")
            
            return data.get("data", {})
        except Exception as e:
            logger.error(f"[TheGraph] Query failed: {e}")
            return {}
    
    async def get_pool_by_address(self, pool_address: str) -> Optional[Dict]:
        """
        Get pool data by address.
        
        Returns:
            {
                id: str,
                name: str,
                token0: {symbol, decimals},
                token1: {symbol, decimals},
                reserve0: str,
                reserve1: str,
                totalValueLockedUSD: str,
                volumeUSD: str,
                feesUSD: str,
                apr: float (calculated)
            }
        """
        # Check cache
        cache_key = f"pool_{pool_address.lower()}"
        if self._is_cached(cache_key):
            return self._pool_cache.get(cache_key)
        
        query = """
        query GetPool($id: ID!) {
            pool(id: $id) {
                id
                name
                symbol
                token0 {
                    id
                    symbol
                    decimals
                }
                token1 {
                    id
                    symbol
                    decimals
                }
                reserve0
                reserve1
                totalValueLockedUSD
                volumeUSD
                feesUSD
                token0Price
                token1Price
                stable
                gauge {
                    id
                    totalSupply
                    rewardRate
                }
            }
        }
        """
        
        data = await self._query(query, {"id": pool_address.lower()})
        pool = data.get("pool")
        
        if pool:
            # Calculate APR from fees
            pool["apr"] = self._calculate_apr(pool)
            self._cache_set(cache_key, pool)
        
        return pool
    
    async def get_pool_apy(self, pool_address: str) -> Optional[float]:
        """
        Get current APY for a pool.
        
        Combines:
        - Fee APR (from 24h volume)
        - Emissions APR (from gauge rewards)
        """
        pool = await self.get_pool_by_address(pool_address)
        if not pool:
            return None
        
        return pool.get("apr", 0)
    
    async def get_pool_daily_snapshots(
        self, 
        pool_address: str, 
        days: int = 7
    ) -> List[Dict]:
        """
        Get daily snapshots for APY history tracking.
        
        Returns list of daily data points.
        """
        query = """
        query GetPoolDayData($pool: String!, $first: Int!) {
            poolDayDatas(
                where: { pool: $pool }
                orderBy: date
                orderDirection: desc
                first: $first
            ) {
                id
                date
                volumeUSD
                feesUSD
                tvlUSD
                token0Price
                token1Price
            }
        }
        """
        
        data = await self._query(query, {
            "pool": pool_address.lower(),
            "first": days
        })
        
        snapshots = data.get("poolDayDatas", [])
        
        # Calculate APR for each day
        for snapshot in snapshots:
            tvl = float(snapshot.get("tvlUSD", 0))
            fees = float(snapshot.get("feesUSD", 0))
            if tvl > 0:
                snapshot["apr"] = (fees / tvl) * 365 * 100
            else:
                snapshot["apr"] = 0
        
        return snapshots
    
    async def get_pools_by_tokens(
        self, 
        token0: str = None, 
        token1: str = None,
        min_tvl: float = 100000,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get pools filtered by tokens and TVL.
        
        Useful for finding reinvestment options.
        """
        where_clause = f'totalValueLockedUSD_gt: "{min_tvl}"'
        if token0:
            where_clause += f', token0: "{token0.lower()}"'
        if token1:
            where_clause += f', token1: "{token1.lower()}"'
        
        query = f"""
        query GetPools {{
            pools(
                where: {{ {where_clause} }}
                orderBy: totalValueLockedUSD
                orderDirection: desc
                first: {limit}
            ) {{
                id
                name
                symbol
                token0 {{
                    id
                    symbol
                }}
                token1 {{
                    id
                    symbol
                }}
                totalValueLockedUSD
                volumeUSD
                feesUSD
                stable
                gauge {{
                    id
                    totalSupply
                    rewardRate
                }}
            }}
        }}
        """
        
        data = await self._query(query)
        pools = data.get("pools", [])
        
        # Calculate APR for each pool
        for pool in pools:
            pool["apr"] = self._calculate_apr(pool)
        
        return pools
    
    async def get_gauge_emissions(self, gauge_address: str) -> Dict:
        """
        Get gauge emissions data for calculating rewards APR.
        """
        query = """
        query GetGauge($id: ID!) {
            gauge(id: $id) {
                id
                totalSupply
                rewardRate
                pool {
                    id
                    totalValueLockedUSD
                }
            }
        }
        """
        
        data = await self._query(query, {"id": gauge_address.lower()})
        return data.get("gauge", {})
    
    def _calculate_apr(self, pool: Dict) -> float:
        """
        Calculate total APR from pool data.
        
        Components:
        - Fee APR: (daily_fees / tvl) * 365
        - Emissions APR: (reward_rate * aero_price / staked_tvl) * 365
        """
        try:
            tvl = float(pool.get("totalValueLockedUSD", 0))
            volume = float(pool.get("volumeUSD", 0))
            fees = float(pool.get("feesUSD", 0))
            
            if tvl <= 0:
                return 0
            
            # Estimate daily fees from total fees and volume
            # Assume 0.3% fee rate for volatile, 0.05% for stable
            is_stable = pool.get("stable", False)
            fee_rate = 0.0005 if is_stable else 0.003
            
            # If we have volume, calculate daily fee estimate
            # Assume volume is cumulative, estimate daily as volume/365
            daily_volume_estimate = volume / 365 if volume > 0 else 0
            daily_fees = daily_volume_estimate * fee_rate
            
            fee_apr = (daily_fees / tvl) * 365 * 100
            
            # Add emissions APR if gauge exists
            emissions_apr = 0
            gauge = pool.get("gauge")
            if gauge:
                reward_rate = float(gauge.get("rewardRate", 0))
                # AERO price estimate (update with oracle)
                aero_price = 1.0  # TODO: Get from price feed
                if reward_rate > 0:
                    daily_emissions = reward_rate * 86400 * aero_price / 1e18
                    emissions_apr = (daily_emissions / tvl) * 365 * 100
            
            return fee_apr + emissions_apr
        except Exception as e:
            logger.warning(f"[TheGraph] APR calculation error: {e}")
            return 0
    
    def _is_cached(self, key: str) -> bool:
        """Check if cache entry is valid"""
        if key not in self._cache_timestamps:
            return False
        age = (datetime.utcnow() - self._cache_timestamps[key]).total_seconds()
        return age < self._cache_ttl
    
    def _cache_set(self, key: str, value: Dict):
        """Set cache entry"""
        self._pool_cache[key] = value
        self._cache_timestamps[key] = datetime.utcnow()
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instance
graph_client = TheGraphClient()


async def get_pool_apy(pool_address: str) -> Optional[float]:
    """Convenience function to get pool APY"""
    return await graph_client.get_pool_apy(pool_address)


async def get_pool_history(pool_address: str, days: int = 7) -> List[Dict]:
    """Convenience function to get pool history"""
    return await graph_client.get_pool_daily_snapshots(pool_address, days)
