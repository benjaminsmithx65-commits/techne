"""
Position Monitor for Auto-Exit Triggers
Monitors positions and triggers exit + reinvestment when conditions are met.

Exit Triggers:
1. Duration Expiry - investment duration ended
2. APY Below Range - pool APY dropped below min_apy
3. Stop-Loss - position lost >= stop_loss_percent (default 15%)

After exit, automatically finds and enters a new position.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Import dependencies
try:
    from agents.risk_manager import risk_manager
except ImportError:
    risk_manager = None

try:
    from agents.strategy_executor import strategy_executor
except ImportError:
    strategy_executor = None

try:
    from api.agent_config_router import DEPLOYED_AGENTS, _save_agents
except ImportError:
    DEPLOYED_AGENTS = {}
    _save_agents = lambda: None

try:
    from data_sources.thegraph import graph_client
except ImportError:
    graph_client = None

try:
    from api.websocket_router import broadcast_to_user
except ImportError:
    broadcast_to_user = None

try:
    from infrastructure.supabase_client import supabase
except ImportError:
    supabase = None


class PositionMonitor:
    """
    Background service monitoring positions for exit triggers.
    
    Runs every 60 seconds checking:
    - Duration expiry
    - APY below min_apy range
    - Stop-loss threshold
    
    When triggered, executes withdrawal and reinvestment.
    """
    
    def __init__(self):
        self.running = False
        self.check_interval = 60  # seconds
        self.last_check = None
        
        # Default settings for BASIC mode
        self.default_duration_days = 30
        self.default_stop_loss_percent = 15
        
        logger.info("[PositionMonitor] Initialized")
    
    async def start(self):
        """Start the monitoring loop"""
        self.running = True
        logger.info("[PositionMonitor] Starting position monitoring loop")
        
        while self.running:
            try:
                await self.check_all_positions()
                self.last_check = datetime.utcnow()
            except Exception as e:
                logger.error(f"[PositionMonitor] Error in check loop: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("[PositionMonitor] Stopped")
    
    async def check_all_positions(self):
        """Check all user positions for exit triggers.
        
        Data sources:
        1. Supabase user_positions (primary - persistent)
        2. DEPLOYED_AGENTS in-memory (fallback)
        """
        checked = 0
        exits_triggered = 0
        
        for user_address, agents in DEPLOYED_AGENTS.items():
            for agent in agents:
                if not agent.get("is_active", False):
                    continue
                
                # Try to get positions from Supabase first
                positions = []
                if supabase and supabase.is_available:
                    try:
                        positions = await supabase.get_user_positions(user_address)
                        logger.debug(f"[PositionMonitor] Got {len(positions)} positions from Supabase for {user_address[:10]}")
                    except Exception as e:
                        logger.warning(f"[PositionMonitor] Supabase fetch failed: {e}")
                
                # Fallback to in-memory positions
                if not positions:
                    positions = agent.get("positions", [])
                
                if not positions:
                    continue
                
                for position in positions:
                    checked += 1
                    exit_result = await self.check_position_exit(agent, position)
                    
                    if exit_result.get("should_exit"):
                        exits_triggered += 1
                        await self.execute_exit_and_reinvest(
                            agent, 
                            position, 
                            exit_result.get("reason", "Unknown")
                        )
        
        if checked > 0:
            logger.info(f"[PositionMonitor] Checked {checked} positions, {exits_triggered} exits triggered")
    
    async def check_position_exit(self, agent: Dict, position: Dict) -> Dict:
        """
        Check if position should be exited.
        
        Returns:
            {should_exit: bool, reason: str, trigger: str}
        """
        # 1. Check Duration Expiry
        duration_check = await self.check_duration_expiry(agent, position)
        if duration_check.get("expired"):
            return {
                "should_exit": True,
                "reason": duration_check.get("reason"),
                "trigger": "duration"
            }
        
        # 2. Check APY Below Range
        apy_check = await self.check_apy_range(agent, position)
        if apy_check.get("below_range"):
            return {
                "should_exit": True,
                "reason": apy_check.get("reason"),
                "trigger": "apy"
            }
        
        # 3. Check Stop-Loss
        stop_loss_check = await self.check_stop_loss(agent, position)
        if stop_loss_check.get("triggered"):
            return {
                "should_exit": True,
                "reason": stop_loss_check.get("reason"),
                "trigger": "stop_loss"
            }
        
        return {"should_exit": False}
    
    async def check_duration_expiry(self, agent: Dict, position: Dict) -> Dict:
        """
        Check if investment duration has expired.
        
        Uses agent's deployed_at + duration (default 30 days)
        """
        deployed_at_str = agent.get("deployed_at")
        if not deployed_at_str:
            return {"expired": False, "reason": "No deployment date"}
        
        try:
            deployed_at = datetime.fromisoformat(deployed_at_str.replace('Z', '+00:00'))
        except:
            return {"expired": False, "reason": "Invalid deployment date"}
        
        # Get duration from agent config (default 30 days)
        duration_config = agent.get("duration", {})
        if isinstance(duration_config, dict):
            duration_days = duration_config.get("days", self.default_duration_days)
        else:
            duration_days = self.default_duration_days
        
        # If duration is 0 or infinity, no expiry
        if duration_days <= 0:
            return {"expired": False, "reason": "No duration limit"}
        
        expiry_date = deployed_at + timedelta(days=duration_days)
        now = datetime.utcnow()
        
        if now >= expiry_date:
            return {
                "expired": True,
                "reason": f"Duration expired ({duration_days} days completed)"
            }
        
        return {"expired": False}
    
    async def check_apy_range(self, agent: Dict, position: Dict) -> Dict:
        """
        Check if pool APY dropped below agent's min_apy.
        
        Uses The Graph subgraph to get current APY.
        """
        min_apy = agent.get("min_apy", 10.0)
        pool_address = position.get("pool_address") or position.get("protocol_address")
        
        if not pool_address:
            return {"below_range": False, "reason": "No pool address"}
        
        # Get current APY from position cache or fetch
        current_apy = position.get("current_apy")
        
        if current_apy is None:
            # Fetch from The Graph subgraph
            if graph_client:
                try:
                    current_apy = await graph_client.get_pool_apy(pool_address)
                except Exception as e:
                    logger.warning(f"[PositionMonitor] Failed to fetch APY from The Graph: {e}")
                    return {"below_range": False, "reason": "Failed to fetch APY"}
        
        if current_apy is None:
            return {"below_range": False, "reason": "APY not available"}
        
        # Update position with current APY
        position["current_apy"] = current_apy
        
        if current_apy < min_apy:
            return {
                "below_range": True,
                "reason": f"APY dropped to {current_apy:.1f}% (below min {min_apy}%)",
                "current_apy": current_apy
            }
        
        return {"below_range": False, "current_apy": current_apy}
    
    async def check_stop_loss(self, agent: Dict, position: Dict) -> Dict:
        """
        Check if position has hit stop-loss threshold.
        
        For BASIC mode: default 15%
        For PRO mode: uses configured stopLossPercent
        """
        # Get stop-loss config
        pro_config = agent.get("pro_config") or {}
        stop_loss_enabled = pro_config.get("stopLossEnabled", True)  # Default enabled
        stop_loss_percent = pro_config.get("stopLossPercent", self.default_stop_loss_percent)
        
        if not stop_loss_enabled:
            return {"triggered": False, "reason": "Stop-loss disabled"}
        
        entry_value = position.get("entry_value", 0)
        current_value = position.get("current_value", entry_value)
        
        if entry_value <= 0:
            return {"triggered": False, "reason": "No entry value"}
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        
        if loss_percent >= stop_loss_percent:
            return {
                "triggered": True,
                "reason": f"Stop-loss triggered: -{loss_percent:.1f}% (threshold: -{stop_loss_percent}%)",
                "loss_percent": loss_percent
            }
        
        return {"triggered": False, "loss_percent": loss_percent}
    
    async def execute_exit_and_reinvest(self, agent: Dict, position: Dict, reason: str):
        """
        Execute position exit and reinvestment.
        
        1. Withdraw from current position
        2. Broadcast WebSocket event
        3. Find new best pool
        4. Invest in new pool
        5. Update positions in Supabase and memory
        """
        agent_id = agent.get("id", "unknown")
        user_address = agent.get("user_address")
        protocol = position.get("protocol") or position.get("protocol_name", "Unknown")
        amount = position.get("current_value", 0)
        
        logger.info(f"[PositionMonitor] Executing exit for {agent_id}: {reason}")
        
        # 1. Mark position as exiting
        position["status"] = "exiting"
        position["exit_reason"] = reason
        position["exit_started_at"] = datetime.utcnow().isoformat()
        
        # 2. Broadcast exit event via WebSocket
        if broadcast_to_user and user_address:
            await broadcast_to_user(user_address, {
                "type": "position_exit",
                "agent_id": agent_id,
                "position_id": position.get("id"),
                "protocol": protocol,
                "reason": reason,
                "amount": amount,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # 3. Execute on-chain withdrawal (placeholder - integrate with contract)
        withdrawal_success = await self.execute_withdrawal(agent, position)
        
        if not withdrawal_success:
            logger.error(f"[PositionMonitor] Withdrawal failed for {agent_id}")
            position["status"] = "exit_failed"
            return
        
        # 4. Close position in Supabase
        if supabase and supabase.is_available and user_address:
            try:
                await supabase.close_user_position(user_address, protocol)
                await supabase.log_position_history(
                    user_address=user_address,
                    protocol=protocol,
                    action="exit",
                    amount=amount,
                    metadata={"reason": reason, "agent_id": agent_id}
                )
                logger.info(f"[PositionMonitor] Position closed in Supabase")
            except Exception as e:
                logger.warning(f"[PositionMonitor] Supabase close failed: {e}")
        
        # 5. Remove exited position from memory
        agent["positions"] = [p for p in agent.get("positions", []) if p.get("id") != position.get("id")]
        
        # 6. Find new pool and reinvest
        if strategy_executor and amount > 0:
            try:
                # Find matching pools excluding the one we just exited
                excluded = [position.get("pool_address")]
                new_pool = await self.find_reinvestment_pool(agent, excluded)
                
                if new_pool:
                    # Execute new investment
                    reinvest_result = await self.execute_reinvestment(agent, new_pool, amount)
                    
                    if reinvest_result.get("success"):
                        new_position = reinvest_result.get("position", {})
                        
                        # Save new position to Supabase
                        if supabase and supabase.is_available and user_address:
                            try:
                                await supabase.save_user_position(
                                    user_address=user_address,
                                    protocol=new_pool.get("project", "Unknown"),
                                    entry_value=amount,
                                    current_value=amount,
                                    apy=new_pool.get("apy", 0),
                                    pool_address=new_pool.get("pool_address"),
                                    metadata={"agent_id": agent_id, "reinvested_from": protocol}
                                )
                                await supabase.log_position_history(
                                    user_address=user_address,
                                    protocol=new_pool.get("project", "Unknown"),
                                    action="enter",
                                    amount=amount,
                                    metadata={"apy": new_pool.get("apy", 0), "agent_id": agent_id}
                                )
                            except Exception as e:
                                logger.warning(f"[PositionMonitor] Supabase save failed: {e}")
                        
                        # Broadcast new position event
                        if broadcast_to_user and user_address:
                            await broadcast_to_user(user_address, {
                                "type": "position_enter",
                                "agent_id": agent_id,
                                "protocol": new_pool.get("project", "Unknown"),
                                "pool_address": new_pool.get("pool_address"),
                                "amount": amount,
                                "apy": new_pool.get("apy", 0),
                                "timestamp": datetime.utcnow().isoformat()
                            })
                        
                        logger.info(f"[PositionMonitor] Reinvested into {new_pool.get('project')}")
                else:
                    logger.warning(f"[PositionMonitor] No suitable pool found for reinvestment")
            except Exception as e:
                logger.error(f"[PositionMonitor] Reinvestment failed: {e}")
        
        # 7. Save updated agents to file
        _save_agents()
        
        logger.info(f"[PositionMonitor] Exit complete for {agent_id}")
    
    async def execute_withdrawal(self, agent: Dict, position: Dict) -> bool:
        """
        Execute on-chain withdrawal from protocol.
        
        TODO: Integrate with V4.3.3 contract executeWithdraw
        """
        # For now, simulate success
        # In production, this would call the smart contract
        logger.info(f"[PositionMonitor] Simulating withdrawal from {position.get('protocol', 'unknown')}")
        
        # TODO: Implement actual on-chain withdrawal
        # from agents.contract_monitor import contract_monitor
        # return await contract_monitor.execute_withdrawal(agent, position)
        
        return True
    
    async def find_reinvestment_pool(self, agent: Dict, excluded_pools: List[str] = None) -> Optional[Dict]:
        """
        Find best pool for reinvestment.
        
        Uses strategy_executor's pool matching with exclusions.
        """
        if not strategy_executor:
            return None
        
        excluded = excluded_pools or []
        
        try:
            # Get matching pools
            pools = await strategy_executor.find_matching_pools(agent)
            
            # Filter out excluded pools
            pools = [p for p in pools if p.get("pool_address") not in excluded]
            
            if not pools:
                return None
            
            # Rank and select best
            selected = await strategy_executor.rank_and_select(pools, agent)
            
            return selected[0] if selected else None
        except Exception as e:
            logger.error(f"[PositionMonitor] Failed to find reinvestment pool: {e}")
            return None
    
    async def execute_reinvestment(self, agent: Dict, pool: Dict, amount: float) -> Dict:
        """
        Execute investment into new pool.
        
        TODO: Integrate with V4.3.3 contract executeStrategy
        """
        # For now, simulate success and add to positions
        new_position = {
            "id": f"pos_{int(datetime.utcnow().timestamp())}",
            "protocol": pool.get("project"),
            "protocol_address": pool.get("pool_address"),
            "pool_address": pool.get("pool_address"),
            "symbol": pool.get("symbol"),
            "entry_value": amount,
            "current_value": amount,
            "entry_apy": pool.get("apy", 0),
            "current_apy": pool.get("apy", 0),
            "opened_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        agent["positions"].append(new_position)
        
        logger.info(f"[PositionMonitor] Simulated reinvestment into {pool.get('project')}")
        
        # TODO: Implement actual on-chain investment
        # return await strategy_executor.execute_v4_strategy(...)
        
        return {"success": True, "position": new_position}


# Global instance
position_monitor = PositionMonitor()


async def start_monitor():
    """Start the position monitor (call from main app startup)"""
    await position_monitor.start()


def stop_monitor():
    """Stop the position monitor"""
    position_monitor.stop()
