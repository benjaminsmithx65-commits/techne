"""
Agent Coordinator - Orchestrates Multi-Agent System
Routes data between all 8 agents and manages the complete workflow

Enhanced with Observability for full workflow tracing
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Observability integration
try:
    from agents.observability_engine import observability, traced, SpanStatus
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):
        def decorator(func): return func
        return decorator

# Core Agents - scout is in artisan/, rest in agents/
from artisan.scout_agent import scout_agent as scout
from .appraiser_agent import appraiser
from .merchant_agent import merchant
from .concierge_agent import concierge

# Extended Agents
from .sentinel_agent import sentinel
from .historian_agent import historian
from .arbitrageur_agent import arbitrageur
from .guardian_agent import guardian

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentCoordinator")


class AgentCoordinator:
    """
    Orchestrates the 8-agent system
    
    Complete Workflow:
    1. Scout finds new pools → 
    2. Sentinel checks security →
    3. Appraiser analyzes risk →
    4. Historian records data →
    5. Arbitrageur finds opportunities →
    6. Guardian monitors positions →
    7. Merchant handles payments →
    8. Concierge formats responses
    """
    
    def __init__(self):
        # Core agents
        self.scout = scout
        self.appraiser = appraiser
        self.merchant = merchant
        self.concierge = concierge
        
        # Extended agents
        self.sentinel = sentinel
        self.historian = historian
        self.arbitrageur = arbitrageur
        self.guardian = guardian
        
        self.is_running = False
        self.last_sync = None
        
        # Subscribe to Scout updates
        self.scout.subscribe(self._on_scout_update)
        
        # Subscribe to security alerts
        self.sentinel.subscribe(self._on_security_alert)
        
        # Subscribe to guardian alerts
        self.guardian.subscribe_alerts(self._on_guardian_alert)
        
    async def start(self):
        """Start the multi-agent system"""
        self.is_running = True
        logger.info("🏛️ Agent Coordinator started with 8 agents")
        
        # Start Scout's continuous monitoring
        await self.scout.start()
    
    def stop(self):
        """Stop the multi-agent system"""
        self.is_running = False
        self.scout.stop()
        logger.info("Agent Coordinator stopped")
    
    async def _on_scout_update(self, event_type: str, data: Any):
        """Handle updates from Scout - routes to all relevant agents"""
        logger.info(f"📬 Received {event_type} from Scout")
        
        if event_type == "new_pools":
            await self._process_new_pools(data)
        elif event_type == "apy_changes":
            await self._process_apy_changes(data)
    
    async def _on_security_alert(self, alert_type: str, data: Dict):
        """Handle security alerts from Sentinel"""
        logger.warning(f"🚨 Security alert: {alert_type}")
        
        # Format and potentially send to users
        if data.get("severity") == "high":
            # Trigger emergency exits if needed
            pool_id = data.get("pool", {}).get("pool")
            if pool_id:
                for user_id, positions in self.guardian.positions.items():
                    for pos in positions:
                        if pos.pool_id == pool_id:
                            self.guardian.trigger_emergency_exit(
                                user_id, pool_id, f"Security alert: {alert_type}"
                            )
    
    def _on_guardian_alert(self, alert):
        """Handle alerts from Guardian"""
        logger.info(f"🛡️ Guardian alert: {alert.message}")
        
        # Send via Concierge (Telegram etc.)
        formatted = self.concierge.format_telegram_alert("security_warning", {
            "message": alert.message,
            "severity": alert.severity.value
        })
    
    async def _process_new_pools(self, pools: List[Dict]):
        """Process new pools through the full agent pipeline"""
        
        # 1. Security check with Sentinel
        for pool in pools:
            security_report = self.sentinel.analyze_pool_security(pool)
            pool["security"] = {
                "threat_level": security_report.threat_level.value,
                "flags": [f.value for f in security_report.flags],
                "is_safe": security_report.threat_level.value in ["safe", "low"]
            }
        
        # Filter out dangerous pools
        safe_pools = [p for p in pools if p.get("security", {}).get("is_safe", False)]
        
        # 2. Risk analysis with Appraiser
        analyzed = self.appraiser.analyze_pools(safe_pools)
        
        # 3. Record to Historian
        for pool in analyzed:
            self.historian.record_pool_data(pool)
        self.historian.record_market_snapshot(analyzed)
        
        # 4. Find arbitrage opportunities
        top_opps = self.arbitrageur.find_top_opportunities(analyzed, limit=10)
        
        # 5. Notify via Concierge
        verified = [p for p in analyzed if p["verification_status"] == "artisan_verified"]
        
        logger.info(f"New pools: {len(pools)} found, {len(safe_pools)} safe, {len(verified)} verified")
        
        for pool in verified[:3]:  # Top 3 only
            alert = self.concierge.format_telegram_alert("new_pool", pool)
            logger.info(f"Would send Telegram: {pool['symbol']}")
    
    async def _process_apy_changes(self, changes: List[Dict]):
        """Process APY changes through agents"""
        
        # Check TVL drops with Sentinel
        current_pools = [c["pool"] for c in changes]
        previous_pools = self.scout.cache.get("pools", [])
        await self.sentinel.monitor_tvl_changes(current_pools, previous_pools)
        
        for change in changes:
            pool = change["pool"]
            
            # Record to historian
            self.historian.record_pool_data(pool)
            
            # Alert on significant drops
            if change["change_pct"] < -20:
                alert = self.concierge.format_telegram_alert("apy_drop", {
                    "symbol": pool.get("symbol"),
                    "old_apy": change["old_apy"],
                    "new_apy": change["new_apy"]
                })
                logger.info(f"APY Drop Alert: {pool.get('symbol')}")
            
            # Alert on spikes (could be suspicious)
            elif change["change_pct"] > 50:
                alert = self.concierge.format_telegram_alert("high_apy", pool)
                logger.info(f"High APY Alert: {pool.get('symbol')}")
    
    # ===========================================
    # API METHODS - ENHANCED
    # ===========================================
    
    def get_opportunities(
        self, 
        user_id: Optional[str] = None,
        filters: Optional[Dict] = None,
        limit: int = 20,
        include_trends: bool = False
    ) -> Dict:
        """Get analyzed opportunities with full agent insights"""
        
        # Get pools from Scout
        pools = self.scout.get_top_pools(limit=limit * 2)
        
        if filters:
            pools = self.scout.get_pools(filters)
        
        # Add security data from Sentinel
        for pool in pools:
            report = self.sentinel.analyze_pool_security(pool)
            pool["security_status"] = report.threat_level.value
        
        # Analyze with Appraiser
        analyzed = self.appraiser.analyze_pools(pools)
        
        # Add trend data from Historian if requested
        if include_trends:
            for pool in analyzed:
                trend = self.historian.analyze_pool_trend(pool.get("pool"), days=7)
                if trend:
                    pool["trend"] = {
                        "direction": trend.direction,
                        "strength": trend.strength,
                        "prediction": trend.prediction
                    }
        
        # Sort by risk-adjusted APY
        def sort_key(p):
            apy = p.get("apy", 0)
            risk_penalty = {"safe": 0, "low": 0.1, "moderate": 0.2, 
                           "elevated": 0.3, "high": 0.5, "extreme": 0.7, "suspicious": 1}
            security_penalty = {"safe": 0, "low": 0.05, "medium": 0.2, 
                               "high": 0.5, "critical": 1}
            
            risk_p = risk_penalty.get(p.get("risk_level", "moderate"), 0.3)
            sec_p = security_penalty.get(p.get("security_status", "medium"), 0.3)
            
            return apy * (1 - risk_p) * (1 - sec_p)
        
        analyzed.sort(key=sort_key, reverse=True)
        analyzed = analyzed[:limit]
        
        # Check user access
        requires_payment = []
        if user_id:
            for pool in analyzed:
                pool_id = pool.get("pool")
                if not self.merchant.has_pool_access(user_id, pool_id):
                    requires_payment.append(pool_id)
        
        return {
            "pools": analyzed,
            "total": len(analyzed),
            "requires_payment": requires_payment,
            "cache_age": self.scout.get_cache_age(),
            "market_trend": self.historian.get_market_trend(days=7)
        }
    
    def get_pool_details(self, pool_id: str, user_id: Optional[str] = None) -> Dict:
        """Get detailed pool analysis with all agent insights"""
        
        # Check access
        if user_id and not self.merchant.has_pool_access(user_id, pool_id):
            payment = self.merchant.create_pool_access_request(user_id, pool_id)
            return {
                "requires_payment": True,
                "payment_request": {
                    "id": payment.id,
                    "amount_usd": payment.amount_usd,
                    "recipient": payment.recipient_address,
                    "expires_at": payment.expires_at.isoformat()
                },
                "preview": self._get_pool_preview(pool_id)
            }
        
        # Get pool data
        pools = self.scout.get_pools()
        pool = next((p for p in pools if p.get("pool") == pool_id), None)
        
        if not pool:
            return {"error": "Pool not found"}
        
        # Full analysis from all agents
        risk_assessment = self.appraiser.analyze_pool(pool)
        security_report = self.sentinel.analyze_pool_security(pool)
        historical = self.historian.get_pool_performance(pool_id, days=30)
        trend = self.historian.analyze_pool_trend(pool_id, days=7)
        alternatives = self.arbitrageur.find_better_alternatives(pool, pools[:50])
        
        # Format with Concierge
        formatted = self.concierge.format_analysis_response(pool, {
            "risk_level": risk_assessment.level.value,
            "risk_score": risk_assessment.score,
            "verification_status": risk_assessment.status.value,
            "warnings": risk_assessment.warnings,
            "recommendation": risk_assessment.recommendation
        })
        
        return {
            "pool": pool,
            "analysis": {
                "risk_level": risk_assessment.level.value,
                "risk_score": risk_assessment.score,
                "status": risk_assessment.status.value,
                "warnings": risk_assessment.warnings,
                "flags": risk_assessment.flags,
                "recommendation": risk_assessment.recommendation
            },
            "security": {
                "threat_level": security_report.threat_level.value,
                "flags": [f.value for f in security_report.flags],
                "is_audited": security_report.is_audited,
                "liquidity_locked": security_report.liquidity_locked
            },
            "historical": historical,
            "trend": {
                "direction": trend.direction if trend else "unknown",
                "strength": trend.strength if trend else 0,
                "prediction": trend.prediction if trend else None
            } if trend else None,
            "alternatives": [
                {
                    "pool_symbol": alt.to_pool.get("symbol"),
                    "yield_gain": alt.yield_difference,
                    "break_even_days": alt.break_even_days
                }
                for alt in alternatives[:3]
            ],
            "formatted": formatted
        }
    
    def _get_pool_preview(self, pool_id: str) -> Dict:
        """Get limited preview for non-paying users"""
        pools = self.scout.get_pools()
        pool = next((p for p in pools if p.get("pool") == pool_id), None)
        
        if not pool:
            return {}
        
        return {
            "symbol": pool.get("symbol"),
            "project": pool.get("project"),
            "apy": pool.get("apy"),
            "chain": pool.get("chain"),
        }
    
    # ===========================================
    # USER POSITION MANAGEMENT
    # ===========================================
    
    def register_user_position(
        self,
        user_id: str,
        pool_id: str,
        amount: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        """Register a new position for monitoring"""
        
        pools = self.scout.get_pools()
        pool = next((p for p in pools if p.get("pool") == pool_id), None)
        
        if not pool:
            return {"error": "Pool not found"}
        
        position = self.guardian.register_position(
            user_id=user_id,
            pool_id=pool_id,
            symbol=pool.get("symbol", "Unknown"),
            amount=amount,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        return {
            "success": True,
            "position": {
                "pool_id": pool_id,
                "symbol": position.symbol,
                "amount": amount,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
        }
    
    def get_user_portfolio(self, user_id: str) -> Dict:
        """Get complete portfolio with analysis"""
        portfolio = self.guardian.get_user_portfolio(user_id)
        alerts = self.guardian.get_user_alerts(user_id, unread_only=True)
        
        return {
            **portfolio,
            "alerts": alerts,
            "recommendations": self._get_portfolio_recommendations(user_id)
        }
    
    def _get_portfolio_recommendations(self, user_id: str) -> List[Dict]:
        """Get recommendations for user's portfolio"""
        positions = self.guardian.get_user_positions(user_id)
        if not positions:
            return []
        
        pools = self.scout.get_pools()
        recommendations = []
        
        for position in positions:
            pool = next((p for p in pools if p.get("pool") == position.pool_id), None)
            if pool:
                alts = self.arbitrageur.find_better_alternatives(pool, pools[:50])
                if alts and alts[0].yield_difference > 10:
                    recommendations.append({
                        "type": "rebalance",
                        "from": position.symbol,
                        "to": alts[0].to_pool.get("symbol"),
                        "yield_gain": alts[0].yield_difference
                    })
        
        return recommendations
    
    # ===========================================
    # SYSTEM STATUS
    # ===========================================
    
    def get_system_status(self) -> Dict:
        """Get status of all 8 agents"""
        return {
            "coordinator": {
                "is_running": self.is_running,
                "agents_active": 8
            },
            "core_agents": {
                "scout": {
                    "running": self.scout.is_running,
                    "cache_age_seconds": self.scout.get_cache_age(),
                    "pools_cached": len(self.scout.cache.get("pools", []))
                },
                "appraiser": {
                    "verified_protocols": len(self.appraiser.verified_protocols)
                },
                "merchant": {
                    "pending_payments": len(self.merchant.pending_payments),
                    "active_subscriptions": len(self.merchant.subscriptions)
                },
                "concierge": {
                    "personality": self.concierge.personality["name"]
                }
            },
            "extended_agents": {
                "sentinel": {
                    "blacklisted": len(self.sentinel.blacklist),
                    "watchlist": len(self.sentinel.watchlist)
                },
                "historian": {
                    "pools_tracked": len(self.historian.pool_histories),
                    "market_snapshots": len(self.historian.market_snapshots)
                },
                "arbitrageur": {
                    "cached_opportunities": len(self.arbitrageur.cached_opportunities)
                },
                "guardian": {
                    "users_monitored": len(self.guardian.positions),
                    "active_alerts": len([a for a in self.guardian.alerts if not a.acknowledged]),
                    "emergency_queue": len(self.guardian.emergency_queue)
                }
            }
        }
    
    def handle_chat(self, message: str, user_id: Optional[str] = None) -> str:
        """Handle chat message through Concierge"""
        user_context = None
        
        if user_id:
            subscription = self.merchant.get_subscription(user_id)
            portfolio = self.guardian.get_user_portfolio(user_id)
            user_context = {
                "is_subscriber": subscription is not None,
                "tier": subscription.tier if subscription else "free",
                "portfolio_value": portfolio.get("total_value", 0)
            }
        
        return self.concierge.handle_chat_message(message, user_context)


# Singleton instance
coordinator = AgentCoordinator()

