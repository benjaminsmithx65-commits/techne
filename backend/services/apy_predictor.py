"""
APY Predictor Service
Predicts APY trends using linear regression

Features:
- Record APY observations over time
- Linear regression for 24h prediction
- Trend detection (UP/DOWN/STABLE)
- Volatility assessment
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import deque

# APY history storage
# Format: {pool_id: deque([(timestamp, apy), ...])}
_apy_history: Dict[str, deque] = {}
MAX_HISTORY_POINTS = 288  # 24h at 5-min intervals


class APYPredictor:
    """
    Predicts APY trends using simple linear regression.
    
    Usage:
        predictor = APYPredictor()
        predictor.record_apy("pool_123", 15.5)
        prediction = predictor.predict_24h("pool_123")
        
        if prediction["trend"] == "DOWN":
            print("APY declining - consider exit")
    """
    
    def record_apy(self, pool_id: str, apy: float, timestamp: float = None):
        """Record an APY observation."""
        ts = timestamp or datetime.utcnow().timestamp()
        
        if pool_id not in _apy_history:
            _apy_history[pool_id] = deque(maxlen=MAX_HISTORY_POINTS)
        
        _apy_history[pool_id].append((ts, apy))
    
    def get_history(
        self, 
        pool_id: str, 
        hours: int = 24
    ) -> List[Tuple[float, float]]:
        """Get APY history for a pool."""
        if pool_id not in _apy_history:
            return []
        
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        
        return [(ts, apy) for ts, apy in _apy_history[pool_id] if ts >= cutoff]
    
    def predict_24h(self, pool_id: str) -> Dict[str, Any]:
        """
        Predict APY for the next 24 hours using linear regression.
        
        Returns:
            {
                "pool_id": "xxx",
                "current_apy": 15.5,
                "predicted_apy_24h": 14.2,
                "trend": "DOWN",
                "slope_per_hour": -0.054,
                "confidence": "HIGH",
                "volatility": 1.2,
                "recommendation": "HOLD" / "MONITOR" / "EXIT"
            }
        """
        history = self.get_history(pool_id, hours=24)
        
        if len(history) < 6:
            return {
                "pool_id": pool_id,
                "current_apy": history[-1][1] if history else None,
                "predicted_apy_24h": None,
                "trend": "UNKNOWN",
                "confidence": "LOW",
                "message": "Insufficient data (need 6+ observations)"
            }
        
        # Extract arrays
        timestamps = np.array([h[0] for h in history])
        apys = np.array([h[1] for h in history])
        
        # Normalize timestamps to hours
        timestamps_hours = (timestamps - timestamps.min()) / 3600
        
        # Linear regression
        slope, intercept = np.polyfit(timestamps_hours, apys, 1)
        
        # Predict 24h forward
        max_hour = timestamps_hours.max()
        predicted_24h = slope * (max_hour + 24) + intercept
        predicted_24h = max(0, predicted_24h)  # APY can't be negative
        
        # Current APY
        current_apy = apys[-1]
        
        # Calculate volatility (standard deviation)
        volatility = float(np.std(apys))
        
        # Trend determination
        change_24h = predicted_24h - current_apy
        change_pct = (change_24h / current_apy * 100) if current_apy > 0 else 0
        
        if change_pct > 5:
            trend = "UP"
        elif change_pct < -5:
            trend = "DOWN"
        else:
            trend = "STABLE"
        
        # Confidence based on data points and R²
        residuals = apys - (slope * timestamps_hours + intercept)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((apys - np.mean(apys)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        if len(history) > 50 and r_squared > 0.7:
            confidence = "HIGH"
        elif len(history) > 20 and r_squared > 0.5:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        # Recommendation
        if trend == "DOWN" and change_pct < -20:
            recommendation = "EXIT"
        elif trend == "DOWN" and change_pct < -10:
            recommendation = "MONITOR"
        else:
            recommendation = "HOLD"
        
        return {
            "pool_id": pool_id,
            "current_apy": round(current_apy, 2),
            "predicted_apy_24h": round(predicted_24h, 2),
            "change_24h_pct": round(change_pct, 2),
            "trend": trend,
            "slope_per_hour": round(slope, 4),
            "volatility": round(volatility, 2),
            "r_squared": round(r_squared, 4),
            "confidence": confidence,
            "data_points": len(history),
            "recommendation": recommendation
        }
    
    def get_moving_average(
        self, 
        pool_id: str, 
        hours: int = 6
    ) -> Optional[float]:
        """Get simple moving average APY."""
        history = self.get_history(pool_id, hours)
        
        if not history:
            return None
        
        apys = [h[1] for h in history]
        return sum(apys) / len(apys)
    
    def detect_apy_spike(
        self, 
        pool_id: str, 
        threshold_pct: float = 50
    ) -> Dict[str, Any]:
        """
        Detect sudden APY spikes (often temporary/unsustainable).
        
        Returns:
            {
                "has_spike": True,
                "spike_magnitude": 120%,
                "is_sustainable": False
            }
        """
        history = self.get_history(pool_id, hours=24)
        
        if len(history) < 12:
            return {"has_spike": False, "message": "Insufficient data"}
        
        # Compare recent (last 2h) to previous (2-24h ago)
        recent = [h[1] for h in history[-24:]]  # Last ~2h
        previous = [h[1] for h in history[:-24]] if len(history) > 24 else recent[:12]
        
        recent_avg = sum(recent) / len(recent) if recent else 0
        previous_avg = sum(previous) / len(previous) if previous else 0
        
        if previous_avg <= 0:
            return {"has_spike": False}
        
        change_pct = ((recent_avg - previous_avg) / previous_avg) * 100
        
        has_spike = change_pct > threshold_pct
        
        return {
            "has_spike": has_spike,
            "spike_magnitude_pct": round(change_pct, 2),
            "recent_apy": round(recent_avg, 2),
            "baseline_apy": round(previous_avg, 2),
            "is_sustainable": not has_spike,
            "warning": "APY spike detected - likely temporary" if has_spike else None
        }


# Global instance
_apy_predictor = None

def get_apy_predictor() -> APYPredictor:
    global _apy_predictor
    if _apy_predictor is None:
        _apy_predictor = APYPredictor()
    return _apy_predictor


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    import random
    
    print("="*60)
    print("APY Predictor Test")
    print("="*60)
    
    predictor = APYPredictor()
    
    # Simulate declining APY over 24h
    base_apy = 20.0
    now = datetime.utcnow().timestamp()
    
    for i in range(100):
        ts = now - (100 - i) * 300  # 5-min intervals going back
        # APY declines from 20% to ~15% with noise
        apy = base_apy - (i * 0.05) + random.uniform(-0.5, 0.5)
        predictor.record_apy("test_pool", apy, ts)
    
    # Predict
    result = predictor.predict_24h("test_pool")
    
    print(f"\n  Pool: {result['pool_id']}")
    print(f"  Current APY: {result['current_apy']}%")
    print(f"  Predicted 24h: {result['predicted_apy_24h']}%")
    print(f"  Change: {result['change_24h_pct']:.1f}%")
    print(f"  Trend: {result['trend']}")
    print(f"  Confidence: {result['confidence']} (R²={result['r_squared']:.2f})")
    print(f"  Volatility: ±{result['volatility']:.2f}%")
    print(f"  Recommendation: {result['recommendation']}")
    
    # Test spike detection
    print("\n  Spike Detection:")
    spike = predictor.detect_apy_spike("test_pool")
    print(f"    Has Spike: {spike['has_spike']}")
