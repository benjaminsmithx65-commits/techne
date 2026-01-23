"""
Pyth Network Price Oracle Integration
Real-time prices with ~400ms latency for Base chain

Features:
- Direct on-chain price reads from Pyth contract
- 30-second staleness protection
- Price confidence intervals
- EMA prices for smoothing
"""

import os
import time
from typing import Optional, Dict, Any
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Pyth Network contract on Base (CORRECT ADDRESS!)
# Source: https://docs.pyth.network/price-feeds/contract-addresses/evm
PYTH_CONTRACT_ADDRESS = "0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a"

# Price feed IDs (Pyth format - 32 bytes)
PRICE_FEEDS = {
    "ETH/USD": "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace",
    "BTC/USD": "0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43",
    "USDC/USD": "0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a",
    "USDT/USD": "0x2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b",
}

# Pyth Price struct ABI
PYTH_ABI = [
    {
        "inputs": [{"name": "id", "type": "bytes32"}],
        "name": "getPrice",
        "outputs": [
            {
                "components": [
                    {"name": "price", "type": "int64"},
                    {"name": "conf", "type": "uint64"},
                    {"name": "expo", "type": "int32"},
                    {"name": "publishTime", "type": "uint256"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "id", "type": "bytes32"}],
        "name": "getEmaPrice",
        "outputs": [
            {
                "components": [
                    {"name": "price", "type": "int64"},
                    {"name": "conf", "type": "uint64"},
                    {"name": "expo", "type": "int32"},
                    {"name": "publishTime", "type": "uint256"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "id", "type": "bytes32"},
            {"name": "age", "type": "uint256"}
        ],
        "name": "getPriceNoOlderThan",
        "outputs": [
            {
                "components": [
                    {"name": "price", "type": "int64"},
                    {"name": "conf", "type": "uint64"},
                    {"name": "expo", "type": "int32"},
                    {"name": "publishTime", "type": "uint256"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ============================================
# CHAINLINK FALLBACK (More reliable on Base)
# ============================================
CHAINLINK_FEEDS = {
    "ETH/USD": "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",
    "BTC/USD": "0x64c911996D3c6aC71E9b8Ac06D99C0E63d67e7C6", 
    "USDC/USD": "0x7e860098F58bBFC8648a4311b374B1D669a2bc6B",
}

CHAINLINK_ABI = [
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"name": "roundId", "type": "uint80"},
            {"name": "answer", "type": "int256"},
            {"name": "startedAt", "type": "uint256"},
            {"name": "updatedAt", "type": "uint256"},
            {"name": "answeredInRound", "type": "uint80"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Default staleness threshold
MAX_PRICE_AGE_SECONDS = 30


class PythOracle:
    """
    Pyth Network price oracle client for Base chain.
    
    Usage:
        oracle = PythOracle()
        price = oracle.get_price("ETH/USD")
        
        if price["is_stale"]:
            raise ValueError("Price too old - cannot trade")
    """
    
    def __init__(self, rpc_url: str = None):
        self.rpc_url = rpc_url or os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(PYTH_CONTRACT_ADDRESS),
            abi=PYTH_ABI
        )
        
        print(f"[PythOracle] Connected to Base: {self.w3.is_connected()}")
    
    def get_price(
        self, 
        symbol: str, 
        max_age_seconds: int = None
    ) -> Dict[str, Any]:
        """
        Get real-time price from Pyth Network.
        
        Args:
            symbol: Price pair (e.g., "ETH/USD")
            max_age_seconds: Maximum allowed age (default 30s)
        
        Returns:
            {
                "symbol": "ETH/USD",
                "price": 3245.67,
                "confidence": 0.05,
                "publish_time": 1706123456,
                "age_seconds": 2.5,
                "is_stale": False,
                "source": "pyth"
            }
        """
        max_age = max_age_seconds or MAX_PRICE_AGE_SECONDS
        
        feed_id = PRICE_FEEDS.get(symbol)
        if not feed_id:
            return {
                "symbol": symbol,
                "error": f"Unknown price feed: {symbol}",
                "is_stale": True
            }
        
        try:
            # Get price from Pyth contract
            result = self.contract.functions.getPrice(feed_id).call()
            
            price_raw = result[0]  # int64
            conf_raw = result[1]   # uint64
            expo = result[2]       # int32 (negative exponent)
            publish_time = result[3]  # uint256
            
            # Convert to human-readable price
            price = price_raw * (10 ** expo)
            confidence = conf_raw * (10 ** expo)
            
            # Calculate age
            current_time = int(time.time())
            age_seconds = current_time - publish_time
            is_stale = age_seconds > max_age
            
            return {
                "symbol": symbol,
                "price": round(price, 6),
                "confidence": round(confidence, 6),
                "publish_time": publish_time,
                "age_seconds": round(age_seconds, 1),
                "is_stale": is_stale,
                "max_age": max_age,
                "source": "pyth"
            }
            
        except Exception as e:
            print(f"[PythOracle] Error getting price for {symbol}: {e}")
            # Fallback to Chainlink
            return self.get_chainlink_price(symbol, max_age)
    
    def get_chainlink_price(
        self,
        symbol: str,
        max_age_seconds: int = None
    ) -> Dict[str, Any]:
        """
        Get price from Chainlink (fallback when Pyth fails).
        More reliable but slightly slower (~1 min vs 400ms).
        """
        max_age = max_age_seconds or MAX_PRICE_AGE_SECONDS
        
        feed_address = CHAINLINK_FEEDS.get(symbol)
        if not feed_address:
            return {
                "symbol": symbol,
                "error": f"No Chainlink feed for: {symbol}",
                "is_stale": True,
                "source": "chainlink"
            }
        
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(feed_address),
                abi=CHAINLINK_ABI
            )
            
            decimals = contract.functions.decimals().call()
            data = contract.functions.latestRoundData().call()
            
            price = data[1] / (10 ** decimals)
            updated_at = data[3]
            
            current_time = int(time.time())
            age_seconds = current_time - updated_at
            is_stale = age_seconds > max_age
            
            return {
                "symbol": symbol,
                "price": round(price, 6),
                "confidence": price * 0.001,  # Chainlink ~0.1% confidence
                "publish_time": updated_at,
                "age_seconds": round(age_seconds, 1),
                "is_stale": is_stale,
                "max_age": max_age,
                "source": "chainlink"
            }
            
        except Exception as e:
            print(f"[PythOracle] Chainlink error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "is_stale": True,
                "source": "chainlink"
            }
    
    def get_ema_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get exponential moving average price (smoother, less volatile).
        """
        feed_id = PRICE_FEEDS.get(symbol)
        if not feed_id:
            return {"error": f"Unknown feed: {symbol}"}
        
        try:
            result = self.contract.functions.getEmaPrice(feed_id).call()
            
            price = result[0] * (10 ** result[2])
            
            return {
                "symbol": symbol,
                "ema_price": round(price, 6),
                "publish_time": result[3],
                "source": "pyth_ema"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_price_no_older_than(
        self, 
        symbol: str, 
        max_age_seconds: int = 30
    ) -> Optional[float]:
        """
        Get price only if it's fresher than max_age_seconds.
        Returns None if price is too old.
        
        Use this for critical trading decisions.
        """
        feed_id = PRICE_FEEDS.get(symbol)
        if not feed_id:
            return None
        
        try:
            result = self.contract.functions.getPriceNoOlderThan(
                feed_id, 
                max_age_seconds
            ).call()
            
            price = result[0] * (10 ** result[2])
            return round(price, 6)
            
        except Exception as e:
            # Pyth reverts if price is too old
            print(f"[PythOracle] Price too old or error: {e}")
            return None
    
    def is_price_fresh(self, symbol: str, max_age_seconds: int = 30) -> bool:
        """
        Check if price feed is fresh enough for trading.
        """
        price_data = self.get_price(symbol, max_age_seconds)
        return not price_data.get("is_stale", True)
    
    def get_all_prices(self) -> Dict[str, Dict]:
        """
        Get all tracked prices at once.
        """
        prices = {}
        for symbol in PRICE_FEEDS.keys():
            prices[symbol] = self.get_price(symbol)
        return prices


# Global singleton instance
_oracle_instance = None

def get_oracle() -> PythOracle:
    """Get or create Pyth oracle singleton."""
    global _oracle_instance
    if _oracle_instance is None:
        _oracle_instance = PythOracle()
    return _oracle_instance


# ============================================
# INTEGRATION WITH is_data_stale()
# ============================================

def is_price_stale(symbol: str = "ETH/USD", max_age_seconds: int = 30) -> tuple:
    """
    Check if price data is stale.
    
    Returns:
        (is_stale: bool, age_seconds: float, message: str)
    
    Usage:
        stale, age, msg = is_price_stale("ETH/USD")
        if stale:
            raise ValueError(f"Cannot trade: {msg}")
    """
    oracle = get_oracle()
    price_data = oracle.get_price(symbol, max_age_seconds)
    
    if "error" in price_data:
        return (True, float('inf'), f"Price error: {price_data['error']}")
    
    age = price_data.get("age_seconds", float('inf'))
    is_stale = price_data.get("is_stale", True)
    
    if is_stale:
        msg = f"Price stale: {symbol} is {age:.1f}s old (max {max_age_seconds}s)"
    else:
        msg = f"Price fresh: {symbol} is {age:.1f}s old"
    
    return (is_stale, age, msg)


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    print("="*60)
    print("Pyth Oracle Test")
    print("="*60)
    
    oracle = PythOracle()
    
    for symbol in ["ETH/USD", "BTC/USD", "USDC/USD"]:
        print(f"\n{symbol}:")
        price = oracle.get_price(symbol)
        
        if "error" in price:
            print(f"  Error: {price['error']}")
        else:
            print(f"  Price: ${price['price']:,.2f}")
            print(f"  Confidence: ±${price['confidence']:.4f}")
            print(f"  Age: {price['age_seconds']:.1f}s")
            print(f"  Stale: {price['is_stale']}")
    
    print("\n" + "="*60)
    print("Staleness Check:")
    stale, age, msg = is_price_stale("ETH/USD", 30)
    print(f"  {msg}")
    print("="*60)
