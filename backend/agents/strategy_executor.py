"""
Strategy Executor
Background task that executes strategies for deployed agents
Based on agent config, finds matching pools and executes positions via smart contract
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Import agent config storage
try:
    from api.agent_config_router import DEPLOYED_AGENTS
except ImportError:
    DEPLOYED_AGENTS = {}

# Import scout for pool finding
try:
    from artisan.scout_agent import get_scout_pools
except ImportError:
    get_scout_pools = None


class StrategyExecutor:
    """
    Executes yield strategies for deployed agents
    
    Flow:
    1. Read deployed agents from DEPLOYED_AGENTS
    2. For each active agent, find matching pools via Scout
    3. Rank pools by APY within agent's risk parameters
    4. Execute positions on smart contract (TechneAgentWallet)
    """
    
    def __init__(self):
        self.running = False
        self.execution_interval = 300  # 5 minutes
        self.last_execution: Dict[str, datetime] = {}
        
        # Smart contract config
        self.wallet_contract = os.getenv(
            "AGENT_WALLET_ADDRESS", 
            "0x567D1Fc55459224132aB5148c6140E8900f9a607"
        )
        self.rpc_url = os.getenv(
            "ALCHEMY_RPC_URL",
            "https://base-mainnet.g.alchemy.com/v2/demo"
        )
    
    async def start(self):
        """Start the executor loop"""
        self.running = True
        print("[StrategyExecutor] Starting executor loop...")
        
        while self.running:
            try:
                await self.execute_all_agents()
            except Exception as e:
                print(f"[StrategyExecutor] Execution error: {e}")
            
            await asyncio.sleep(self.execution_interval)
    
    def stop(self):
        """Stop the executor"""
        self.running = False
        print("[StrategyExecutor] Stopped")
    
    async def execute_all_agents(self):
        """Execute strategies for all active agents"""
        active_agents = [
            agent for agent in DEPLOYED_AGENTS.values()
            if agent.get("is_active", False)
        ]
        
        if not active_agents:
            return
        
        print(f"[StrategyExecutor] Processing {len(active_agents)} active agents")
        
        for agent in active_agents:
            try:
                await self.execute_agent_strategy(agent)
            except Exception as e:
                print(f"[StrategyExecutor] Error for {agent.get('user_address')}: {e}")
    
    async def execute_agent_strategy(self, agent: dict):
        """Execute strategy for a single agent"""
        user = agent.get("user_address", "unknown")
        
        # Check if we should execute (rate limit)
        last = self.last_execution.get(user)
        if last and datetime.utcnow() - last < timedelta(minutes=5):
            return
        
        print(f"[StrategyExecutor] Executing for {user[:10]}...")
        
        # 1. Find matching pools
        pools = await self.find_matching_pools(agent)
        
        if not pools:
            print(f"[StrategyExecutor] No matching pools found for {user[:10]}")
            return
        
        print(f"[StrategyExecutor] Found {len(pools)} matching pools")
        
        # 2. Rank and select top pools
        selected_pools = self.rank_and_select(pools, agent)
        
        # 3. Update agent with recommendations (for now, don't execute on-chain)
        agent["recommended_pools"] = selected_pools
        agent["last_scan"] = datetime.utcnow().isoformat()
        
        self.last_execution[user] = datetime.utcnow()
        
        print(f"[StrategyExecutor] Recommended {len(selected_pools)} pools for {user[:10]}")
    
    async def find_matching_pools(self, agent: dict) -> List[dict]:
        """Find pools matching agent's configuration"""
        if not get_scout_pools:
            return []
        
        try:
            # Get pools from Scout
            pools = await get_scout_pools(
                chain=agent.get("chain", "base"),
                limit=50
            )
            
            # Filter by agent preferences
            filtered = []
            
            for pool in pools:
                # Check APY range
                apy = pool.get("apy", 0)
                if apy < agent.get("min_apy", 0):
                    continue
                if apy > agent.get("max_apy", 1000):
                    continue
                
                # Check protocols
                project = (pool.get("project") or "").lower()
                allowed_protocols = [p.lower() for p in agent.get("protocols", [])]
                if allowed_protocols and not any(p in project for p in allowed_protocols):
                    continue
                
                # Check assets (if specified)
                symbol = (pool.get("symbol") or "").upper()
                preferred_assets = [a.upper() for a in agent.get("preferred_assets", [])]
                if preferred_assets and not any(a in symbol for a in preferred_assets):
                    continue
                
                # Check pool type
                pool_type = agent.get("pool_type", "single")
                is_lp = any(sep in symbol for sep in ["-", "/", " / "])
                if pool_type == "single" and is_lp:
                    continue
                if pool_type == "dual" and not is_lp:
                    continue
                
                # Check audit status if required
                if agent.get("only_audited", False):
                    # TODO: Check audit database
                    pass
                
                filtered.append(pool)
            
            return filtered
            
        except Exception as e:
            print(f"[StrategyExecutor] Error finding pools: {e}")
            return []
    
    def rank_and_select(self, pools: List[dict], agent: dict) -> List[dict]:
        """Rank pools and select top N based on agent config"""
        vault_count = agent.get("vault_count", 5)
        max_allocation = agent.get("max_allocation", 25)
        risk_level = agent.get("risk_level", "medium")
        
        # Score each pool
        for pool in pools:
            score = 0
            
            # APY contribution (normalized to 0-40 points)
            apy = pool.get("apy", 0)
            score += min(apy, 100) * 0.4
            
            # TVL contribution (normalized to 0-30 points)
            tvl = pool.get("tvl", 0)
            if tvl > 10_000_000:
                score += 30
            elif tvl > 1_000_000:
                score += 20
            elif tvl > 100_000:
                score += 10
            
            # Risk adjustment
            if risk_level == "low":
                # Prefer lower APY, higher TVL
                score = score * 0.7 + (30 - min(apy, 30))
            elif risk_level == "high":
                # Prefer higher APY
                score = score * 1.3
            
            pool["_score"] = score
        
        # Sort by score
        pools.sort(key=lambda p: p.get("_score", 0), reverse=True)
        
        # Select top N
        selected = pools[:vault_count]
        
        # Calculate allocation per pool
        for i, pool in enumerate(selected):
            # Distribute allocation (higher score = higher allocation)
            pool["_allocation"] = min(max_allocation, 100 // vault_count)
        
        return selected


# Global executor instance
strategy_executor = StrategyExecutor()


async def start_executor():
    """Start the strategy executor (call from main app startup)"""
    asyncio.create_task(strategy_executor.start())


def stop_executor():
    """Stop the strategy executor"""
    strategy_executor.stop()
