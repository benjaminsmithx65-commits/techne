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
                
                # Execute strategy
                await self.execute_agent_strategy(agent)
                
                # Check if rebalancing needed
                if agent.get("auto_rebalance", True):
                    await self.check_rebalance_needed(agent)
            except Exception as e:
                print(f"[StrategyExecutor] Error for {agent.get('id', 'unknown')}: {e}")
    
    async def execute_agent_strategy(self, agent: dict):
        """Execute strategy for a single agent"""
        agent_id = agent.get("id", "unknown")
        
        # Check if we should execute (rate limit)
        last = self.last_execution.get(agent_id)
        if last and datetime.utcnow() - last < timedelta(minutes=5):
            return
        
        print(f"[StrategyExecutor] Executing for agent {agent_id[:15]}...")
        
        # 1. Find matching pools
        pools = await self.find_matching_pools(agent)
        
        if not pools:
            print(f"[StrategyExecutor] No matching pools found - using Aave USDC fallback")
            # Fallback: Default to Aave USDC (always available, always safe)
            pools = [{
                "symbol": "USDC",
                "project": "aave-v3",
                "apy": 6.2,
                "tvl": 500000000,
                "chain": "Base",
                "risk_score": "Low",
                "pool": "aave-usdc-base"
            }]
        
        print(f"[StrategyExecutor] Found {len(pools)} matching pools")
        
        # 2. Rank and select top pools
        selected_pools = self.rank_and_select(pools, agent)
        
        # 3. Update agent with recommendations
        agent["recommended_pools"] = selected_pools
        agent["last_scan"] = datetime.utcnow().isoformat()
        
        self.last_execution[agent_id] = datetime.utcnow()
        
        print(f"[StrategyExecutor] Recommended {len(selected_pools)} pools for {agent_id[:15]}")
        
        # 4. AUTO-EXECUTE: Check if user has idle balance and execute allocation
        user_address = agent.get("user_address")
        if user_address and selected_pools:
            try:
                idle_balance = await self.get_user_idle_balance(user_address)
                
                if idle_balance > 1:  # Minimum $1 to allocate
                    print(f"[StrategyExecutor] 💰 User has ${idle_balance:.2f} idle - auto-allocating!")
                    
                    # Execute allocation
                    result = await self.execute_allocation(agent, idle_balance)
                    
                    if result.get("success"):
                        print(f"[StrategyExecutor] ✅ Auto-allocation SUCCESS: {result.get('successful')}/{result.get('total_pools')} pools")
                    else:
                        print(f"[StrategyExecutor] ❌ Auto-allocation failed: {result.get('error')}")
                else:
                    print(f"[StrategyExecutor] User has no idle balance to allocate")
                    
            except Exception as e:
                print(f"[StrategyExecutor] Balance check error: {e}")
    
    async def get_user_idle_balance(self, user_address: str) -> float:
        """Get user's idle USDC balance from V4 contract"""
        try:
            from web3 import Web3
            
            w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(self.wallet_contract),
                abi=self.v4_abi
            )
            
            balance_wei = contract.functions.balances(
                Web3.to_checksum_address(user_address)
            ).call()
            
            return balance_wei / 1e6  # USDC has 6 decimals
            
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
        
        # Check for APY drift (>20% change)
        for alloc in allocations:
            pool_symbol = alloc.get("pool")
            old_apy = alloc.get("apy", 0)
            
            # Find current APY from recommended
            current = next((p for p in recommended if p.get("symbol") == pool_symbol), None)
            if current:
                new_apy = current.get("apy", 0)
                if old_apy > 0 and abs(new_apy - old_apy) / old_apy > 0.2:
                    print(f"[StrategyExecutor] APY drift detected: {pool_symbol} {old_apy:.1f}% → {new_apy:.1f}%")
                    agent["needs_rebalance"] = True
    
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
                min_tvl=100000,  # $100k minimum
                min_apy=agent.get("min_apy", 5),
                max_apy=agent.get("max_apy", 200),
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
                
                # Check pool type
                pool_type = agent.get("pool_type", "single")
                is_lp = any(sep in symbol for sep in ["-", "/", " / "])
                if pool_type == "single" and is_lp:
                    continue
                if pool_type == "dual" and not is_lp:
                    continue
                
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
                        
                        # Parse LP pair from symbol (e.g., "WETH/AERO" or "WETH-AERO")
                        pair = symbol.replace("-", "/").replace(" / ", "/")
                        if "WETH" not in pair.upper():
                            # Default to WETH/AERO if no WETH in pair
                            pair = "WETH/AERO"
                        
                        print(f"[StrategyExecutor] Building LP flow for {pair} with ${allocation_per_pool:.2f}")
                        
                        steps = await builder.build_dual_lp_flow(
                            usdc_amount=usdc_wei,
                            target_pair=pair,
                            recipient=agent_account.address,
                            slippage=agent.get("slippage", 0.5)
                        )
                        
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
