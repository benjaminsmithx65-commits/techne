"""
Wash Trading Detection Service
Detects fake volume and artificial APY in liquidity pools

Features:
- Analyze swap patterns from The Graph
- Detect concentrated volume (few wallets = fake)
- Flag pools with "Fake Yield"
"""

import asyncio
import httpx
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime, timedelta

# Subgraph endpoints
AERODROME_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/aerodrome-finance/aerodrome-base"
UNISWAP_SUBGRAPH = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3-base"

# Swap query for Uniswap V3
UNISWAP_SWAPS_QUERY = """
{
  swaps(
    first: 1000,
    where: { pool: "%s", timestamp_gt: %s }
    orderBy: timestamp
    orderDirection: desc
  ) {
    id
    sender
    recipient
    amountUSD
    timestamp
  }
}
"""

# Swap query for Aerodrome
AERODROME_SWAPS_QUERY = """
{
  swaps(
    first: 1000,
    where: { pair: "%s", timestamp_gt: %s }
    orderBy: timestamp
    orderDirection: desc
  ) {
    id
    sender
    to
    amountUSD
    timestamp
  }
}
"""


class WashTradingDetector:
    """
    Detects wash trading (fake volume) in liquidity pools.
    
    Wash trading indicators:
    - Few addresses generate most volume
    - Circular trades (A→B→A)
    - Consistent trade sizes
    - High frequency from same addresses
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def query_subgraph(self, url: str, query: str) -> Dict[str, Any]:
        """Execute GraphQL query."""
        try:
            response = await self.client.post(
                url,
                json={"query": query},
                headers={"Content-Type": "application/json"}
            )
            return response.json() if response.status_code == 200 else {}
        except Exception as e:
            print(f"[WashDetector] Query error: {e}")
            return {}
    
    async def analyze_pool(
        self, 
        pool_address: str, 
        protocol: str = "uniswap_v3",
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze a pool for wash trading patterns.
        
        Returns:
            {
                "pool": "0x...",
                "is_wash_trading": True/False,
                "concentration_score": 0.85,  # 0-1, higher = more concentrated
                "unique_traders": 15,
                "top_3_volume_pct": 82.5,
                "apy_validity": "FAKE" / "REAL" / "SUSPICIOUS",
                "red_flags": [...]
            }
        """
        # Calculate timestamp for lookback
        since = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
        
        # Select query based on protocol
        if protocol == "aerodrome":
            query = AERODROME_SWAPS_QUERY % (pool_address.lower(), since)
            subgraph = AERODROME_SUBGRAPH
            sender_key = "sender"
        else:
            query = UNISWAP_SWAPS_QUERY % (pool_address.lower(), since)
            subgraph = UNISWAP_SUBGRAPH
            sender_key = "sender"
        
        result = await self.query_subgraph(subgraph, query)
        swaps = result.get("data", {}).get("swaps", [])
        
        if not swaps:
            return {
                "pool": pool_address,
                "is_wash_trading": False,
                "concentration_score": 0,
                "unique_traders": 0,
                "top_3_volume_pct": 0,
                "apy_validity": "UNKNOWN",
                "red_flags": ["No swap data available"],
                "total_volume_usd": 0
            }
        
        # Analyze volume distribution
        volume_by_address: Dict[str, float] = defaultdict(float)
        trade_count_by_address: Dict[str, int] = defaultdict(int)
        trade_sizes: List[float] = []
        
        total_volume = 0
        
        for swap in swaps:
            sender = swap.get(sender_key, "").lower()
            amount = float(swap.get("amountUSD", 0) or 0)
            
            if sender and amount > 0:
                volume_by_address[sender] += amount
                trade_count_by_address[sender] += 1
                trade_sizes.append(amount)
                total_volume += amount
        
        # Calculate metrics
        unique_traders = len(volume_by_address)
        
        if total_volume == 0 or unique_traders == 0:
            return {
                "pool": pool_address,
                "is_wash_trading": False,
                "concentration_score": 0,
                "unique_traders": 0,
                "top_3_volume_pct": 0,
                "apy_validity": "UNKNOWN",
                "red_flags": ["No volume"],
                "total_volume_usd": 0
            }
        
        # Sort by volume
        sorted_volumes = sorted(volume_by_address.values(), reverse=True)
        
        # Top 3 concentration
        top_3_volume = sum(sorted_volumes[:3])
        top_3_pct = (top_3_volume / total_volume) * 100
        
        # Top 1 concentration
        top_1_pct = (sorted_volumes[0] / total_volume) * 100 if sorted_volumes else 0
        
        # Concentration score (0-1)
        concentration = top_3_pct / 100
        
        # Detect red flags
        red_flags = []
        
        if top_3_pct > 80:
            red_flags.append(f"Top 3 addresses control {top_3_pct:.1f}% of volume")
        
        if top_1_pct > 50:
            red_flags.append(f"Single address controls {top_1_pct:.1f}% of volume")
        
        if unique_traders < 5:
            red_flags.append(f"Only {unique_traders} unique traders in {hours}h")
        
        # Check for consistent trade sizes (bot behavior)
        if trade_sizes:
            avg_size = sum(trade_sizes) / len(trade_sizes)
            variance = sum((s - avg_size) ** 2 for s in trade_sizes) / len(trade_sizes)
            std_dev = variance ** 0.5
            cv = std_dev / avg_size if avg_size > 0 else 0
            
            if cv < 0.1:  # Very consistent sizes
                red_flags.append("Trade sizes suspiciously consistent (bot pattern)")
        
        # Check for high frequency from same addresses
        max_trades = max(trade_count_by_address.values()) if trade_count_by_address else 0
        if max_trades > 50:
            red_flags.append(f"Single address made {max_trades} trades")
        
        # Determine verdict
        is_wash = top_3_pct > 80 or (top_1_pct > 50 and unique_traders < 10)
        
        if is_wash:
            apy_validity = "FAKE"
        elif top_3_pct > 60 or len(red_flags) >= 2:
            apy_validity = "SUSPICIOUS"
        else:
            apy_validity = "REAL"
        
        return {
            "pool": pool_address,
            "protocol": protocol,
            "is_wash_trading": is_wash,
            "concentration_score": round(concentration, 4),
            "unique_traders": unique_traders,
            "total_trades": len(swaps),
            "top_1_volume_pct": round(top_1_pct, 2),
            "top_3_volume_pct": round(top_3_pct, 2),
            "total_volume_usd": round(total_volume, 2),
            "apy_validity": apy_validity,
            "red_flags": red_flags,
            "analysis_period_hours": hours
        }
    
    async def close(self):
        await self.client.aclose()


# Global instance
_wash_detector = None

def get_wash_detector() -> WashTradingDetector:
    global _wash_detector
    if _wash_detector is None:
        _wash_detector = WashTradingDetector()
    return _wash_detector


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("="*60)
        print("Wash Trading Detector Test")
        print("="*60)
        
        detector = WashTradingDetector()
        
        # Test with a real Uniswap V3 pool (USDC/WETH)
        pool = "0xd0b53d9277642d899df5c87a3966a349a798f224"  # Example pool
        
        print(f"\nAnalyzing pool: {pool[:10]}...")
        
        result = await detector.analyze_pool(pool, "uniswap_v3", hours=24)
        
        print(f"\n  Wash Trading: {result['is_wash_trading']}")
        print(f"  APY Validity: {result['apy_validity']}")
        print(f"  Unique Traders: {result['unique_traders']}")
        print(f"  Top 3 Volume %: {result['top_3_volume_pct']:.1f}%")
        print(f"  Total Volume: ${result['total_volume_usd']:,.2f}")
        
        if result["red_flags"]:
            print(f"\n  🚩 Red Flags:")
            for flag in result["red_flags"]:
                print(f"    - {flag}")
        
        await detector.close()
    
    asyncio.run(test())
