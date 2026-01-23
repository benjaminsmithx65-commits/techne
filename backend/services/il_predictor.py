"""
IL Divergence Predictor
Predicts Impermanent Loss risk based on token price correlation

Features:
- Track price correlation between token pairs
- Detect correlation breakdown (divergence)
- Predict IL risk before it happens
- Suggest early exit when correlation drops
"""

import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque

# In-memory price history storage
# Format: {token_address: deque([(timestamp, price), ...])}
_price_history: Dict[str, deque] = {}
MAX_HISTORY_POINTS = 288  # 24h at 5-min intervals


class ILDivergencePredictor:
    """
    Predicts Impermanent Loss risk by monitoring token correlation.
    
    When correlation drops below historical norms, IL risk increases.
    
    Usage:
        predictor = ILDivergencePredictor()
        risk = await predictor.analyze_pair("WETH", "TOKEN")
        
        if risk["divergence_risk"] == "HIGH":
            print("Exit early - IL risk increasing!")
    """
    
    def __init__(self):
        self.correlation_cache: Dict[str, float] = {}
        self.historical_correlations: Dict[str, List[float]] = {}
    
    def record_price(self, token: str, price: float, timestamp: float = None):
        """Record a price observation for correlation tracking."""
        token = token.upper()
        ts = timestamp or datetime.utcnow().timestamp()
        
        if token not in _price_history:
            _price_history[token] = deque(maxlen=MAX_HISTORY_POINTS)
        
        _price_history[token].append((ts, price))
    
    def get_price_series(
        self, 
        token: str, 
        hours: int = 24
    ) -> Tuple[List[float], List[float]]:
        """Get price series for a token."""
        token = token.upper()
        
        if token not in _price_history:
            return [], []
        
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        
        timestamps = []
        prices = []
        
        for ts, price in _price_history[token]:
            if ts >= cutoff:
                timestamps.append(ts)
                prices.append(price)
        
        return timestamps, prices
    
    def calculate_correlation(
        self, 
        token_a: str, 
        token_b: str, 
        hours: int = 24
    ) -> Optional[float]:
        """
        Calculate Pearson correlation between two tokens.
        
        Returns:
            Correlation coefficient (-1 to 1), or None if insufficient data
        """
        _, prices_a = self.get_price_series(token_a, hours)
        _, prices_b = self.get_price_series(token_b, hours)
        
        # Align series (use minimum length)
        min_len = min(len(prices_a), len(prices_b))
        
        if min_len < 10:
            return None  # Insufficient data
        
        prices_a = prices_a[-min_len:]
        prices_b = prices_b[-min_len:]
        
        # Calculate Pearson correlation
        try:
            correlation = np.corrcoef(prices_a, prices_b)[0, 1]
            return float(correlation) if not np.isnan(correlation) else None
        except Exception:
            return None
    
    def calculate_rolling_correlation(
        self,
        token_a: str,
        token_b: str,
        window_hours: int = 6,
        step_hours: int = 1
    ) -> List[Tuple[float, float]]:
        """Calculate rolling correlation over time."""
        _, prices_a = self.get_price_series(token_a, 24)
        _, prices_b = self.get_price_series(token_b, 24)
        
        min_len = min(len(prices_a), len(prices_b))
        if min_len < 20:
            return []
        
        prices_a = prices_a[-min_len:]
        prices_b = prices_b[-min_len:]
        
        window_size = window_hours * 12  # Assuming 5-min intervals
        step_size = step_hours * 12
        
        correlations = []
        
        for i in range(0, len(prices_a) - window_size, step_size):
            subset_a = prices_a[i:i+window_size]
            subset_b = prices_b[i:i+window_size]
            
            try:
                corr = np.corrcoef(subset_a, subset_b)[0, 1]
                if not np.isnan(corr):
                    correlations.append((i / 12, float(corr)))  # (hours from start, correlation)
            except Exception:
                continue
        
        return correlations
    
    async def analyze_pair(
        self,
        token_a: str,
        token_b: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze a token pair for divergence risk.
        
        Returns:
            {
                "pair": "WETH/TOKEN",
                "current_correlation": 0.85,
                "historical_avg": 0.95,
                "correlation_drop": 10.5%,
                "divergence_risk": "LOW" / "MEDIUM" / "HIGH",
                "predicted_il_increase": 2.5%,
                "recommendation": "HOLD" / "MONITOR" / "EXIT_EARLY"
            }
        """
        pair_key = f"{token_a.upper()}/{token_b.upper()}"
        
        # Calculate current correlation
        current_corr = self.calculate_correlation(token_a, token_b, hours)
        
        if current_corr is None:
            return {
                "pair": pair_key,
                "current_correlation": None,
                "divergence_risk": "UNKNOWN",
                "recommendation": "INSUFFICIENT_DATA",
                "message": "Not enough price history"
            }
        
        # Get historical average (use longer period if available)
        historical_corr = self.calculate_correlation(token_a, token_b, hours * 2)
        if historical_corr is None:
            historical_corr = current_corr
        
        # Store in history for trend analysis
        if pair_key not in self.historical_correlations:
            self.historical_correlations[pair_key] = []
        self.historical_correlations[pair_key].append(current_corr)
        
        # Keep last 50 observations
        if len(self.historical_correlations[pair_key]) > 50:
            self.historical_correlations[pair_key] = self.historical_correlations[pair_key][-50:]
        
        # Calculate average historical correlation
        avg_historical = sum(self.historical_correlations[pair_key]) / len(self.historical_correlations[pair_key])
        
        # Calculate correlation drop
        corr_drop_pct = ((avg_historical - current_corr) / avg_historical) * 100 if avg_historical > 0 else 0
        
        # Predict IL increase based on correlation breakdown
        # IL formula factor: lower correlation = higher potential IL
        predicted_il_factor = max(0, (1 - current_corr) * 50)  # Rough estimate
        
        # Determine risk level
        if corr_drop_pct > 30 or current_corr < 0.5:
            divergence_risk = "HIGH"
            recommendation = "EXIT_EARLY"
        elif corr_drop_pct > 15 or current_corr < 0.7:
            divergence_risk = "MEDIUM"
            recommendation = "MONITOR"
        else:
            divergence_risk = "LOW"
            recommendation = "HOLD"
        
        return {
            "pair": pair_key,
            "current_correlation": round(current_corr, 4),
            "historical_avg_correlation": round(avg_historical, 4),
            "correlation_drop_pct": round(corr_drop_pct, 2),
            "divergence_risk": divergence_risk,
            "predicted_il_factor": round(predicted_il_factor, 2),
            "recommendation": recommendation,
            "data_points": len(self.historical_correlations[pair_key]),
            "analysis_period_hours": hours
        }
    
    def estimate_il_from_price_change(
        self,
        initial_price_a: float,
        initial_price_b: float,
        current_price_a: float,
        current_price_b: float
    ) -> Dict[str, float]:
        """
        Estimate IL from price changes.
        
        Standard IL formula:
        IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
        """
        if initial_price_a <= 0 or initial_price_b <= 0:
            return {"il_percent": 0, "price_ratio": 1}
        
        # Calculate price ratio change
        initial_ratio = initial_price_a / initial_price_b
        current_ratio = current_price_a / current_price_b
        
        k = current_ratio / initial_ratio
        
        # IL formula
        lp_value_ratio = 2 * np.sqrt(k) / (1 + k)
        il_percent = (1 - lp_value_ratio) * 100
        
        return {
            "il_percent": round(il_percent, 4),
            "price_ratio_change": round(k, 4),
            "lp_vs_hodl_ratio": round(lp_value_ratio, 4)
        }


# Global instance
_il_predictor = None

def get_il_predictor() -> ILDivergencePredictor:
    global _il_predictor
    if _il_predictor is None:
        _il_predictor = ILDivergencePredictor()
    return _il_predictor


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("="*60)
        print("IL Divergence Predictor Test")
        print("="*60)
        
        predictor = ILDivergencePredictor()
        
        # Simulate price history
        import random
        
        base_eth = 3000
        base_token = 1.0
        
        for i in range(100):
            # ETH follows a smooth trend
            eth_price = base_eth + (i * 10) + random.uniform(-50, 50)
            
            # Token starts correlated, then diverges
            if i < 50:
                token_price = base_token + (i * 0.01) + random.uniform(-0.02, 0.02)
            else:
                # Token diverges
                token_price = base_token + random.uniform(-0.2, 0.05)
            
            predictor.record_price("WETH", eth_price)
            predictor.record_price("TOKEN", token_price)
        
        # Analyze
        result = await predictor.analyze_pair("WETH", "TOKEN", hours=24)
        
        print(f"\n  Pair: {result['pair']}")
        print(f"  Current Correlation: {result['current_correlation']}")
        print(f"  Historical Avg: {result['historical_avg_correlation']}")
        print(f"  Correlation Drop: {result['correlation_drop_pct']:.1f}%")
        print(f"  Divergence Risk: {result['divergence_risk']}")
        print(f"  Recommendation: {result['recommendation']}")
        
        # Test IL calculation
        il = predictor.estimate_il_from_price_change(
            3000, 1.0,  # Initial
            4000, 0.8   # Current (ETH up, token down)
        )
        print(f"\n  Estimated IL from price change: {il['il_percent']:.2f}%")
    
    asyncio.run(test())
