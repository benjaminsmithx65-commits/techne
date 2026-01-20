"""
Deposit Monitor & Auto-Allocator
Monitors agent wallets for deposits and triggers automatic allocation
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional
from web3 import Web3
import httpx

# Token addresses on Base
TOKENS = {
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    "WETH": "0x4200000000000000000000000000000000000006",
    "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
}

# Token decimals
DECIMALS = {"USDC": 6, "USDT": 6, "WETH": 18, "DAI": 18, "ETH": 18}

# ERC20 ABI for balance checking
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], 
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], 
     "type": "function"}
]


class DepositMonitor:
    """
    Monitors agent wallets and triggers allocation when deposits detected
    
    Flow:
    1. Poll balances every 30 seconds
    2. Detect new deposits (balance increase)
    3. Trigger Strategy Executor
    4. Execute swaps + deposits to pools
    """
    
    def __init__(self):
        self.running = False
        self.poll_interval = 30  # seconds
        
        # Track last known balances
        self.last_balances: Dict[str, Dict[str, int]] = {}
        
        # RPC - use public Base RPC or env override
        self.rpc_url = os.getenv(
            "ALCHEMY_RPC_URL",
            "https://mainnet.base.org"  # Public Base RPC (no rate limits)
        )
        self.w3 = None
    
    def _get_web3(self) -> Web3:
        """Get Web3 instance (lazy init)"""
        if not self.w3:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        return self.w3
    
    async def start(self):
        """Start monitoring loop"""
        self.running = True
        print("[DepositMonitor] Starting deposit monitoring...")
        
        while self.running:
            try:
                await self.check_all_agents()
            except Exception as e:
                print(f"[DepositMonitor] Error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        print("[DepositMonitor] Stopped")
    
    async def check_all_agents(self):
        """Check balances for all deployed agents"""
        try:
            from api.agent_config_router import DEPLOYED_AGENTS
        except ImportError:
            return
        
        # DEPLOYED_AGENTS is {user_address: [list of agents]}
        active_agents = []
        for user_agents in DEPLOYED_AGENTS.values():
            for agent in user_agents:
                if agent.get("is_active", False):
                    active_agents.append(agent)
        
        for agent in active_agents:
            await self.check_agent_balance(agent)
    
    async def check_agent_balance(self, agent: dict):
        """Check and compare balance for an agent"""
        agent_address = agent.get("agent_address")
        user_address = agent.get("user_address")
        
        if not agent_address:
            return
        
        # Get current balances
        current = await self.get_balances(agent_address)
        previous = self.last_balances.get(agent_address, {})
        
        # Detect deposits
        deposits = []
        for token, balance in current.items():
            prev_balance = previous.get(token, 0)
            if balance > prev_balance:
                deposit_amount = balance - prev_balance
                deposits.append({
                    "token": token,
                    "amount": deposit_amount,
                    "formatted": self.format_amount(token, deposit_amount)
                })
        
        # Update stored balances
        self.last_balances[agent_address] = current
        
        # If deposits detected, trigger allocation
        if deposits:
            print(f"[DepositMonitor] New deposits for {agent_address[:10]}:")
            for d in deposits:
                print(f"  + {d['formatted']} {d['token']}")
            
            await self.trigger_allocation(agent, deposits)
    
    async def get_balances(self, address: str) -> Dict[str, int]:
        """Get token balances for an address"""
        w3 = self._get_web3()
        balances = {}
        
        try:
            # Ensure address is checksum formatted
            checksum_address = Web3.to_checksum_address(address)
            
            # ETH balance
            eth_balance = w3.eth.get_balance(checksum_address)
            balances["ETH"] = eth_balance
            
            # ERC20 balances
            for symbol, token_address in TOKENS.items():
                try:
                    contract = w3.eth.contract(
                        address=Web3.to_checksum_address(token_address),
                        abi=ERC20_ABI
                    )
                    balance = contract.functions.balanceOf(
                        Web3.to_checksum_address(address)
                    ).call()
                    balances[symbol] = balance
                except Exception as e:
                    balances[symbol] = 0
                    
        except Exception as e:
            print(f"[DepositMonitor] Balance check error: {e}")
        
        return balances
    
    def format_amount(self, token: str, amount: int) -> str:
        """Format amount with proper decimals"""
        decimals = DECIMALS.get(token, 18)
        formatted = amount / (10 ** decimals)
        return f"{formatted:.4f}"
    
    async def trigger_allocation(self, agent: dict, deposits: List[dict]):
        """Trigger automatic allocation based on new deposits"""
        try:
            # Import executor
            from agents.strategy_executor import strategy_executor
            
            # Calculate total deposit value in USD
            total_usd = 0
            for d in deposits:
                if d["token"] in ["USDC", "USDT", "DAI"]:
                    total_usd += d["amount"] / (10 ** 6)
                elif d["token"] in ["ETH", "WETH"]:
                    # Assume ~$3500 ETH (should use price feed)
                    total_usd += (d["amount"] / (10 ** 18)) * 3500
            
            print(f"[DepositMonitor] Total deposit value: ${total_usd:.2f}")
            
            # Update agent with deposit info
            agent["pending_allocation"] = {
                "deposits": deposits,
                "total_usd": total_usd,
                "detected_at": datetime.utcnow().isoformat()
            }
            
            # Get pool recommendations
            await strategy_executor.execute_agent_strategy(agent)
            
            recommended = agent.get("recommended_pools", [])
            if not recommended:
                print(f"[DepositMonitor] No pools recommended, skipping allocation")
                return
            
            # Execute allocation
            await self.execute_allocation(agent, deposits, recommended)
            
        except Exception as e:
            print(f"[DepositMonitor] Allocation trigger error: {e}")
    
    async def execute_allocation(
        self, 
        agent: dict, 
        deposits: List[dict], 
        pools: List[dict]
    ):
        """Execute the actual allocation to pools using strategy executor"""
        try:
            from agents.strategy_executor import strategy_executor
            
            agent_address = agent.get("agent_address")
            print(f"[DepositMonitor] Executing allocation to {len(pools)} pools...")
            
            # Calculate total deposit value in USD
            total_usd = 0
            for d in deposits:
                if d["token"] in ["USDC", "USDT", "DAI"]:
                    total_usd += d["amount"] / (10 ** 6)
                elif d["token"] in ["ETH", "WETH"]:
                    # Use ETH price from agent or default
                    eth_price = agent.get("eth_price", 3500)
                    total_usd += (d["amount"] / (10 ** 18)) * eth_price
            
            if total_usd < 10:
                print(f"[DepositMonitor] Deposit too small (${total_usd:.2f}), minimum $10")
                return
            
            # Set recommended pools on agent
            agent["recommended_pools"] = pools
            
            # Execute allocation via strategy executor (real on-chain)
            result = await strategy_executor.execute_allocation(
                agent=agent,
                amount_usdc=total_usd
            )
            
            if result.get("success"):
                successful = result.get("successful", 0)
                total = result.get("total_pools", 0)
                print(f"[DepositMonitor] ✓ Allocated to {successful}/{total} pools")
                
                # Update agent status
                agent["last_allocation"] = datetime.utcnow().isoformat()
                agent["allocation_count"] = agent.get("allocation_count", 0) + successful
                agent["total_allocated_usd"] = agent.get("total_allocated_usd", 0) + total_usd
                
                # Log individual allocations
                for pool_result in result.get("results", []):
                    if pool_result.get("result", {}).get("success"):
                        agent.setdefault("allocations", []).append({
                            "pool": pool_result.get("pool"),
                            "protocol": pool_result.get("protocol"),
                            "amount": pool_result.get("amount"),
                            "tx_hash": pool_result.get("result", {}).get("tx_hash"),
                            "allocated_at": datetime.utcnow().isoformat()
                        })
            else:
                error = result.get("error", "Unknown error")
                print(f"[DepositMonitor] ✗ Allocation failed: {error}")
                agent["allocation_error"] = error
            
        except Exception as e:
            print(f"[DepositMonitor] Allocation execution error: {e}")
            agent["allocation_error"] = str(e)
    
    def get_required_token(self, pool: dict) -> str:
        """Determine what token the pool needs"""
        symbol = (pool.get("symbol") or "").upper()
        
        if "USDC" in symbol:
            return "USDC"
        elif "USDT" in symbol:
            return "USDT"
        elif "DAI" in symbol:
            return "DAI"
        elif "ETH" in symbol or "WETH" in symbol:
            return "WETH"
        else:
            return "USDC"  # Default
    
    def find_deposit_token(self, deposits: List[dict], required: str) -> Optional[dict]:
        """Find the best deposit token to use"""
        # First check if we have the required token
        for d in deposits:
            if d["token"] == required:
                return d
        
        # Otherwise use the largest deposit
        if deposits:
            return max(deposits, key=lambda x: x["amount"])
        
        return None


# Global monitor instance
deposit_monitor = DepositMonitor()


async def start_deposit_monitoring():
    """Start the deposit monitor (call from main app startup)"""
    asyncio.create_task(deposit_monitor.start())


def stop_deposit_monitoring():
    """Stop the deposit monitor"""
    deposit_monitor.stop()
