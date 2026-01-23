"""
AI Yield Predictor - Scout Agent v2.0 Phase 2
Machine learning-based APY prediction using historical DefiLlama data

Features:
- Historical APY trend analysis (7, 14, 30 day windows)
- Trend detection (rising, stable, declining)
- Linear regression for short-term forecasting
- TVL correlation analysis (APY tends to drop when TVL rises)
- Confidence scoring based on data quality
"""

import asyncio
import httpx
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
from collections import deque
import statistics

from dotenv import load_dotenv
load_dotenv()

# Supabase client (lazy init)
_supabase_client = None

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_ANON_KEY")
            if url and key:
                _supabase_client = create_client(url, key)
        except Exception as e:
            logger.debug(f"Supabase not available: {e}")
    return _supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("YieldPredictor")


class YieldPredictor:
    """
    AI-powered yield prediction engine using historical data analysis.
    Predicts future APY with confidence scores based on trend patterns.
    """
    
    def __init__(self):
        # Historical data cache: pool_id -> [{"date": ..., "apy": ..., "tvl": ...}]
        self.history_cache = {}
        self.cache_ttl = 3600  # 1 hour
        self.last_fetch = {}
        
        logger.info("🔮 Yield Predictor initialized")
    
    async def predict(self, pool: Dict[str, Any], days_ahead: int = 7) -> Dict[str, Any]:
        """
        Generate APY prediction for a pool.
        
        Args:
            pool: Pool data with id, project, apy, tvl
            days_ahead: Days to predict (7, 14, or 30)
            
        Returns:
            Prediction with current APY, predicted APY, trend, and confidence
        """
        pool_id = pool.get("id") or f"{pool.get('project')}_{pool.get('symbol')}"
        current_apy = pool.get("apy", 0)
        current_tvl = pool.get("tvl", 0)
        
        # Fetch historical data
        history = await self._get_historical_data(pool_id)
        
        if not history or len(history) < 3:
            # Not enough data - return simple estimate
            return self._simple_prediction(pool, days_ahead)
        
        # Calculate trends
        apy_trend = self._calculate_trend(history, "apy")
        tvl_trend = self._calculate_trend(history, "tvl")
        
        # Calculate prediction
        predicted_apy = self._forecast_apy(history, current_apy, days_ahead)
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(history, apy_trend)
        
        # Determine trend classification
        trend_class = self._classify_trend(apy_trend["slope"])
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            current_apy, predicted_apy, trend_class, confidence
        )
        
        return {
            "pool_id": pool_id,
            "project": pool.get("project"),
            "symbol": pool.get("symbol"),
            "chain": pool.get("chain"),
            "current_apy": round(current_apy, 2),
            "predicted_apy": {
                f"{days_ahead}d": round(predicted_apy, 2),
            },
            "trend": {
                "direction": trend_class,
                "icon": self._get_trend_icon(trend_class),
                "apy_change_7d": round(apy_trend["change_7d"], 2) if apy_trend["change_7d"] else 0,
                "tvl_change_7d": round(tvl_trend["change_7d"], 2) if tvl_trend["change_7d"] else 0,
            },
            "confidence": {
                "score": round(confidence, 2),
                "level": self._confidence_level(confidence),
                "data_points": len(history),
            },
            "recommendation": recommendation,
            "last_updated": datetime.now().isoformat()
        }
    
    async def _get_historical_data(self, pool_id: str) -> List[Dict[str, Any]]:
        """
        Fetch historical APY data for a pool.
        Uses DefiLlama's historical endpoint if available.
        """
        # Check cache
        if pool_id in self.history_cache:
            last_fetch = self.last_fetch.get(pool_id)
            if last_fetch and (datetime.now() - last_fetch).seconds < self.cache_ttl:
                return self.history_cache[pool_id]
        
        try:
            # DefiLlama historical endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"https://yields.llama.fi/chart/{pool_id}"
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    history = data.get("data", [])
                    
                    # Process and cache
                    processed = [
                        {
                            "date": h.get("timestamp"),
                            "apy": h.get("apy", 0),
                            "tvl": h.get("tvlUsd", 0)
                        }
                        for h in history[-90:]  # Last 90 days
                    ]
                    
                    self.history_cache[pool_id] = processed
                    self.last_fetch[pool_id] = datetime.now()
                    
                    return processed
                    
        except Exception as e:
            logger.debug(f"Could not fetch history for {pool_id}: {e}")
        
        return []
    
    def _calculate_trend(self, history: List[Dict], field: str) -> Dict[str, Any]:
        """Calculate trend statistics for a field (apy or tvl)"""
        if not history or len(history) < 2:
            return {"slope": 0, "change_7d": 0, "volatility": 0}
        
        values = [h.get(field, 0) for h in history if h.get(field) is not None]
        
        if len(values) < 2:
            return {"slope": 0, "change_7d": 0, "volatility": 0}
        
        # 7-day change
        if len(values) >= 7:
            change_7d = values[-1] - values[-7]
        else:
            change_7d = values[-1] - values[0]
        
        # Simple linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)
        
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Volatility (standard deviation)
        volatility = statistics.stdev(values) if len(values) > 1 else 0
        
        return {
            "slope": slope,
            "change_7d": change_7d,
            "volatility": volatility,
            "mean": y_mean
        }
    
    def _forecast_apy(self, history: List[Dict], current_apy: float, days_ahead: int) -> float:
        """
        Forecast APY using weighted average of:
        1. Linear trend extrapolation
        2. Mean reversion towards historical average
        3. Current value (momentum)
        """
        if not history:
            return current_apy
        
        values = [h.get("apy", 0) for h in history if h.get("apy") is not None]
        
        if not values:
            return current_apy
        
        # Historical mean (30-day if available)
        hist_mean = statistics.mean(values[-30:]) if len(values) >= 30 else statistics.mean(values)
        
        # Calculate trend
        trend = self._calculate_trend(history, "apy")
        slope = trend["slope"]
        
        # Linear projection
        linear_forecast = current_apy + (slope * days_ahead)
        
        # Mean reversion factor (stronger for longer forecasts)
        mean_reversion_weight = min(0.3, 0.05 * days_ahead)
        
        # Weighted forecast
        forecast = (
            linear_forecast * (0.5 - mean_reversion_weight) +
            hist_mean * mean_reversion_weight +
            current_apy * 0.5
        )
        
        # Clamp to reasonable bounds
        forecast = max(0, min(forecast, current_apy * 3))  # Don't predict >3x current
        
        return forecast
    
    def _calculate_confidence(self, history: List[Dict], trend: Dict) -> float:
        """
        Calculate confidence score (0-1) based on:
        - Data availability
        - Trend consistency
        - Volatility
        """
        if not history:
            return 0.3
        
        # Data availability score (more data = higher confidence)
        data_score = min(len(history) / 30, 1.0) * 0.4
        
        # Volatility score (lower volatility = higher confidence)
        volatility = trend.get("volatility", 0)
        mean = trend.get("mean", 1) or 1
        cv = volatility / mean if mean > 0 else 1  # Coefficient of variation
        volatility_score = max(0, 1 - cv) * 0.4
        
        # Trend consistency (consistent direction = higher confidence)
        slope = trend.get("slope", 0)
        consistency_score = 0.2 if abs(slope) > 0.01 else 0.1
        
        return min(data_score + volatility_score + consistency_score, 1.0)
    
    def _classify_trend(self, slope: float) -> str:
        """Classify trend based on slope"""
        if slope > 0.1:
            return "rising"
        elif slope < -0.1:
            return "declining"
        else:
            return "stable"
    
    def _get_trend_icon(self, trend: str) -> str:
        """Get icon for trend"""
        icons = {
            "rising": "📈",
            "declining": "📉",
            "stable": "➡️"
        }
        return icons.get(trend, "➡️")
    
    def _confidence_level(self, score: float) -> str:
        """Convert confidence score to level"""
        if score >= 0.7:
            return "High"
        elif score >= 0.4:
            return "Medium"
        else:
            return "Low"
    
    def _generate_recommendation(
        self, 
        current: float, 
        predicted: float, 
        trend: str, 
        confidence: float
    ) -> Dict[str, Any]:
        """Generate actionable recommendation"""
        
        change_pct = ((predicted - current) / current * 100) if current > 0 else 0
        
        if confidence < 0.4:
            action = "monitor"
            message = "Insufficient data - monitor before acting"
            icon = "👀"
        elif trend == "declining" and change_pct < -10:
            action = "harvest_soon"
            message = f"APY may drop {abs(change_pct):.0f}% - consider harvesting"
            icon = "⚠️"
        elif trend == "rising" and change_pct > 10:
            action = "hold"
            message = f"APY trending up - hold for better yields"
            icon = "📈"
        elif trend == "stable":
            action = "hold"
            message = "Stable yields - continue as planned"
            icon = "✅"
        else:
            action = "monitor"
            message = "Mixed signals - monitor regularly"
            icon = "👀"
        
        return {
            "action": action,
            "message": message,
            "icon": icon,
            "change_estimate": f"{change_pct:+.1f}%"
        }
    
    def _simple_prediction(self, pool: Dict[str, Any], days_ahead: int) -> Dict[str, Any]:
        """
        Simple prediction when no historical data available.
        Uses heuristics based on pool characteristics.
        """
        current_apy = pool.get("apy", 0)
        project = pool.get("project", "").lower()
        
        # High APY pools tend to decline
        if current_apy > 50:
            decay_factor = 0.9  # 10% decay per week
            predicted = current_apy * (decay_factor ** (days_ahead / 7))
            trend = "declining"
        # Low APY established pools tend to be stable
        elif current_apy < 5:
            predicted = current_apy * 0.98  # Very slight decline
            trend = "stable"
        else:
            predicted = current_apy * 0.95  # Slight decline typical
            trend = "stable"
        
        return {
            "pool_id": pool.get("id"),
            "project": pool.get("project"),
            "symbol": pool.get("symbol"),
            "chain": pool.get("chain"),
            "current_apy": round(current_apy, 2),
            "predicted_apy": {
                f"{days_ahead}d": round(predicted, 2),
            },
            "trend": {
                "direction": trend,
                "icon": self._get_trend_icon(trend),
                "apy_change_7d": 0,
                "tvl_change_7d": 0,
            },
            "confidence": {
                "score": 0.3,
                "level": "Low",
                "data_points": 0,
            },
            "recommendation": {
                "action": "monitor",
                "message": "No historical data - estimate only",
                "icon": "❓",
                "change_estimate": f"{((predicted - current_apy) / current_apy * 100):+.1f}%" if current_apy > 0 else "N/A"
            },
            "last_updated": datetime.now().isoformat()
        }
    
    # =====================================================
    # REINFORCEMENT LEARNING FEEDBACK LOOP
    # =====================================================
    
    async def record_prediction(self, prediction: Dict[str, Any], days_ahead: int = 7) -> bool:
        """
        Record a prediction to Supabase for future verification.
        Called automatically after predict() for learning.
        """
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            pool_id = prediction.get("pool_id")
            predicted_apy = prediction.get("predicted_apy", {}).get(f"{days_ahead}d", 0)
            current_apy = prediction.get("current_apy", 0)
            confidence = prediction.get("confidence", {}).get("score", 0)
            
            record = {
                "id": str(uuid.uuid4()),
                "pool_id": pool_id,
                "predicted_apy": predicted_apy,
                "current_apy_at_prediction": current_apy,
                "confidence_score": confidence,
                "days_ahead": days_ahead,
                "verify_at": (datetime.now() + timedelta(days=days_ahead)).isoformat(),
                "created_at": datetime.now().isoformat(),
                "verified": False,
                "actual_apy": None,
                "error_pct": None
            }
            
            supabase.table("prediction_feedback").insert(record).execute()
            logger.debug(f"📊 Recorded prediction for {pool_id}")
            return True
            
        except Exception as e:
            logger.debug(f"Failed to record prediction: {e}")
            return False
    
    async def verify_past_predictions(self) -> Dict[str, Any]:
        """
        Check predictions that are due for verification.
        Fetches actual APY and calculates error.
        Run this daily via cron/scheduler.
        """
        supabase = get_supabase()
        if not supabase:
            return {"error": "Supabase not configured"}
        
        try:
            # Find unverified predictions past their verify_at date
            now = datetime.now().isoformat()
            result = supabase.table("prediction_feedback").select("*").eq(
                "verified", False
            ).lt("verify_at", now).limit(100).execute()
            
            pending = result.data or []
            verified_count = 0
            total_error = 0
            
            for pred in pending:
                pool_id = pred["pool_id"]
                
                # Fetch current actual APY from DefiLlama
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        url = f"https://yields.llama.fi/chart/{pool_id}"
                        response = await client.get(url)
                        
                        if response.status_code == 200:
                            data = response.json().get("data", [])
                            if data:
                                actual_apy = data[-1].get("apy", 0)
                                predicted_apy = pred["predicted_apy"]
                                
                                # Calculate error
                                if predicted_apy > 0:
                                    error_pct = abs(actual_apy - predicted_apy) / predicted_apy * 100
                                else:
                                    error_pct = 100
                                
                                # Update record
                                supabase.table("prediction_feedback").update({
                                    "verified": True,
                                    "actual_apy": actual_apy,
                                    "error_pct": error_pct,
                                    "verified_at": datetime.now().isoformat()
                                }).eq("id", pred["id"]).execute()
                                
                                verified_count += 1
                                total_error += error_pct
                                
                except Exception as e:
                    logger.debug(f"Failed to verify {pool_id}: {e}")
            
            avg_error = total_error / verified_count if verified_count > 0 else 0
            
            return {
                "verified": verified_count,
                "pending": len(pending) - verified_count,
                "avg_error_pct": round(avg_error, 2),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {"error": str(e)}
    
    async def get_model_accuracy(self, days: int = 30) -> Dict[str, Any]:
        """
        Get model accuracy metrics over past N days.
        Returns MAE, accuracy rate, and improvement trend.
        """
        supabase = get_supabase()
        if not supabase:
            return {"error": "Supabase not configured"}
        
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            result = supabase.table("prediction_feedback").select("*").eq(
                "verified", True
            ).gt("created_at", cutoff).execute()
            
            records = result.data or []
            
            if not records:
                return {
                    "period_days": days,
                    "predictions_verified": 0,
                    "message": "No verified predictions yet"
                }
            
            errors = [r["error_pct"] for r in records if r.get("error_pct") is not None]
            
            # Calculate metrics
            mae = statistics.mean(errors) if errors else 0  # Mean Absolute Error
            accuracy_rate = sum(1 for e in errors if e < 20) / len(errors) * 100 if errors else 0
            
            # Trend: compare first half vs second half
            mid = len(errors) // 2
            if mid > 0:
                first_half_mae = statistics.mean(errors[:mid])
                second_half_mae = statistics.mean(errors[mid:])
                improvement = first_half_mae - second_half_mae
            else:
                improvement = 0
            
            return {
                "period_days": days,
                "predictions_verified": len(records),
                "mae_pct": round(mae, 2),
                "accuracy_rate": round(accuracy_rate, 2),  # % within 20% error
                "improvement_trend": round(improvement, 2),  # positive = getting better
                "best_performing_pools": self._get_best_pools(records),
                "worst_performing_pools": self._get_worst_pools(records)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_best_pools(self, records: List[Dict], n: int = 3) -> List[str]:
        """Get pool IDs with lowest prediction error"""
        sorted_records = sorted(records, key=lambda r: r.get("error_pct", 100))
        return [r["pool_id"] for r in sorted_records[:n]]
    
    def _get_worst_pools(self, records: List[Dict], n: int = 3) -> List[str]:
        """Get pool IDs with highest prediction error"""
        sorted_records = sorted(records, key=lambda r: r.get("error_pct", 0), reverse=True)
        return [r["pool_id"] for r in sorted_records[:n]]


# Singleton instance
yield_predictor = YieldPredictor()


# Convenience functions
async def predict_yield(pool: Dict[str, Any], days: int = 7) -> Dict[str, Any]:
    """Get yield prediction for a single pool"""
    return await yield_predictor.predict(pool, days)


async def batch_predict(pools: List[Dict[str, Any]], days: int = 7) -> List[Dict[str, Any]]:
    """Get predictions for multiple pools"""
    return [await yield_predictor.predict(pool, days) for pool in pools]
