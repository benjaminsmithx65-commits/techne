"""
DexScreener API Client
Provides token price change data (5m, 1h, 6h, 24h) for each token in a pair
"""
import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("DexScreener")

# Chain ID mapping for DexScreener
CHAIN_MAP = {
    "base": "base",
    "ethereum": "ethereum",
    "arbitrum": "arbitrum",
    "optimism": "optimism", 
    "polygon": "polygon",
    "bsc": "bsc",
    "avalanche": "avalanche",
    "solana": "solana",
}


class DexScreenerClient:
    """Client for DexScreener API (free, no API key needed)"""
    
    BASE_URL = "https://api.dexscreener.com/latest/dex"
    
    def __init__(self):
        self.timeout = 10.0
        logger.info("📊 DexScreener client initialized")
    
    async def get_pair_data(self, chain: str, pair_address: str) -> Optional[Dict[str, Any]]:
        """
        Fetch pair data including price changes for both tokens.
        
        Args:
            chain: Chain name (e.g., 'base', 'ethereum')
            pair_address: Pool/pair contract address
            
        Returns:
            Dict with pair data including priceChange for m5, h1, h6, h24
        """
        chain_id = CHAIN_MAP.get(chain.lower(), chain.lower())
        url = f"{self.BASE_URL}/pairs/{chain_id}/{pair_address.lower()}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    logger.debug(f"DexScreener API error: {response.status_code}")
                    return None
                
                data = response.json()
                pair = data.get("pair") or (data.get("pairs", [{}])[0] if data.get("pairs") else None)
                
                if not pair:
                    logger.debug(f"No pair data found for {pair_address}")
                    return None
                
                return self._normalize_pair_data(pair)
                
        except Exception as e:
            logger.debug(f"DexScreener request failed: {e}")
            return None
    
    async def get_token_volatility(self, chain: str, pair_address: str) -> Dict[str, Any]:
        """
        Get volatility data (price changes) for both tokens in a pair.
        
        Returns:
            Dict with token0 and token1 volatility data:
            {
                "token0": {"symbol": "NOCK", "price_change_5m": X, "price_change_1h": X, "price_change_6h": X, "price_change_24h": X},
                "token1": {"symbol": "USDC", "price_change_5m": X, "price_change_1h": X, "price_change_6h": X, "price_change_24h": X},
                "pair_price_change_24h": X
            }
        """
        pair_data = await self.get_pair_data(chain, pair_address)
        
        if not pair_data:
            return {}
        
        price_change = pair_data.get("priceChange", {})
        base_token = pair_data.get("baseToken", {})
        quote_token = pair_data.get("quoteToken", {})
        
        # DexScreener's priceChange is for the pair (base token price in quote token terms)
        # We need to estimate individual token volatility
        # The pair price change reflects base token's relative performance to quote token
        
        return {
            "token0": {
                "symbol": base_token.get("symbol", "Token0"),
                "address": base_token.get("address", ""),
                "price_usd": float(pair_data.get("priceUsd", 0) or 0),
                "price_change_5m": float(price_change.get("m5", 0) or 0),
                "price_change_1h": float(price_change.get("h1", 0) or 0),
                "price_change_6h": float(price_change.get("h6", 0) or 0),
                "price_change_24h": float(price_change.get("h24", 0) or 0),
            },
            "token1": {
                "symbol": quote_token.get("symbol", "Token1"),
                "address": quote_token.get("address", ""),
                # Quote token (usually stablecoin) - assume stable
                "price_change_5m": 0,
                "price_change_1h": 0,
                "price_change_6h": 0,
                "price_change_24h": 0,
            },
            "pair_price_change_24h": float(price_change.get("h24", 0) or 0),
            "pair_price_change_6h": float(price_change.get("h6", 0) or 0),
            "pair_price_change_1h": float(price_change.get("h1", 0) or 0),
            "source": "dexscreener"
        }
    
    def _normalize_pair_data(self, pair: Dict) -> Dict[str, Any]:
        """Normalize DexScreener pair data to standard format"""
        price_change = pair.get("priceChange", {})
        
        return {
            "pairAddress": pair.get("pairAddress", ""),
            "baseToken": pair.get("baseToken", {}),
            "quoteToken": pair.get("quoteToken", {}),
            "priceNative": pair.get("priceNative"),
            "priceUsd": pair.get("priceUsd"),
            "txns": pair.get("txns", {}),
            "volume": pair.get("volume", {}),
            "priceChange": {
                "m5": float(price_change.get("m5", 0) or 0),
                "h1": float(price_change.get("h1", 0) or 0),
                "h6": float(price_change.get("h6", 0) or 0),
                "h24": float(price_change.get("h24", 0) or 0),
            },
            "liquidity": pair.get("liquidity", {}),
            "fdv": pair.get("fdv"),
            "pairCreatedAt": pair.get("pairCreatedAt"),
        }


# Singleton instance
dexscreener_client = DexScreenerClient()
