"""
Historian Agent - "The Memory" of Artisan System
Historical data analysis, backtesting, trend detection

Responsibilities:
- Store and retrieve historical APY data
- Detect trends (rising/falling yields)
- Calculate historical performance metrics
- Support backtesting simulations
- Identify seasonal patterns
- Sync with Memory Engine for long-term trends
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

# Observability integration
try:
    from agents.observability_engine import observability, traced, SpanStatus
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):
        def decorator(func): return func
        return decorator

# Memory integration
try:
    from agents.memory_engine import memory_engine, MemoryType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HistorianAgent")


@dataclass
class HistoricalDataPoint:
    timestamp: datetime
    apy: float
    tvl: float
    volume_24h: Optional[float] = None


@dataclass
class TrendAnalysis:
    direction: str  # "rising", "falling", "stable"
    strength: float  # 0-1
    average_apy: float
    volatility: float
    prediction: str


@dataclass
class PoolHistory:
    pool_id: str
    symbol: str
    project: str
    data_points: List[HistoricalDataPoint] = field(default_factory=list)
    

class HistorianAgent:
    """
    The Historian - Historical Data and Trend Analysis Agent
    Remembers everything, predicts the future from the past
    """
    
    def __init__(self):
        # Historical data storage (in production, use database)
        self.pool_histories: Dict[str, PoolHistory] = {}
        
        # Protocol-level historical stats
        self.protocol_stats: Dict[str, Dict] = {}
        
        # Market snapshots
        self.market_snapshots: List[Dict] = []
        
        # Settings
        self.max_data_points = 1000  # Per pool
        self.snapshot_interval_hours = 6
        
    # ===========================================
    # DATA COLLECTION
    # ===========================================
    
    def record_pool_data(self, pool: Dict):
        """Record a data point for a pool"""
        pool_id = pool.get("pool")
        if not pool_id:
            return
        
        # Create history if doesn't exist
        if pool_id not in self.pool_histories:
            self.pool_histories[pool_id] = PoolHistory(
                pool_id=pool_id,
                symbol=pool.get("symbol", "Unknown"),
                project=pool.get("project", "Unknown")
            )
        
        # Add data point
        data_point = HistoricalDataPoint(
            timestamp=datetime.now(),
            apy=pool.get("apy", 0),
            tvl=pool.get("tvlUsd", 0),
            volume_24h=pool.get("volumeUsd24h")
        )
        
        history = self.pool_histories[pool_id]
        history.data_points.append(data_point)
        
        # Trim if too many
        if len(history.data_points) > self.max_data_points:
            history.data_points = history.data_points[-self.max_data_points:]
    
    def record_market_snapshot(self, pools: List[Dict]):
        """Record overall market state"""
        snapshot = {
            "timestamp": datetime.now(),
            "total_pools": len(pools),
            "total_tvl": sum(p.get("tvlUsd", 0) for p in pools),
            "average_apy": statistics.mean([p.get("apy", 0) for p in pools if p.get("apy", 0) > 0]) if pools else 0,
            "top_apy": max((p.get("apy", 0) for p in pools), default=0),
        }
        
        self.market_snapshots.append(snapshot)
        
        # Keep last 1000 snapshots
        if len(self.market_snapshots) > 1000:
            self.market_snapshots = self.market_snapshots[-1000:]
    
    # ===========================================
    # TREND ANALYSIS
    # ===========================================
    
    def analyze_pool_trend(self, pool_id: str, days: int = 7) -> Optional[TrendAnalysis]:
        """Analyze APY trend for a pool"""
        if pool_id not in self.pool_histories:
            return None
        
        history = self.pool_histories[pool_id]
        cutoff = datetime.now() - timedelta(days=days)
        
        recent_data = [
            dp for dp in history.data_points 
            if dp.timestamp >= cutoff
        ]
        
        if len(recent_data) < 3:
            return None
        
        apys = [dp.apy for dp in recent_data]
        
        # Calculate trend direction
        first_half = statistics.mean(apys[:len(apys)//2])
        second_half = statistics.mean(apys[len(apys)//2:])
        
        if second_half > first_half * 1.1:
            direction = "rising"
            strength = min((second_half - first_half) / first_half, 1.0)
        elif second_half < first_half * 0.9:
            direction = "falling"
            strength = min((first_half - second_half) / first_half, 1.0)
        else:
            direction = "stable"
            strength = 0.0
        
        # Calculate volatility
        volatility = statistics.stdev(apys) / statistics.mean(apys) if len(apys) > 1 else 0
        
        # Simple prediction
        if direction == "rising":
            prediction = f"APY likely to increase. Current trend shows {strength*100:.1f}% growth momentum."
        elif direction == "falling":
            prediction = f"APY declining. Consider exit if trend continues. Dropped {strength*100:.1f}% from peak."
        else:
            prediction = "APY stable. Good for long-term holding if yield meets target."
        
        return TrendAnalysis(
            direction=direction,
            strength=strength,
            average_apy=statistics.mean(apys),
            volatility=volatility,
            prediction=prediction
        )
    
    def find_rising_pools(self, pools: List[Dict], min_growth: float = 0.1) -> List[Dict]:
        """Find pools with rising APY trends"""
        rising = []
        
        for pool in pools:
            pool_id = pool.get("pool")
            trend = self.analyze_pool_trend(pool_id, days=7)
            
            if trend and trend.direction == "rising" and trend.strength >= min_growth:
                pool["trend"] = {
                    "direction": trend.direction,
                    "strength": trend.strength,
                    "prediction": trend.prediction
                }
                rising.append(pool)
        
        return sorted(rising, key=lambda p: p["trend"]["strength"], reverse=True)
    
    def find_stable_pools(self, pools: List[Dict], max_volatility: float = 0.1) -> List[Dict]:
        """Find pools with stable, consistent APY"""
        stable = []
        
        for pool in pools:
            pool_id = pool.get("pool")
            trend = self.analyze_pool_trend(pool_id, days=30)
            
            if trend and trend.volatility <= max_volatility:
                pool["stability_score"] = 1 - trend.volatility
                stable.append(pool)
        
        return sorted(stable, key=lambda p: p.get("stability_score", 0), reverse=True)
    
    def get_recent_average_apy(self, pool_id: str, hours: int = 12) -> Optional[float]:
        """
        Get average APY for the last N hours.
        Used for rotation trigger - if 12h average < min_apy, rotate out.
        """
        if pool_id not in self.pool_histories:
            return None
        
        history = self.pool_histories[pool_id]
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent_data = [
            dp for dp in history.data_points 
            if dp.timestamp >= cutoff
        ]
        
        if not recent_data:
            return None
        
        return statistics.mean([dp.apy for dp in recent_data])
    
    def check_below_min_apy(self, pool_id: str, min_apy: float, hours: int = 12) -> dict:
        """
        Check if pool's average APY has been below min_apy for the specified hours.
        Returns rotation recommendation.
        """
        avg_apy = self.get_recent_average_apy(pool_id, hours)
        
        if avg_apy is None:
            return {"should_rotate": False, "reason": "Insufficient data"}
        
        if avg_apy < min_apy:
            return {
                "should_rotate": True,
                "reason": f"12h average APY ({avg_apy:.2f}%) < min_apy ({min_apy}%)",
                "current_avg": avg_apy,
                "min_apy": min_apy,
                "hours_checked": hours
            }
        
        return {
            "should_rotate": False,
            "reason": f"APY OK: {avg_apy:.2f}% >= {min_apy}%",
            "current_avg": avg_apy
        }
    
    # ===========================================
    # HISTORICAL METRICS
    # ===========================================
    
    def get_pool_performance(self, pool_id: str, days: int = 30) -> Optional[Dict]:
        """Get historical performance metrics for a pool"""
        if pool_id not in self.pool_histories:
            return None
        
        history = self.pool_histories[pool_id]
        cutoff = datetime.now() - timedelta(days=days)
        
        data = [dp for dp in history.data_points if dp.timestamp >= cutoff]
        
        if not data:
            return None
        
        apys = [dp.apy for dp in data]
        tvls = [dp.tvl for dp in data]
        
        return {
            "pool_id": pool_id,
            "period_days": days,
            "data_points": len(data),
            "apy": {
                "current": apys[-1] if apys else 0,
                "average": statistics.mean(apys),
                "min": min(apys),
                "max": max(apys),
                "volatility": statistics.stdev(apys) if len(apys) > 1 else 0,
            },
            "tvl": {
                "current": tvls[-1] if tvls else 0,
                "average": statistics.mean(tvls),
                "growth": ((tvls[-1] - tvls[0]) / tvls[0] * 100) if tvls and tvls[0] > 0 else 0,
            }
        }
    
    def get_protocol_ranking(self, days: int = 30) -> List[Dict]:
        """Rank protocols by historical performance"""
        protocol_data = defaultdict(list)
        
        cutoff = datetime.now() - timedelta(days=days)
        
        for pool_id, history in self.pool_histories.items():
            recent_data = [dp for dp in history.data_points if dp.timestamp >= cutoff]
            if recent_data:
                avg_apy = statistics.mean([dp.apy for dp in recent_data])
                protocol_data[history.project].append({
                    "apy": avg_apy,
                    "tvl": recent_data[-1].tvl
                })
        
        rankings = []
        for protocol, pools in protocol_data.items():
            rankings.append({
                "protocol": protocol,
                "pool_count": len(pools),
                "average_apy": statistics.mean([p["apy"] for p in pools]),
                "total_tvl": sum(p["tvl"] for p in pools),
            })
        
        return sorted(rankings, key=lambda x: x["average_apy"], reverse=True)
    
    # ===========================================
    # BACKTESTING SUPPORT
    # ===========================================
    
    def get_historical_data(self, pool_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get historical data for backtesting"""
        if pool_id not in self.pool_histories:
            return []
        
        history = self.pool_histories[pool_id]
        
        return [
            {
                "timestamp": dp.timestamp.isoformat(),
                "apy": dp.apy,
                "tvl": dp.tvl,
                "volume_24h": dp.volume_24h
            }
            for dp in history.data_points
            if start_date <= dp.timestamp <= end_date
        ]
    
    def simulate_returns(self, pool_id: str, amount: float, days: int) -> Optional[Dict]:
        """Simulate historical returns"""
        perf = self.get_pool_performance(pool_id, days)
        if not perf:
            return None
        
        avg_daily_apy = perf["apy"]["average"] / 365
        
        # Simple compound calculation
        final_amount = amount
        for _ in range(days):
            final_amount *= (1 + avg_daily_apy / 100)
        
        return {
            "initial_amount": amount,
            "final_amount": final_amount,
            "profit": final_amount - amount,
            "return_percent": ((final_amount - amount) / amount) * 100,
            "days": days,
            "average_apy": perf["apy"]["average"]
        }
    
    # ===========================================
    # MARKET ANALYSIS
    # ===========================================
    
    def get_market_trend(self, days: int = 7) -> Dict:
        """Analyze overall market trend"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [s for s in self.market_snapshots if s["timestamp"] >= cutoff]
        
        if len(recent) < 2:
            return {"trend": "unknown", "data_points": len(recent)}
        
        first_avg = recent[0]["average_apy"]
        last_avg = recent[-1]["average_apy"]
        
        if last_avg > first_avg * 1.1:
            trend = "bull"
        elif last_avg < first_avg * 0.9:
            trend = "bear"
        else:
            trend = "sideways"
        
        return {
            "trend": trend,
            "apy_change": ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0,
            "tvl_change": ((recent[-1]["total_tvl"] - recent[0]["total_tvl"]) / recent[0]["total_tvl"] * 100) if recent[0]["total_tvl"] > 0 else 0,
            "data_points": len(recent)
        }


# Singleton
historian = HistorianAgent()
