"""
Risk Manager
Enforces risk limits from Pro Mode frontend settings
Handles: Position sizing, Stop-Loss, Take-Profit, Volatility Guard
"""

import os
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# Import price feed for volatility detection
try:
    import httpx
except ImportError:
    httpx = None


@dataclass
class RiskLimits:
    """Risk limits from Pro Mode config"""
    # Position Sizing
    max_allocation_percent: float = 25.0
    max_per_pool_percent: float = 10.0
    
    # Stop Loss
    stop_loss_enabled: bool = True
    stop_loss_percent: float = 15.0
    
    # Take Profit
    take_profit_enabled: bool = False
    take_profit_amount: float = 500.0
    
    # Volatility Guard
    volatility_guard_enabled: bool = True
    volatility_threshold: float = 10.0  # % daily price change
    
    # MEV Protection
    mev_protection: bool = True
    
    # Gas Strategy
    gas_strategy: str = "smart"  # "smart", "fast", "cheap"
    max_gas_gwei: float = 50.0


class RiskManager:
    """
    Manages risk for agent positions
    
    Features:
    - Position sizing based on pool TVL
    - Stop-loss monitoring and auto-exit
    - Take-profit triggers
    - Volatility guard (pause on high vol)
    - Price monitoring
    """
    
    def __init__(self):
        self.positions: Dict[str, Dict] = {}
        self.price_cache: Dict[str, float] = {}
        self.price_cache_time: Dict[str, datetime] = {}
        self.alerts: List[Dict] = []
        
        # Coingecko for price data
        self.price_api = "https://api.coingecko.com/api/v3"
        
    def parse_pro_config(self, pro_config: Optional[Dict]) -> RiskLimits:
        """Parse Pro Mode config from frontend into RiskLimits"""
        limits = RiskLimits()
        
        if not pro_config:
            return limits
        
        # Stop Loss
        limits.stop_loss_enabled = pro_config.get("stopLossEnabled", True)
        limits.stop_loss_percent = pro_config.get("stopLossPercent", 15)
        
        # Take Profit
        limits.take_profit_enabled = pro_config.get("takeProfitEnabled", False)
        limits.take_profit_amount = pro_config.get("takeProfitAmount", 500)
        
        # Volatility Guard
        limits.volatility_guard_enabled = pro_config.get("volatilityGuard", True)
        limits.volatility_threshold = pro_config.get("volatilityThreshold", 10)
        
        # MEV Protection
        limits.mev_protection = pro_config.get("mevProtection", True)
        
        # Gas Strategy
        limits.gas_strategy = pro_config.get("gasStrategy", "smart")
        gas_map = {"cheap": 30, "smart": 50, "fast": 100}
        limits.max_gas_gwei = gas_map.get(limits.gas_strategy, 50)
        
        return limits
    
    def calculate_position_size(
        self,
        total_capital: float,
        pool_tvl: float,
        agent_config: Dict
    ) -> float:
        """
        Calculate safe position size based on capital and pool TVL
        
        Rules:
        - Max 25% of capital per pool (from agent config)
        - Max 0.5% of pool TVL (to avoid slippage/impact)
        - Gas cost must be < 1% of position
        """
        max_allocation = agent_config.get("max_allocation", 25) / 100
        
        # Rule 1: Max percent of capital
        capital_limit = total_capital * max_allocation
        
        # Rule 2: Max 0.5% of pool TVL
        tvl_limit = pool_tvl * 0.005
        
        # Use minimum of limits
        safe_size = min(capital_limit, tvl_limit)
        
        # Rule 3: Minimum position = $50 (gas efficiency)
        if safe_size < 50:
            safe_size = 0  # Skip too-small positions
        
        return safe_size
    
    async def check_stop_loss(
        self,
        agent: Dict,
        position: Dict
    ) -> Dict:
        """
        Check if position should be stopped due to loss
        
        Returns:
            {should_exit: bool, reason: str, loss_percent: float}
        """
        limits = self.parse_pro_config(agent.get("pro_config"))
        
        if not limits.stop_loss_enabled:
            return {"should_exit": False, "reason": "Stop-loss disabled"}
        
        entry_value = position.get("entry_value", 0)
        current_value = position.get("current_value", entry_value)
        
        if entry_value <= 0:
            return {"should_exit": False, "reason": "No entry value"}
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        
        if loss_percent >= limits.stop_loss_percent:
            return {
                "should_exit": True,
                "reason": f"Stop-loss triggered: -{loss_percent:.1f}% >= -{limits.stop_loss_percent}%",
                "loss_percent": loss_percent
            }
        
        return {
            "should_exit": False,
            "reason": f"Loss {loss_percent:.1f}% below threshold {limits.stop_loss_percent}%",
            "loss_percent": loss_percent
        }
    
    async def check_take_profit(
        self,
        agent: Dict,
        position: Dict
    ) -> Dict:
        """
        Check if position should be closed for profit taking
        
        Returns:
            {should_exit: bool, reason: str, profit: float}
        """
        limits = self.parse_pro_config(agent.get("pro_config"))
        
        if not limits.take_profit_enabled:
            return {"should_exit": False, "reason": "Take-profit disabled"}
        
        entry_value = position.get("entry_value", 0)
        current_value = position.get("current_value", entry_value)
        
        profit = current_value - entry_value
        
        if profit >= limits.take_profit_amount:
            return {
                "should_exit": True,
                "reason": f"Take-profit triggered: ${profit:.2f} >= ${limits.take_profit_amount}",
                "profit": profit
            }
        
        return {
            "should_exit": False,
            "reason": f"Profit ${profit:.2f} below target ${limits.take_profit_amount}",
            "profit": profit
        }
    
    async def check_volatility(
        self,
        agent: Dict,
        token_symbol: str
    ) -> Dict:
        """
        Check if market volatility is too high
        
        Returns:
            {should_pause: bool, reason: str, volatility: float}
        """
        limits = self.parse_pro_config(agent.get("pro_config"))
        
        if not limits.volatility_guard_enabled:
            return {"should_pause": False, "reason": "Volatility guard disabled"}
        
        # Get 24h price change
        volatility = await self._get_24h_volatility(token_symbol)
        
        if volatility >= limits.volatility_threshold:
            return {
                "should_pause": True,
                "reason": f"⚠️ High volatility: {volatility:.1f}% >= {limits.volatility_threshold}%",
                "volatility": volatility
            }
        
        return {
            "should_pause": False,
            "reason": f"Volatility OK: {volatility:.1f}%",
            "volatility": volatility
        }
    
    async def _get_24h_volatility(self, symbol: str) -> float:
        """Get 24-hour price volatility percentage"""
        if not httpx:
            return 0.0
        
        # Check cache (valid for 5 minutes)
        cache_key = f"vol_{symbol}"
        if cache_key in self.price_cache:
            cache_age = datetime.utcnow() - self.price_cache_time.get(cache_key, datetime.min)
            if cache_age < timedelta(minutes=5):
                return self.price_cache[cache_key]
        
        # Map symbols to coingecko IDs
        id_map = {
            "ETH": "ethereum", "WETH": "ethereum",
            "BTC": "bitcoin", "WBTC": "wrapped-bitcoin",
            "USDC": "usd-coin", "USDT": "tether",
            "AERO": "aerodrome-finance",
        }
        
        coin_id = id_map.get(symbol.upper(), symbol.lower())
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.price_api}/simple/price",
                    params={
                        "ids": coin_id,
                        "vs_currencies": "usd",
                        "include_24hr_change": "true"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    change = abs(data.get(coin_id, {}).get("usd_24h_change", 0))
                    
                    # Cache result
                    self.price_cache[cache_key] = change
                    self.price_cache_time[cache_key] = datetime.utcnow()
                    
                    return change
        except Exception as e:
            print(f"[RiskManager] Volatility check error: {e}")
        
        return 0.0
    
    async def evaluate_position(
        self,
        agent: Dict,
        position: Dict
    ) -> Dict:
        """
        Full risk evaluation for a position
        
        Returns combined risk assessment
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "position_id": position.get("id"),
            "should_exit": False,
            "should_pause": False,
            "alerts": []
        }
        
        # Check stop loss
        sl_check = await self.check_stop_loss(agent, position)
        if sl_check["should_exit"]:
            results["should_exit"] = True
            results["alerts"].append({
                "type": "stop_loss",
                "severity": "critical",
                "message": sl_check["reason"]
            })
        
        # Check take profit
        tp_check = await self.check_take_profit(agent, position)
        if tp_check["should_exit"]:
            results["should_exit"] = True
            results["alerts"].append({
                "type": "take_profit",
                "severity": "info",
                "message": tp_check["reason"]
            })
        
        # Check volatility (get token from position)
        tokens = position.get("tokens", [])
        for token in tokens:
            vol_check = await self.check_volatility(agent, token)
            if vol_check["should_pause"]:
                results["should_pause"] = True
                results["alerts"].append({
                    "type": "volatility",
                    "severity": "warning",
                    "message": vol_check["reason"]
                })
        
        # Store alerts
        self.alerts.extend(results["alerts"])
        
        return results


# Global instance
risk_manager = RiskManager()


def get_risk_limits(agent_config: Dict) -> RiskLimits:
    """Get risk limits from agent config"""
    return risk_manager.parse_pro_config(agent_config.get("pro_config"))


async def check_position_risk(agent: Dict, position: Dict) -> Dict:
    """Check risk for a position"""
    return await risk_manager.evaluate_position(agent, position)
