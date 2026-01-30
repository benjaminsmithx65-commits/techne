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

# Import on-chain executor for real execution
try:
    from integrations.onchain_executor import onchain_executor, execute_lp_entry
except ImportError:
    onchain_executor = None
    execute_lp_entry = None

# Import lending executor for single-sided pools
try:
    from integrations.lending_executor import lending_executor, supply_to_lending
except ImportError:
    lending_executor = None
    supply_to_lending = None

# Import risk manager for stop-loss, take-profit, volatility guard
try:
    from agents.risk_manager import risk_manager, check_position_risk
except ImportError:
    risk_manager = None
    check_position_risk = None

# Import audit logger for Neural Terminal live updates
try:
    from api.audit_router import log_audit_entry
except ImportError:
    log_audit_entry = None

# Import historian for APY tracking and rotation
try:
    from agents.historian_agent import historian
except ImportError:
    historian = None


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
        
        # PARK THRESHOLDS - auto-deposit to Aave if conditions met
        self.park_idle_threshold = 100  # $100 USDC minimum to trigger Park (covers tx fees)
        self.park_idle_hours = 12  # Hours idle before Park
        self.park_no_pools_hours = 0.25  # 15 minutes without matching pools before Park
        
        # Track state for Park logic
        self.last_pools_found: Dict[str, datetime] = {}  # agent_id -> when pools were last found
        self.idle_since: Dict[str, datetime] = {}  # agent_id -> when idle balance started
        
        # Smart contract config - V4.3.3 PRODUCTION (same as frontend!)
        self.wallet_contract = os.getenv(
            "AGENT_WALLET_ADDRESS", 
            "0xC83E01e39A56Ec8C56Dd45236E58eE7a139cCDD4"  # V4.3.3 - must match frontend!
        )
        self.rpc_url = os.getenv(
            "ALCHEMY_RPC_URL",
            "https://mainnet.base.org"
        )
        
        # V4 ABI for executeStrategy
        self.v4_abi = [
            {
                "inputs": [
                    {"name": "user", "type": "address"},
                    {"name": "protocol", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "data", "type": "bytes"}
                ],
                "name": "executeStrategy",
                "outputs": [
                    {"name": "success", "type": "bool"},
                    {"name": "result", "type": "bytes"}
                ],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "user", "type": "address"}],
                "name": "balances",
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    def check_gas_price(self, agent: dict, w3) -> tuple[bool, float]:
        """
        Check if current gas price is within agent's max_gas_price limit.
        Returns (is_ok, current_gwei)
        """
        max_gas_gwei = agent.get("max_gas_price", 50)  # Default 50 gwei
        current_gas = w3.eth.gas_price
        current_gwei = current_gas / 1e9
        
        if current_gwei > max_gas_gwei:
            print(f"[StrategyExecutor] Gas too high: {current_gwei:.2f} > {max_gas_gwei} gwei - SKIPPING")
            return False, current_gwei
        return True, current_gwei
    
    def check_should_compound(self, agent: dict) -> bool:
        """
        Check if it's time to compound based on compound_frequency setting.
        Returns True if should compound now.
        """
        compound_freq = agent.get("compound_frequency", 7)  # Days between compounds
        last_compound = agent.get("last_compound_time")
        
        if not last_compound:
            return True  # Never compounded, do it now
        
        from datetime import datetime, timedelta
        try:
            last_dt = datetime.fromisoformat(last_compound)
            next_compound = last_dt + timedelta(days=compound_freq)
            return datetime.utcnow() >= next_compound
        except:
            return True
    
    def check_emergency_exit(self, agent: dict, current_value: float, initial_value: float) -> bool:
        """
        Check if emergency exit should trigger based on max_drawdown setting.
        Returns True if should exit positions.
        """
        if not agent.get("emergency_exit", True):
            return False
        
        max_drawdown = agent.get("max_drawdown", 30)  # Default -30%
        
        if initial_value <= 0:
            return False
        
        current_drawdown = ((initial_value - current_value) / initial_value) * 100
        
        if current_drawdown >= max_drawdown:
            print(f"[StrategyExecutor] EMERGENCY EXIT: Drawdown {current_drawdown:.1f}% >= {max_drawdown}%")
            return True
        return False
    
    def filter_avoid_il(self, pools: list, agent: dict) -> list:
        """
        Filter out pools that may cause impermanent loss if avoid_il is enabled.
        Single-sided lending pools are preferred.
        """
        if not agent.get("avoid_il", False):
            return pools
        
        # Single-sided lending protocols (no IL risk)
        safe_protocols = ["aave", "aave-v3", "compound", "compound-v3", "morpho", "moonwell", "beefy"]
        
        filtered = []
        for pool in pools:
            project = pool.get("project", "").lower()
            pool_type = pool.get("pool_type", pool.get("category", "")).lower()
            
            # Keep if it's a lending protocol or single-asset vault
            if any(safe in project for safe in safe_protocols):
                filtered.append(pool)
            elif "lending" in pool_type or "single" in pool_type:
                filtered.append(pool)
            # Skip DEX LP pools (high IL risk)
        
        print(f"[StrategyExecutor] Avoid IL filter: {len(pools)} -> {len(filtered)} pools")
        return filtered if filtered else pools[:3]  # Fallback to top 3 if all filtered
    
    def check_park_conditions(self, agent: dict, pools_found: bool, idle_balance: float) -> dict:
        """
        Check if Park conditions are met for auto-deposit to Aave USDC.
        
        Triggers Park when:
        1. No matching pools found for > 6 hours (park_no_pools_hours)
        2. Idle balance > $5000 for > 12 hours (park_idle_hours)
        
        Returns:
            dict with should_park, reason, trigger
        """
        agent_id = agent.get("id", "unknown")
        now = datetime.utcnow()
        
        # Track pools found state
        if pools_found:
            self.last_pools_found[agent_id] = now
        
        # Track idle state
        if idle_balance >= self.park_idle_threshold:
            if agent_id not in self.idle_since:
                self.idle_since[agent_id] = now
                print(f"[StrategyExecutor] 🅿️ Idle tracking started for {agent_id[:15]}: ${idle_balance:.0f}")
        else:
            # Reset idle tracking if balance drops below threshold
            if agent_id in self.idle_since:
                del self.idle_since[agent_id]
        
        # CHECK 1: No pools found for > 6 hours
        last_found = self.last_pools_found.get(agent_id)
        if last_found:
            hours_since_pools = (now - last_found).total_seconds() / 3600
            if not pools_found and hours_since_pools >= self.park_no_pools_hours:
                return {
                    "should_park": True,
                    "reason": f"No matching pools for {hours_since_pools:.1f}h (threshold: {self.park_no_pools_hours}h)",
                    "trigger": "no_pools_timeout"
                }
        elif not pools_found:
            # First time - initialize tracking
            self.last_pools_found[agent_id] = now
        
        # CHECK 2: Idle balance > $5k for > 12 hours  
        idle_start = self.idle_since.get(agent_id)
        if idle_start and idle_balance >= self.park_idle_threshold:
            hours_idle = (now - idle_start).total_seconds() / 3600
            if hours_idle >= self.park_idle_hours:
                return {
                    "should_park": True,
                    "reason": f"${idle_balance:.0f} idle for {hours_idle:.1f}h (threshold: {self.park_idle_hours}h)",
                    "trigger": "idle_timeout"
                }
        
        return {"should_park": False, "reason": None, "trigger": None}
    
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
        # DEPLOYED_AGENTS now stores: user_address -> [list of agents]
        all_agents = []
        for user_agents in DEPLOYED_AGENTS.values():
            if isinstance(user_agents, list):
                all_agents.extend([a for a in user_agents if a.get("is_active", False)])
            elif isinstance(user_agents, dict) and user_agents.get("is_active", False):
                all_agents.append(user_agents)
        
        if not all_agents:
            return
        
        print(f"[StrategyExecutor] Processing {len(all_agents)} active agents")
        
        for agent in all_agents:
            try:
                # Check existing positions for risk (stop-loss, take-profit)
                await self.check_position_risks(agent)
                
                # Check if compound timing is right based on compound_frequency
                if not self.check_should_compound(agent):
                    print(f"[StrategyExecutor] Skipping {agent.get('id', 'unknown')[:15]} - not compound time yet")
                    continue
                
                # Execute strategy
                await self.execute_agent_strategy(agent)
                
                # Update last compound time
                agent["last_compound_time"] = datetime.utcnow().isoformat()
                
                # Check if rebalancing needed
                if agent.get("auto_rebalance", True):
                    await self.check_rebalance_needed(agent)
            except Exception as e:
                print(f"[StrategyExecutor] Error for {agent.get('id', 'unknown')}: {e}")
    
    async def execute_agent_strategy(self, agent: dict):
        """Execute strategy for a single agent"""
        agent_id = agent.get("id", "unknown")
        user_address = agent.get("user_address", "")
        
        # Check if we should execute (rate limit)
        last = self.last_execution.get(agent_id)
        if last and datetime.utcnow() - last < timedelta(minutes=5):
            return
        
        print(f"[StrategyExecutor] Executing for agent {agent_id[:15]}...")
        
        # Log: Starting scan
        if log_audit_entry:
            log_audit_entry(
                action="POOL_SCAN_START",
                wallet=user_address,
                details={
                    "agent_id": agent_id[:15],
                    "protocols": agent.get("protocols", []),
                    "min_apy": agent.get("min_apy", 50),
                    "pool_type": agent.get("pool_type", "all")
                }
            )
        
        # 1. Find matching pools
        pools = await self.find_matching_pools(agent)
        
        if not pools:
            print(f"[StrategyExecutor] No matching pools found - using Aave USDC fallback")
            
            # Fetch live APY from Aave on-chain (like Aerodrome Sugar)
            aave_usdc_apy = 5.0  # Default fallback
            aave_usdc_tvl = 30000000  # Default $30M
            try:
                from protocols.aave_v3 import get_aave_protocol
                aave = get_aave_protocol()
                reserves = aave.get_reserves_data()
                usdc_reserve = next((r for r in reserves if r.get("asset") == "USDC"), None)
                if usdc_reserve:
                    aave_usdc_apy = usdc_reserve.get("apy", 5.0)
                    aave_usdc_tvl = usdc_reserve.get("tvl", 30000000)
                    print(f"[StrategyExecutor] Live Aave USDC: APY={aave_usdc_apy}%, TVL=${aave_usdc_tvl:,.0f}")
            except Exception as e:
                print(f"[StrategyExecutor] Aave live fetch failed, using defaults: {e}")
            
            # Log: No pools found - parking in Aave
            if log_audit_entry:
                log_audit_entry(
                    action="PARKING_ENGAGED",
                    wallet=user_address,
                    details={"apy": aave_usdc_apy, "reason": "No matching pools found", "source": "on-chain"}
                )
            # Fallback: Default to Aave USDC (always available, always safe)
            pools = [{
                "symbol": "USDC",
                "project": "aave-v3",
                "apy": aave_usdc_apy,
                "tvl": aave_usdc_tvl,
                "chain": "Base",
                "risk_score": "Low",
                "pool": "aave-usdc-base"
            }]
        
        print(f"[StrategyExecutor] Found {len(pools)} matching pools")
        
        # Log: Pools found
        if log_audit_entry and pools:
            top_pool = pools[0] if pools else {}
            log_audit_entry(
                action="POOL_EVALUATION",
                wallet=user_address,
                details={
                    "pools_found": len(pools),
                    "top_pool": top_pool.get("symbol", "Unknown"),
                    "top_apy": top_pool.get("apy", 0),
                    "top_tvl": top_pool.get("tvl", 0)
                }
            )
        
        # 2. Rank and select top pools
        selected_pools = self.rank_and_select(pools, agent)
        
        # 3. Update agent with recommendations
        agent["recommended_pools"] = selected_pools
        agent["last_scan"] = datetime.utcnow().isoformat()
        
        self.last_execution[agent_id] = datetime.utcnow()
        
        print(f"[StrategyExecutor] Recommended {len(selected_pools)} pools for {agent_id[:15]}")
        
        # Log: Recommendations ready
        if log_audit_entry and selected_pools:
            log_audit_entry(
                action="SCAN_COMPLETE",
                wallet=user_address,
                details={
                    "selected_count": len(selected_pools),
                    "pools": [p.get("symbol", "?") for p in selected_pools[:3]]
                }
            )
        
        # 4. AUTO-EXECUTE: Check if user has idle balance and execute allocation
        if user_address and selected_pools:
            try:
                idle_balance = await self.get_user_idle_balance(user_address, agent)
                
                # Check Park conditions (6h no pools, 12h idle > $5k)
                pools_were_found = len(pools) > 0 and pools[0].get("project") != "aave-v3"  # Not just fallback
                park_check = self.check_park_conditions(agent, pools_were_found, idle_balance)
                
                if park_check.get("should_park"):
                    print(f"[StrategyExecutor] 🅿️ PARK TRIGGERED: {park_check['reason']}")
                    
                    # Force Aave USDC for Park
                    aave_usdc_apy = 5.0
                    try:
                        from protocols.aave_v3 import get_aave_protocol
                        aave = get_aave_protocol()
                        reserves = aave.get_reserves_data()
                        usdc_reserve = next((r for r in reserves if r.get("asset") == "USDC"), None)
                        if usdc_reserve:
                            aave_usdc_apy = usdc_reserve.get("apy", 5.0)
                    except:
                        pass
                    
                    selected_pools = [{
                        "symbol": "USDC",
                        "project": "aave-v3",
                        "apy": aave_usdc_apy,
                        "chain": "Base",
                        "risk_score": "Low",
                        "pool": "aave-usdc-base"
                    }]
                    
                    if log_audit_entry:
                        log_audit_entry(
                            action="PARKING_ENGAGED",
                            wallet=user_address,
                            details={
                                "apy": aave_usdc_apy,
                                "reason": park_check["reason"],
                                "trigger": park_check["trigger"],
                                "idle_balance": idle_balance,
                                "source": "on-chain"
                            }
                        )
                
                # MINIMUM $20 USDC to execute any moves (prevent dust trades)
                if idle_balance >= 20:
                    print(f"[StrategyExecutor] User has ${idle_balance:.2f} idle - auto-allocating!")
                    
                    # Log: Starting allocation
                    if log_audit_entry:
                        log_audit_entry(
                            action="ALLOCATION_START",
                            wallet=user_address,
                            details={"amount": idle_balance, "pools": len(selected_pools)}
                        )
                    
                    # Execute allocation
                    result = await self.execute_allocation(agent, idle_balance)
                    
                    if result.get("success"):
                        print(f"[StrategyExecutor] Auto-allocation SUCCESS: {result.get('successful')}/{result.get('total_pools')} pools")
                        if log_audit_entry:
                            log_audit_entry(
                                action="ALLOCATION_SUCCESS",
                                wallet=user_address,
                                details={
                                    "amount": idle_balance,
                                    "pools_executed": result.get('successful', 0)
                                }
                            )
                    else:
                        print(f"[StrategyExecutor] Auto-allocation failed: {result.get('error')}")
                        if log_audit_entry:
                            log_audit_entry(
                                action="ALLOCATION_FAILED",
                                wallet=user_address,
                                details={"error": str(result.get('error', 'Unknown'))}
                            )
                else:
                    print(f"[StrategyExecutor] Balance ${idle_balance:.2f} below $20 minimum - skipping execution")
                    if log_audit_entry:
                        log_audit_entry(
                            action="IDLE_CAPITAL",
                            wallet=user_address,
                            details={"balance": idle_balance, "minimum": 20, "reason": "Balance below $20 minimum"}
                        )
                    
            except Exception as e:
                print(f"[StrategyExecutor] Balance check error: {e}")
    
    async def get_user_idle_balance(self, user_address: str, agent: dict = None) -> float:
        """
        Get user's idle USDC balance from BOTH sources:
        1. V4 contract balances(user_address)
        2. Agent EOA wallet USDC balance
        
        Returns the sum of both.
        """
        try:
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            USDC = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
            usdc_abi = [{'inputs': [{'name': 'account', 'type': 'address'}], 'name': 'balanceOf', 'outputs': [{'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]
            usdc = w3.eth.contract(address=USDC, abi=usdc_abi)
            
            total_balance = 0
            
            # Source 1: V4 Contract balance (user's deposited funds)
            try:
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(self.wallet_contract),
                    abi=self.v4_abi
                )
                v4_balance_wei = contract.functions.balances(
                    Web3.to_checksum_address(user_address)
                ).call()
                v4_balance = v4_balance_wei / 1e6
                total_balance += v4_balance
                print(f"[StrategyExecutor] V4 contract balance: ${v4_balance:.2f}")
            except Exception as e:
                print(f"[StrategyExecutor] V4 balance check failed: {e}")
            
            # Source 2: Agent EOA USDC balance (agent's own wallet)
            if agent and agent.get("agent_address"):
                try:
                    agent_address = Web3.to_checksum_address(agent.get("agent_address"))
                    eoa_balance_wei = usdc.functions.balanceOf(agent_address).call()
                    eoa_balance = eoa_balance_wei / 1e6
                    total_balance += eoa_balance
                    print(f"[StrategyExecutor] Agent EOA balance: ${eoa_balance:.2f}")
                except Exception as e:
                    print(f"[StrategyExecutor] Agent EOA balance check failed: {e}")
            
            print(f"[StrategyExecutor] Total idle balance: ${total_balance:.2f}")
            return total_balance
            
        except Exception as e:
            print(f"[StrategyExecutor] Error reading balance: {e}")
            return 0
    
    async def check_rebalance_needed(self, agent: dict):
        """Check if agent positions need rebalancing"""
        allocations = agent.get("allocations", [])
        recommended = agent.get("recommended_pools", [])
        
        if not allocations or not recommended:
            return
        
        # Get current allocation symbols
        current_symbols = set(a.get("pool") for a in allocations)
        recommended_symbols = set(p.get("symbol") for p in recommended)
        
        # Check for changes
        new_pools = recommended_symbols - current_symbols
        removed_pools = current_symbols - recommended_symbols
        
        if new_pools or removed_pools:
            print(f"[StrategyExecutor] Rebalance needed for {agent.get('id')}")
            print(f"  New pools: {new_pools}")
            print(f"  Removed pools: {removed_pools}")
            
            # Mark for rebalancing
            agent["needs_rebalance"] = True
            agent["rebalance_reason"] = {
                "new_pools": list(new_pools),
                "removed_pools": list(removed_pools),
                "detected_at": datetime.utcnow().isoformat()
            }
        
        # Check for APY drift using rebalance_threshold setting
        rebalance_threshold = agent.get("rebalance_threshold", 5) / 100  # Default 5%, convert to decimal
        
        for alloc in allocations:
            pool_symbol = alloc.get("pool")
            old_apy = alloc.get("apy", 0)
            
            # Find current APY from recommended
            current = next((p for p in recommended if p.get("symbol") == pool_symbol), None)
            if current:
                new_apy = current.get("apy", 0)
                if old_apy > 0 and abs(new_apy - old_apy) / old_apy > rebalance_threshold:
                    print(f"[StrategyExecutor] APY drift detected: {pool_symbol} {old_apy:.1f}% → {new_apy:.1f}% (threshold: {rebalance_threshold*100:.0f}%)")
                    agent["needs_rebalance"] = True
        
        # Check if any position APY is below min_apy for apy_check_hours (default 24h)
        if historian:
            min_apy = agent.get("min_apy", 5)
            apy_check_hours = agent.get("apy_check_hours", 24)  # Default 24h (1 day)
            
            for alloc in allocations:
                pool_id = alloc.get("pool_id") or alloc.get("pool")
                if not pool_id:
                    continue
                
                rotation_check = historian.check_below_min_apy(pool_id, min_apy, apy_check_hours)
                
                if rotation_check.get("should_rotate"):
                    print(f"[StrategyExecutor] 🔄 ROTATION TRIGGER: {pool_id} - {rotation_check['reason']}")
                    agent["needs_rebalance"] = True
                    alloc["needs_rotation"] = True
                    alloc["rotation_reason"] = rotation_check["reason"]
                    
                    if log_audit_entry:
                        log_audit_entry(
                            action="ROTATION_TRIGGER",
                            wallet=agent.get("user_address", ""),
                            details={
                                "pool_id": pool_id,
                                "avg_apy": rotation_check.get("current_avg"),
                                "min_apy": min_apy,
                                "check_hours": apy_check_hours
                            }
                        )
    
    async def check_position_risks(self, agent: dict):
        """
        Check all positions for risk triggers using Pro Mode settings
        
        Uses risk_manager to check:
        - Stop-loss: exit if loss >= threshold
        - Take-profit: exit if profit >= target
        - Volatility guard: pause if market too volatile
        """
        if not check_position_risk:
            return
        
        allocations = agent.get("allocations", [])
        pro_config = agent.get("pro_config", {})
        
        if not allocations:
            return
        
        agent_id = agent.get("id", "unknown")
        
        for position in allocations:
            result = await check_position_risk(agent, position)
            
            if result.get("should_exit"):
                print(f"[StrategyExecutor] 🚨 Risk trigger for {agent_id}: {result.get('alerts', [])}")
                # Mark position for exit
                position["needs_exit"] = True
                position["exit_reason"] = result.get("alerts", [{"message": "Risk limit reached"}])[0].get("message")
                
                # TODO: Execute exit via onchain_executor
                # await self.execute_exit(agent, position)
                
            if result.get("should_pause"):
                print(f"[StrategyExecutor] ⏸️ Pausing {agent_id} due to volatility")
                agent["paused"] = True
                agent["pause_reason"] = "High market volatility"
                agent["pause_until"] = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        
        # Check emergency exit based on max_drawdown setting
        total_invested = sum(p.get("amount", 0) for p in allocations)
        total_current = sum(p.get("current_value", p.get("amount", 0)) for p in allocations)
        
        if self.check_emergency_exit(agent, total_current, total_invested):
            print(f"[StrategyExecutor] 🚨 EMERGENCY EXIT triggered for {agent_id}")
            # Mark all positions for exit
            for position in allocations:
                position["needs_exit"] = True
                position["exit_reason"] = f"Emergency exit: max drawdown exceeded"
            
            if log_audit_entry:
                log_audit_entry(
                    action="EMERGENCY_EXIT",
                    wallet=agent.get("user_address", ""),
                    details={
                        "invested": total_invested,
                        "current": total_current,
                        "drawdown_pct": ((total_invested - total_current) / total_invested * 100) if total_invested > 0 else 0,
                        "max_drawdown": agent.get("max_drawdown", 30)
                    }
                )
    
    async def find_matching_pools(self, agent: dict) -> List[dict]:
        """Find pools matching agent's configuration"""
        if not get_scout_pools:
            print("[StrategyExecutor] Scout not available, using fallback")
            return []
        
        try:
            # Get pools from Scout - returns {"pools": [...], "total": N, ...}
            chain = agent.get("chain", "base")
            # Normalize chain name for DefiLlama
            chain_map = {"base": "Base", "ethereum": "Ethereum", "arbitrum": "Arbitrum"}
            normalized_chain = chain_map.get(chain.lower(), chain.title())
            
            result = await get_scout_pools(
                chain=normalized_chain,
                min_tvl=agent.get("min_tvl", 500000),  # $500k minimum (user wants quality)
                min_apy=agent.get("min_apy", 50),  # 50% minimum APY
                max_apy=agent.get("max_apy", 50000),  # Allow high APY
                protocols=agent.get("protocols", []),
                stablecoin_only=agent.get("pool_type") == "stablecoin"
            )
            
            # CRITICAL: Extract pools from result dict
            if isinstance(result, dict):
                pools = result.get("pools", [])
                print(f"[StrategyExecutor] Got {len(pools)} pools from Scout")
            elif isinstance(result, list):
                pools = result
            else:
                pools = []
            
            if not pools:
                print(f"[StrategyExecutor] No pools returned from Scout for {normalized_chain}")
                return []
            
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
                
                # Check pool type (default: allow ALL pools)
                pool_type = agent.get("pool_type", "all")
                is_lp = any(sep in symbol for sep in ["-", "/", " / "])
                if pool_type == "single" and is_lp:
                    continue
                if pool_type == "dual" and not is_lp:
                    continue
                # pool_type == "all" allows everything
                
                # Check risk score (from Scout)
                risk_score = pool.get("risk_score", "Medium")
                risk_level = agent.get("risk_level", "medium")
                if risk_level == "low" and risk_score == "High":
                    continue
                
                # Check audit status if required
                if agent.get("only_audited", False):
                    # Trusted protocols are considered audited
                    trusted = ['aave', 'compound', 'curve', 'uniswap', 'morpho', 'lido']
                    if not any(t in project for t in trusted):
                        continue
                
                filtered.append(pool)
            
            # Apply avoid_il filter if enabled
            filtered = self.filter_avoid_il(filtered, agent)
            
            print(f"[StrategyExecutor] Filtered to {len(filtered)} pools matching agent config")
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
    
    async def execute_v4_strategy(
        self, 
        agent: dict,  # Now takes full agent with encrypted_private_key
        protocol_address: str, 
        amount_usdc: float,
        call_data: bytes = b""
    ) -> Dict:
        """
        Execute strategy on V4 contract for a specific user.
        
        V4 Individual Model:
        - Uses agent's OWN private key (not global env)
        - Moves funds from balances[user] to investments[user][protocol]
        - Each user's funds tracked separately
        
        Args:
            agent: Agent dict containing user_address and encrypted_private_key
            protocol_address: DeFi protocol to allocate to
            amount_usdc: Amount in USDC (6 decimals)
            call_data: Encoded call data for the protocol
        """
        try:
            from web3 import Web3
            
            user_address = agent.get("user_address")
            encrypted_pk = agent.get("encrypted_private_key")
            
            # Get private key - try agent's own key first, fallback to env
            if encrypted_pk:
                try:
                    from services.agent_keys import decrypt_private_key
                    agent_private_key = decrypt_private_key(encrypted_pk)
                    print(f"[StrategyExecutor] Using agent's own execution key")
                except Exception as e:
                    print(f"[StrategyExecutor] Key decryption failed: {e}")
                    agent_private_key = os.getenv("AGENT_PRIVATE_KEY")
            else:
                agent_private_key = os.getenv("AGENT_PRIVATE_KEY")
            
            if not agent_private_key:
                return {"success": False, "error": "No execution key available for agent"}
            
            w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(self.wallet_contract),
                abi=self.v4_abi
            )
            
            # Check user's free balance first
            user_balance = contract.functions.balances(
                Web3.to_checksum_address(user_address)
            ).call()
            
            amount_wei = int(amount_usdc * 1e6)  # USDC has 6 decimals
            
            if user_balance < amount_wei:
                return {
                    "success": False, 
                    "error": f"Insufficient balance: {user_balance/1e6:.2f} USDC < {amount_usdc:.2f} USDC"
                }
            
            # Check gas price limit
            gas_ok, current_gwei = self.check_gas_price(agent, w3)
            if not gas_ok:
                return {
                    "success": False,
                    "error": f"Gas too high: {current_gwei:.1f} gwei > {agent.get('max_gas_price', 50)} gwei limit"
                }
            
            # Build transaction
            account = w3.eth.account.from_key(agent_private_key)
            
            tx = contract.functions.executeStrategy(
                Web3.to_checksum_address(user_address),
                Web3.to_checksum_address(protocol_address),
                amount_wei,
                call_data
            ).build_transaction({
                "from": account.address,
                "gas": 500000,
                "gasPrice": w3.eth.gas_price,
                "nonce": w3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send
            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[StrategyExecutor] V4 executeStrategy TX: {tx_hash.hex()}")
            
            # Wait for receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "user": user_address,
                "protocol": protocol_address,
                "amount": amount_usdc,
                "gas_used": receipt.gasUsed
            }
            
        except Exception as e:
            print(f"[StrategyExecutor] V4 execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_allocation(self, agent: dict, amount_usdc: float) -> Dict:
        """
        Execute real on-chain allocation to recommended pools using V4 contract.
        
        V4 calls executeStrategy(user, protocol, amount, data) for each pool.
        
        Args:
            agent: Agent config with recommended_pools and user_address
            amount_usdc: Total USDC amount to allocate
            
        Returns:
            Execution result with tx hashes
        """
        user_address = agent.get("user_address")
        if not user_address:
            return {"success": False, "error": "Agent has no user_address"}
        
        recommended = agent.get("recommended_pools", [])
        if not recommended:
            return {"success": False, "error": "No recommended pools"}
        
        # Protocol addresses for single-sided lending + DEX LP
        PROTOCOL_ADDRESSES = {
            # Lending (single-sided)
            "aave": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
            "aave-v3": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
            "compound": "0x46e6b214b524310239732D51387075E0e70970bf",
            "compound-v3": "0x46e6b214b524310239732D51387075E0e70970bf",
            "morpho": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
            "morpho-blue": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
            "moonwell": "0xfBb21d0380bEE3312B33c4353c8936a0F13EF26C",
            # DEX LP (dual-sided)
            "aerodrome": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",  # Aerodrome Router
            "velodrome": "0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858",  # Velodrome Router
        }
        
        # DEX protocols that use LP (dual-sided)
        DEX_PROTOCOLS = ["aerodrome", "velodrome", "uniswap", "curve"]
        
        results = []
        allocation_per_pool = amount_usdc / len(recommended)
        
        for pool in recommended:
            symbol = pool.get("symbol", "")
            project = (pool.get("project") or "").lower()
            
            # Get protocol address
            protocol_address = PROTOCOL_ADDRESSES.get(project)
            if not protocol_address:
                # Try partial match
                for key, addr in PROTOCOL_ADDRESSES.items():
                    if key in project:
                        protocol_address = addr
                        break
            
            if not protocol_address:
                print(f"[StrategyExecutor] Unknown protocol: {project}, skipping")
                results.append({
                    "pool": symbol,
                    "protocol": project,
                    "amount": allocation_per_pool,
                    "result": {"success": False, "error": f"Unknown protocol: {project}"}
                })
                continue
            
            print(f"[StrategyExecutor] V4 allocating ${allocation_per_pool:.2f} for {user_address[:10]}... to {symbol}")
            
            # Detect if this is an LP pool (dual-sided)
            is_lp_pool = any(sep in symbol for sep in ["-", "/", " / "])
            is_dex_protocol = any(dex in project for dex in DEX_PROTOCOLS)
            
            if is_lp_pool or is_dex_protocol:
                # DUAL-SIDED LP: Execute via AerodromeDualLPBuilder for EOA agents
                print(f"[StrategyExecutor] 🔄 LP Pool detected: {symbol} on {project}")
                
                # Check if this is an EOA agent with private key
                encrypted_pk = agent.get("encrypted_private_key")
                if encrypted_pk and "aerodrome" in project:
                    try:
                        from artisan.aerodrome_dual import AerodromeDualLPBuilder
                        from services.agent_keys import decrypt_private_key
                        from eth_account import Account
                        from web3 import Web3
                        
                        # Decrypt agent private key
                        pk = decrypt_private_key(encrypted_pk)
                        agent_account = Account.from_key(pk)
                        
                        # Build LP flow
                        builder = AerodromeDualLPBuilder()
                        usdc_wei = int(allocation_per_pool * 1e6)
                        
                        # Parse LP pair from symbol (e.g., "SOL/USDC" or "WETH-AERO")
                        pair = symbol.replace("-", "/").replace(" / ", "/")
                        tokens = [t.strip().upper() for t in pair.split("/")]
                        
                        # Determine which token we need to swap to
                        if len(tokens) != 2:
                            print(f"[StrategyExecutor] ⚠️ Invalid pair format: {pair}, skipping")
                            result = {"success": False, "error": f"Invalid pair format: {pair}"}
                            results.append({"pool": symbol, "protocol": project, "amount": allocation_per_pool, "result": result})
                            continue
                        
                        # For pairs with USDC: swap 50% USDC to other token
                        # For pairs without USDC: need to swap to both tokens
                        if "USDC" in tokens:
                            # SOL/USDC, WETH/USDC, etc - swap 50% USDC to other token
                            target_token = tokens[0] if tokens[1] == "USDC" else tokens[1]
                            base_token = "USDC"
                            print(f"[StrategyExecutor] USDC pair detected: swap 50% USDC → {target_token}, keep 50% USDC")
                        elif "WETH" in tokens:
                            # WETH/AERO - first swap USDC → WETH, then 50% WETH → other
                            target_token = tokens[0] if tokens[1] == "WETH" else tokens[1]
                            base_token = "WETH"
                            print(f"[StrategyExecutor] WETH pair detected: swap USDC → WETH, then 50% WETH → {target_token}")
                        else:
                            # Neither USDC nor WETH - complex routing needed
                            print(f"[StrategyExecutor] ⚠️ Complex pair {pair} - routing USDC → WETH → tokens")
                            target_token = tokens[0]
                            base_token = "WETH"
                        
                        print(f"[StrategyExecutor] Building LP flow for {pair} with ${allocation_per_pool:.2f}")
                        
                        # USDC PAIR: INSTANT swap via Aerodrome Router, then addLiquidity
                        if base_token == "USDC":
                            print(f"[StrategyExecutor] 🔄 USDC pair flow: swap 50% USDC → {target_token} (instant)")
                            
                            half_usdc = usdc_wei // 2
                            
                            # Get token addresses
                            target_addr = builder._get_token_address(target_token)
                            usdc_addr = builder._get_token_address("USDC")
                            AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
                            
                            slippage = agent.get("slippage", 0.5)  # Default 0.5%
                            deadline = int(datetime.utcnow().timestamp()) + 1200  # 20 min
                            
                            # Build all TX steps
                            steps = []
                            w3 = Web3(Web3.HTTPProvider(self.rpc_url))
                            
                            # Step 1: Approve USDC to Aerodrome Router
                            approve_usdc = builder.build_approve_calldata("USDC", AERODROME_ROUTER, half_usdc)
                            steps.append({"step": 1, "to": usdc_addr, "data": approve_usdc, "desc": f"Approve {half_usdc/1e6:.2f} USDC"})
                            
                            # Step 2: Swap USDC → target token via Aerodrome (instant)
                            swap_calldata = builder.build_swap_calldata(
                                "USDC", target_token, half_usdc, 
                                int(half_usdc * (1 - slippage/100)),  # minAmountOut with slippage
                                agent_account.address, deadline
                            )
                            steps.append({"step": 2, "to": AERODROME_ROUTER, "data": swap_calldata, "desc": f"Swap {half_usdc/1e6:.2f} USDC → {target_token}"})
                            
                            # Execute swap steps first to get target token amount
                            tx_hashes = []
                            target_received = 0
                            
                            for step in steps[:2]:  # Execute approve + swap
                                print(f"[StrategyExecutor] Executing: {step['desc']}")
                                tx = {
                                    'to': Web3.to_checksum_address(step['to']),
                                    'data': step['data'].hex() if isinstance(step['data'], bytes) else step['data'],
                                    'from': agent_account.address,
                                    'nonce': w3.eth.get_transaction_count(agent_account.address, 'latest'),
                                    'gas': 300000,
                                    'gasPrice': int(w3.eth.gas_price * 2),
                                    'chainId': 8453
                                }
                                signed_tx = agent_account.sign_transaction(tx)
                                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                                print(f"[StrategyExecutor] TX: {tx_hash.hex()}")
                                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                                if receipt.status != 1:
                                    result = {"success": False, "error": f"TX failed: {step['desc']}"}
                                    break
                                tx_hashes.append(tx_hash.hex())
                                
                                # After swap, check target token balance
                                if step['step'] == 2:
                                    # Read target token balance
                                    balance_calldata = "0x70a08231" + agent_account.address[2:].lower().zfill(64)
                                    target_balance = w3.eth.call({
                                        'to': Web3.to_checksum_address(target_addr),
                                        'data': balance_calldata
                                    })
                                    target_received = int(target_balance.hex(), 16)
                                    print(f"[StrategyExecutor] ✅ Received {target_received} {target_token} wei")
                            else:
                                # Swap succeeded, now do LP
                                if target_received > 0:
                                    # Step 3: Approve target to Router
                                    approve_target = builder.build_approve_calldata(target_token, AERODROME_ROUTER, target_received)
                                    step3 = {"step": 3, "to": target_addr, "data": approve_target, "desc": f"Approve {target_token}"}
                                    
                                    print(f"[StrategyExecutor] Executing: {step3['desc']}")
                                    tx = {
                                        'to': Web3.to_checksum_address(step3['to']),
                                        'data': step3['data'].hex() if isinstance(step3['data'], bytes) else step3['data'],
                                        'from': agent_account.address,
                                        'nonce': w3.eth.get_transaction_count(agent_account.address, 'latest'),
                                        'gas': 60000,
                                        'gasPrice': int(w3.eth.gas_price * 2),
                                        'chainId': 8453
                                    }
                                    signed_tx = agent_account.sign_transaction(tx)
                                    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                                    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                                    tx_hashes.append(tx_hash.hex())
                                    
                                    # Step 4: addLiquidity
                                    add_liq = builder.build_add_liquidity_calldata(
                                        target_token, "USDC", target_received, half_usdc,
                                        agent_account.address, slippage, deadline, stable=False
                                    )
                                    step4 = {"step": 4, "to": AERODROME_ROUTER, "data": add_liq, "desc": f"addLiquidity({target_token}/USDC)"}
                                    
                                    print(f"[StrategyExecutor] Executing: {step4['desc']}")
                                    tx = {
                                        'to': Web3.to_checksum_address(step4['to']),
                                        'data': step4['data'].hex() if isinstance(step4['data'], bytes) else step4['data'],
                                        'from': agent_account.address,
                                        'nonce': w3.eth.get_transaction_count(agent_account.address, 'latest'),
                                        'gas': 400000,
                                        'gasPrice': int(w3.eth.gas_price * 2),
                                        'chainId': 8453
                                    }
                                    signed_tx = agent_account.sign_transaction(tx)
                                    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                                    
                                    if receipt.status == 1:
                                        tx_hashes.append(tx_hash.hex())
                                        result = {"success": True, "tx_hashes": tx_hashes}
                                        print(f"[StrategyExecutor] ✅ LP position created!")
                                    else:
                                        result = {"success": False, "error": "addLiquidity failed"}
                                else:
                                    result = {"success": False, "error": "No target tokens received from swap"}
                            
                            results.append({"pool": symbol, "protocol": project, "amount": allocation_per_pool, "result": result})
                            continue
                        
                        # WETH PAIR: Use existing dual LP flow with CoW Swap
                        cow_result = await builder.build_dual_lp_flow_cowswap(
                            usdc_amount=usdc_wei,
                            target_pair=pair,
                            agent_address=agent_account.address,
                            agent_private_key=pk,
                            primary_token="USDC",
                            slippage=agent.get("slippage", 1.0)
                        )
                        
                        if not cow_result.get("success"):
                            print(f"[StrategyExecutor] CoW Swap failed: {cow_result.get('error')}")
                            print(f"[StrategyExecutor] Falling back to Aerodrome-only flow...")
                            
                            # Fallback to original method (no CoW)
                            steps = await builder.build_dual_lp_flow(
                                usdc_amount=usdc_wei,
                                target_pair=pair,
                                recipient=agent_account.address,
                                slippage=agent.get("slippage", 0.5)
                            )
                        else:
                            print(f"[StrategyExecutor] ✅ CoW order filled: {cow_result.get('cow_order_id', '')[:20]}...")
                            print(f"[StrategyExecutor] WETH received: {cow_result.get('weth_received', 0) / 1e18:.6f}")
                            steps = cow_result.get("lp_steps", [])
                        
                        print(f"[StrategyExecutor] Got {len(steps)} LP steps, executing...")
                        
                        # Execute each step
                        w3 = Web3(Web3.HTTPProvider(self.rpc_url))
                        tx_hashes = []
                        
                        for step in steps:
                            target = step.get("protocol")
                            calldata = step.get("calldata")
                            desc = step.get("description", f"Step {step.get('step')}")
                            
                            print(f"[StrategyExecutor] Executing: {desc}")
                            
                            tx = {
                                'to': Web3.to_checksum_address(target),
                                'data': calldata.hex() if isinstance(calldata, bytes) else calldata,
                                'from': agent_account.address,
                                'nonce': w3.eth.get_transaction_count(agent_account.address, 'pending'),
                                'gas': 300000,
                                'gasPrice': int(w3.eth.gas_price * 1.5),
                                'chainId': 8453
                            }
                            
                            signed_tx = agent_account.sign_transaction(tx)
                            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                            print(f"[StrategyExecutor] TX sent: {tx_hash.hex()}")
                            
                            # Wait for confirmation
                            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                            if receipt.status != 1:
                                print(f"[StrategyExecutor] ❌ Step failed: {desc}")
                                result = {"success": False, "error": f"Step failed: {desc}"}
                                break
                            
                            tx_hashes.append(tx_hash.hex())
                        else:
                            # All steps succeeded
                            result = {"success": True, "tx_hashes": tx_hashes, "steps": len(steps)}
                            print(f"[StrategyExecutor] ✅ LP deposit complete: {len(tx_hashes)} TXs")
                            
                        # Track LP allocation in agent state
                        if "lp_allocations" not in agent:
                            agent["lp_allocations"] = []
                        agent["lp_allocations"].append({
                            "pool": symbol,
                            "protocol": project,
                            "amount": allocation_per_pool,
                            "pair": pair,
                            "status": "completed" if result.get("success") else "failed",
                            "tx_hashes": tx_hashes,
                            "created_at": datetime.utcnow().isoformat()
                        })
                        
                    except Exception as lp_error:
                        print(f"[StrategyExecutor] LP execution error: {lp_error}")
                        import traceback
                        traceback.print_exc()
                        result = {"success": False, "error": str(lp_error)}
                else:
                    # Fallback: Execute TX for LP pool via V4 contract
                    print(f"[StrategyExecutor] No EOA key for LP, using V4 contract fallback")
                    result = await self.execute_v4_strategy(
                        agent=agent,
                        protocol_address=protocol_address,
                        amount_usdc=allocation_per_pool,
                        call_data=b""
                    )
            else:
                # SINGLE-SIDED: Execute via V4 contract using agent's own key
                result = await self.execute_v4_strategy(
                    agent=agent,  # Pass full agent to use its private key
                    protocol_address=protocol_address,
                    amount_usdc=allocation_per_pool,
                    call_data=b""  # Protocol-specific calldata would be encoded here
                )
            
            results.append({
                "pool": symbol,
                "protocol": project,
                "amount": allocation_per_pool,
                "is_lp": is_lp_pool or is_dex_protocol,
                "result": result
            })
        
        # Update agent with execution results
        agent["last_execution"] = datetime.utcnow().isoformat()
        agent["execution_results"] = results
        
        successful = sum(1 for r in results if r.get("result", {}).get("success", False))
        
        return {
            "success": successful > 0,
            "total_pools": len(recommended),
            "successful": successful,
            "results": results
        }


# Global executor instance
strategy_executor = StrategyExecutor()


async def start_executor():
    """Start the strategy executor (call from main app startup)"""
    asyncio.create_task(strategy_executor.start())


def stop_executor():
    """Stop the strategy executor"""
    strategy_executor.stop()
