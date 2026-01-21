"""
The Graph Integration for Pool Data
Fetches real-time TVL, APY, and pool metrics from DeFi protocol subgraphs.

Uses The Graph Network (decentralized) for reliable data.
"""

import aiohttp
import asyncio
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# The Graph Network endpoints for Base chain
# Format: https://gateway.thegraph.com/api/{API_KEY}/subgraphs/id/{SUBGRAPH_ID}
# Or hosted: https://api.thegraph.com/subgraphs/id/{SUBGRAPH_ID}

GRAPH_API_KEY = os.getenv("GRAPH_API_KEY", "")  # Optional, for higher rate limits

# Real subgraph IDs for Base chain protocols
SUBGRAPH_IDS = {
    "aave": "GQFbb95cE6d8mV989mL5figjaGaKCQB3xqYrr1bRyXqF",  # Aave V3 Base
    "compound": "5nwMCHGwBgLb9F8dG1FdWg9D7YkXHv9hKxQJ7qHxcDXk",  # Compound V3 Base
    "aerodrome": "GENunS3xbYe4qdS32cAQY5BsMhcZ4wKPzEkj1Av1UM",  # Aerodrome Base Full
    "moonwell": "ExCF5jPbKxQ6Fzng8qXPrhCuZNxZ9v7wLZFSR9qmq",  # Moonwell Base
    "uniswap": "43Hwfi3dJSoGpyas9VwNoDAv55yjgGrPCNzh76hKHKxd",  # Uniswap V3 Base
}

# Build full URLs
def _build_subgraph_url(protocol: str) -> str:
    subgraph_id = SUBGRAPH_IDS.get(protocol)
    if not subgraph_id:
        return ""
    
    if GRAPH_API_KEY:
        # Decentralized network (recommended for production)
        return f"https://gateway.thegraph.com/api/{GRAPH_API_KEY}/subgraphs/id/{subgraph_id}"
    else:
        # Hosted service (may have rate limits)
        return f"https://api.thegraph.com/subgraphs/id/{subgraph_id}"

SUBGRAPHS = {
    protocol: _build_subgraph_url(protocol)
    for protocol in SUBGRAPH_IDS.keys()
}

# Pool addresses we track on Base
TRACKED_POOLS = {
    # Aave V3 reserves
    "aave_usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC reserve
    "aave_weth": "0x4200000000000000000000000000000000000006",  # WETH reserve
    
    # Compound V3
    "compound_usdc": "0xb125E6687d4313864e53df431d5425969c15Eb2F",  # COMET USDC
    
    # Moonwell
    "moonwell_usdc": "0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22",  # mUSDC
    "moonwell_weth": "0x628ff693426583D9a7FB391E54366292F509D457",  # mWETH
    
    # Seamless (Fork of Aave)
    "seamless_usdc": "0x8E8673b4094882b9D4096a2E5A7f7F2D90e0B2a8",  # sUSDC
    
    # Aerodrome LP Pools
    "aerodrome_usdc_weth": "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d",  # USDC/WETH vAMM
    "aerodrome_usdc_cbeth": "0x44Ecc644449fC3a9858d2007CaA8CFAa4C561f91",  # USDC/cbETH
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
        import time
        from infrastructure.api_metrics import api_metrics
        
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
        
        start_time = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(subgraph_url, json={"query": query}) as resp:
                    response_time = time.time() - start_time
                    
                    if resp.status == 200:
                        api_metrics.record_call('thegraph', f'/{protocol}', 'success', response_time)
                        result = await resp.json()
                        return self._parse_response(protocol, result)
                    else:
                        api_metrics.record_call('thegraph', f'/{protocol}', 'error', response_time, 
                                               error_message=f"HTTP {resp.status}", status_code=resp.status)
                        print(f"[PoolDataFetcher] Subgraph returned {resp.status}")
                        return None
        except Exception as e:
            api_metrics.record_call('thegraph', f'/{protocol}', 'error', time.time() - start_time,
                                   error_message=str(e)[:200])
            raise
    
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
                
                # Cache to Supabase for historical tracking
                try:
                    from infrastructure.supabase_client import supabase
                    if supabase.is_available:
                        import asyncio
                        asyncio.create_task(supabase.save_pool_snapshot(
                            pool_name=pool_name,
                            protocol=protocol,
                            apy=data.get('apy', 0),
                            tvl=data.get('tvl', 0)
                        ))
                except Exception as e:
                    print(f"[PoolDataFetcher] Supabase cache failed: {e}")
        
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
