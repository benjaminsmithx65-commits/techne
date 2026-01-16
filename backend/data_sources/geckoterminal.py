"""
GeckoTerminal API Client
Provides real-time pool data (TVL, volume, prices) for DeFi pools
"""
import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("GeckoTerminal")

# Network mappings for GeckoTerminal
NETWORK_MAP = {
    # EVM chains
    "base": "base",
    "ethereum": "eth", 
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "polygon": "polygon_pos",
    "bsc": "bsc",
    "avalanche": "avax",
    # Non-EVM chains
    "solana": "solana",
}

class GeckoTerminalClient:
    """Client for GeckoTerminal API (free, no API key needed)"""
    
    BASE_URL = "https://api.geckoterminal.com/api/v2"
    
    def __init__(self):
        self.timeout = 15.0
        logger.info("🦎 GeckoTerminal client initialized")
    
    async def get_pool_by_address(self, chain: str, pool_address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch pool data by address from GeckoTerminal
        
        Args:
            chain: Chain name (e.g., 'base', 'ethereum')
            pool_address: Pool contract address (0x...)
            
        Returns:
            Pool data dict or None if not found
        """
        network = NETWORK_MAP.get(chain.lower(), chain.lower())
        # Solana addresses are case-sensitive (base58), EVM addresses are not
        address_for_url = pool_address if chain.lower() == "solana" else pool_address.lower()
        url = f"{self.BASE_URL}/networks/{network}/pools/{address_for_url}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                
                if response.status_code == 404:
                    logger.warning(f"Pool not found on GeckoTerminal: {pool_address}")
                    return None
                    
                if response.status_code != 200:
                    logger.error(f"GeckoTerminal API error: {response.status_code}")
                    return None
                
                data = response.json()
                pool_data = data.get("data", {})
                
                if not pool_data:
                    return None
                
                return self._normalize_pool_data(pool_data, chain)
                
        except Exception as e:
            logger.error(f"GeckoTerminal request failed: {e}")
            return None
    
    async def get_pool_ohlcv(self, chain: str, pool_address: str, timeframe: str = "day", limit: int = 7) -> Optional[Dict[str, Any]]:
        """
        Fetch OHLCV (price/volume history) data for a pool.
        Used to calculate TVL stability over time.
        
        Args:
            chain: Chain name (e.g., 'base', 'ethereum')
            pool_address: Pool contract address
            timeframe: 'day', 'hour', 'minute' 
            limit: Number of periods to fetch (default 7 for weekly)
            
        Returns:
            Dict with ohlcv_list and calculated changes
        """
        network = NETWORK_MAP.get(chain.lower(), chain.lower())
        address_for_url = pool_address if chain.lower() == "solana" else pool_address.lower()
        url = f"{self.BASE_URL}/networks/{network}/pools/{address_for_url}/ohlcv/{timeframe}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params={"limit": limit})
                
                if response.status_code != 200:
                    logger.debug(f"OHLCV fetch failed: {response.status_code}")
                    return None
                
                data = response.json()
                ohlcv_list = data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
                
                if not ohlcv_list or len(ohlcv_list) < 2:
                    return None
                
                # OHLCV format: [timestamp, open, high, low, close, volume]
                # Calculate price changes
                latest = ohlcv_list[0]  # Most recent
                day_ago = ohlcv_list[1] if len(ohlcv_list) > 1 else latest
                week_ago = ohlcv_list[-1] if len(ohlcv_list) >= 7 else ohlcv_list[-1]
                
                price_now = float(latest[4]) if latest[4] else 0  # close price
                price_24h = float(day_ago[4]) if day_ago[4] else 0
                price_7d = float(week_ago[4]) if week_ago[4] else 0
                
                # Calculate changes
                price_change_24h = ((price_now - price_24h) / price_24h * 100) if price_24h > 0 else 0
                price_change_7d = ((price_now - price_7d) / price_7d * 100) if price_7d > 0 else 0
                
                # Volume analysis
                volumes = [float(o[5]) for o in ohlcv_list if o[5]]
                avg_volume = sum(volumes) / len(volumes) if volumes else 0
                volume_now = volumes[0] if volumes else 0
                
                logger.info(f"OHLCV for {pool_address[:10]}: price_change_24h={price_change_24h:.2f}%, 7d={price_change_7d:.2f}%")
                
                return {
                    "price_change_24h": round(price_change_24h, 2),
                    "price_change_7d": round(price_change_7d, 2),
                    "volume_avg_7d": avg_volume,
                    "volume_24h": volume_now,
                    "price_high_7d": max([float(o[2]) for o in ohlcv_list if o[2]], default=0),
                    "price_low_7d": min([float(o[3]) for o in ohlcv_list if o[3]], default=0),
                    "data_points": len(ohlcv_list)
                }
                
        except Exception as e:
            logger.debug(f"OHLCV request failed: {e}")
            return None
    
    async def search_pool_by_tokens(
        self, 
        chain: str, 
        token0: str, 
        token1: str,
        dex: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Search for pool containing both tokens
        
        Args:
            chain: Chain name
            token0: First token address
            token1: Second token address
            dex: Optional DEX filter (e.g., 'aerodrome')
        """
        network = NETWORK_MAP.get(chain.lower(), chain.lower())
        
        # Search for pools containing token0
        url = f"{self.BASE_URL}/networks/{network}/tokens/{token0.lower()}/pools"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params={"page": 1})
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                pools = data.get("data", [])
                
                # Find pool that also contains token1
                token1_lower = token1.lower()
                for pool in pools:
                    attrs = pool.get("attributes", {})
                    pool_address = attrs.get("address", "")
                    
                    # Check relationships for token addresses
                    relationships = pool.get("relationships", {})
                    base_token = relationships.get("base_token", {}).get("data", {}).get("id", "")
                    quote_token = relationships.get("quote_token", {}).get("data", {}).get("id", "")
                    
                    # Token IDs format: "network_address"
                    if token1_lower in base_token.lower() or token1_lower in quote_token.lower():
                        # Optional: filter by DEX
                        if dex:
                            dex_id = relationships.get("dex", {}).get("data", {}).get("id", "")
                            if dex.lower() not in dex_id.lower():
                                continue
                        
                        logger.info(f"Found pool on GeckoTerminal: {attrs.get('name')}")
                        return self._normalize_pool_data(pool, chain)
                
                return None
                
        except Exception as e:
            logger.error(f"GeckoTerminal search failed: {e}")
            return None
    
    async def get_token_prices(self, chain: str, token_addresses: list) -> Optional[Dict[str, Any]]:
        """
        Fetch token prices with 24h price change for multiple tokens.
        Uses the simple token price endpoint with include_24hr_price_change.
        
        Args:
            chain: Chain name (e.g., 'base', 'ethereum')
            token_addresses: List of token contract addresses
            
        Returns:
            Dict mapping token address to {usd: price, price_change_24h: percent}
        """
        if not token_addresses:
            return {}
            
        network = NETWORK_MAP.get(chain.lower(), chain.lower())
        
        # Join addresses with comma (max 30 for public API)
        addresses_str = ",".join([addr.lower() for addr in token_addresses[:30]])
        url = f"{self.BASE_URL}/simple/networks/{network}/token_price/{addresses_str}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params={"include_24hr_price_change": "true"})
                
                if response.status_code != 200:
                    logger.debug(f"Token price fetch failed: {response.status_code}")
                    return {}
                
                data = response.json()
                token_data = data.get("data", {}).get("attributes", {}).get("token_prices", {})
                
                result = {}
                for addr, info in token_data.items():
                    if isinstance(info, dict):
                        result[addr.lower()] = {
                            "usd": float(info.get("usd", 0) or 0),
                            "price_change_24h": float(info.get("price_change_24h", 0) or 0)
                        }
                    elif isinstance(info, (int, float, str)):
                        # Simple price without change
                        result[addr.lower()] = {
                            "usd": float(info or 0),
                            "price_change_24h": 0
                        }
                
                logger.info(f"Token prices fetched for {len(result)} tokens on {chain}")
                return result
                
        except Exception as e:
            logger.debug(f"Token price request failed: {e}")
            return {}
    
    def _normalize_pool_data(self, pool_data: Dict, chain: str) -> Dict[str, Any]:
        """Convert GeckoTerminal format to our standard format"""
        attrs = pool_data.get("attributes", {})
        relationships = pool_data.get("relationships", {})
        
        # Parse reserve USD (TVL)
        reserve_usd = attrs.get("reserve_in_usd")
        tvl = float(reserve_usd) if reserve_usd else 0
        
        # Parse volume
        volume_24h = attrs.get("volume_usd", {}).get("h24")
        volume = float(volume_24h) if volume_24h else 0
        
        # Parse price change
        price_change_24h = attrs.get("price_change_percentage", {}).get("h24")
        
        # Get DEX name (project)
        dex_data = relationships.get("dex", {}).get("data", {})
        dex_id = dex_data.get("id", "")
        # Extract DEX name from ID format "network_dex-name"
        project = dex_id.split("_")[-1].replace("-", " ").title() if dex_id else "Unknown"
        
        # Calculate APY from fee data
        fee_24h = attrs.get("fee_24h_usd")
        apy_base = 0
        if fee_24h and tvl > 0:
            # Annualize 24h fees (fee_24h is trading fees collected)
            apy_base = (float(fee_24h) / tvl) * 365 * 100
        
        # Get trading fee percentage (if available)
        # Some pools have swap_fee or fee attribute
        trading_fee = None
        pool_name = attrs.get("name", "")
        
        # Extract fee from pool name if present (e.g., "WETH / cbBTC 0.05%")
        import re
        fee_match = re.search(r'(\d+\.?\d*)\s*%', pool_name)
        if fee_match:
            trading_fee = float(fee_match.group(1))
        
        # Extract token addresses from relationships
        # Format: "network_tokenaddress" e.g. "base_0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
        base_token_data = relationships.get("base_token", {}).get("data", {})
        quote_token_data = relationships.get("quote_token", {}).get("data", {})
        
        # Extract token address from ID (format: "network_address")
        base_token_id = base_token_data.get("id", "")
        quote_token_id = quote_token_data.get("id", "")
        
        # Parse address from ID - handle both EVM (0x...) and Solana (base58)
        token0 = ""
        token1 = ""
        if "_" in base_token_id:
            token0 = base_token_id.split("_", 1)[-1]  # Get everything after first underscore
        if "_" in quote_token_id:
            token1 = quote_token_id.split("_", 1)[-1]
        
        # Extract symbols from pool name (e.g., "SOL / USDC" -> symbol0="SOL", symbol1="USDC")
        symbol0, symbol1 = "", ""
        if " / " in pool_name:
            parts = pool_name.split(" / ")
            symbol0 = parts[0].strip().split()[0] if parts[0] else ""  # Get first word (ignore fee)
            symbol1 = parts[1].strip().split()[0] if len(parts) > 1 else ""
        
        return {
            "source": "geckoterminal",
            "address": attrs.get("address", ""),
            "name": attrs.get("name", ""),
            "symbol": attrs.get("name", "").replace(" / ", "-"),
            "project": project,
            "chain": chain.capitalize(),
            "tvlUsd": tvl,
            "tvl": tvl,
            "volume_24h": volume,
            "volume_24h_formatted": f"${volume/1e6:.2f}M" if volume >= 1e6 else f"${volume/1e3:.1f}K" if volume >= 1e3 else f"${volume:.0f}",
            "apy": apy_base,
            "apyBase": apy_base,
            "apyReward": 0,  # GeckoTerminal doesn't have reward APY
            "apy_base": apy_base,
            "apy_reward": 0,
            "priceChange24h": float(price_change_24h) if price_change_24h else 0,
            "baseTokenPrice": attrs.get("base_token_price_usd"),
            "quoteTokenPrice": attrs.get("quote_token_price_usd"),
            "trading_fee": trading_fee,
            "fee_24h_usd": float(fee_24h) if fee_24h else None,
            # Token addresses (for security checks)
            "token0": token0,
            "token1": token1,
            "symbol0": symbol0,
            "symbol1": symbol1,
            # IL risk based on pool type
            "il_risk": "yes",  # Most GeckoTerminal pools have IL risk (volatile pairs)
            "pool_type": "volatile",
            # Additional metadata
            "fdv_usd": attrs.get("fdv_usd"),
            "market_cap_usd": attrs.get("market_cap_usd"),
            "pool_created_at": attrs.get("pool_created_at"),
        }


# Singleton instance
gecko_client = GeckoTerminalClient()
