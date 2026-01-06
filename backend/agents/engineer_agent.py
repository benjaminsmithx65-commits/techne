"""
Engineer Agent - "The Hands" of Techne System
Execution layer for autonomous DeFi operations

MVP Scope:
- Simple ERC-4626 deposits/withdrawals (stablecoin vaults)
- Gas optimization (wait for cheap gas)
- Task queue management

Future Scope:
- Cross-chain bridging
- Multi-step zaps
- Auto-compounding

Enhanced with:
- Transaction outcome tracking via Memory Engine
- Operation tracing via Observability
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import hashlib

# Observability integration
try:
    from agents.observability_engine import observability, traced, SpanStatus
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    def traced(agent, op):
        def decorator(func): return func
        return decorator

# Memory integration  
try:
    from agents.memory_engine import memory_engine, MemoryType
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EngineerAgent")


class TaskType(Enum):
    SIMPLE_DEPOSIT = "simple_deposit"
    SIMPLE_WITHDRAW = "simple_withdraw"
    ZAP_DEPOSIT = "zap_deposit"             # Future: Multi-asset LP
    BRIDGE_AND_FARM = "bridge_and_farm"     # Future: Cross-chain
    COMPOUND = "compound"                    # Future: Auto-compound
    REBALANCE = "rebalance"                  # Future: Portfolio rebalance
    EMERGENCY_EXIT = "emergency_exit"


class TaskStatus(Enum):
    QUEUED = "queued"
    WAITING_GAS = "waiting_gas"
    EXECUTING = "executing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    FAILED_REVERTED = "failed_reverted"
    FAILED_SLIPPAGE = "failed_slippage"
    FAILED_TIMEOUT = "failed_timeout"
    CANCELLED = "cancelled"


@dataclass
class TransactionStep:
    """Single transaction in a multi-step task"""
    action: str  # "approve", "deposit", "withdraw", "swap"
    contract_address: str
    function_name: str
    calldata: bytes = b""
    gas_limit: int = 200000
    value_eth: float = 0.0


@dataclass
class EngineeringTask:
    """Task in the execution queue"""
    id: str
    user_id: str
    task_type: TaskType
    steps: List[TransactionStep] = field(default_factory=list)
    
    # Constraints
    max_gas_cost_usd: float = 5.0
    max_gas_gwei: int = 50  # Base is usually <1 gwei, but set conservative
    min_output_amount: float = 0.0  # Slippage protection
    deadline_timestamp: Optional[int] = None
    
    # Execution tracking
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    tx_hashes: List[str] = field(default_factory=list)
    actual_gas_cost_usd: Optional[float] = None
    actual_output_amount: Optional[float] = None
    error_message: Optional[str] = None


class EngineerAgent:
    """
    The Engineer - Execution Agent
    Converts opportunities into actual transactions
    
    MVP: Simple ERC-4626 deposits/withdrawals
    Future: Cross-chain, zaps, auto-compound
    """
    
    def __init__(self):
        # Task queue
        self.pending_tasks: List[EngineeringTask] = []
        self.completed_tasks: List[EngineeringTask] = []
        
        # Gas monitoring
        self.current_gas_gwei = 1  # Base is very cheap
        self.gas_check_interval = 60  # Check every minute
        
        # ERC-4626 Vault standard (Morpho, Yearn, etc.)
        self.vault_standard = "ERC-4626"
        
        # Base chain config
        self.chain_config = {
            "chain_id": 8453,  # Base
            "rpc_url": "https://mainnet.base.org",
            "gas_price_oracle": "https://base.blockscout.com/api/v1/gas-price-oracle"
        }
        
        # Protocol addresses (MVP: Base chain only)
        self.known_vaults = {
            # Will be populated from Scout's verified protocols
            # Format: "moonwell-usdc": "0x..."
        }
        
        self.is_running = False
        logger.info("🔧 Engineer Agent initialized (MVP: Simple deposits only)")
    
    async def start(self):
        """Start the engineer's execution loop"""
        self.is_running = True
        logger.info("Engineer Agent started - monitoring task queue")
        
        await asyncio.gather(
            self._gas_optimization_loop(),
            self._task_execution_loop()
        )
    
    def stop(self):
        """Stop the engineer"""
        self.is_running = False
        logger.info("Engineer Agent stopped")
    
    # ===========================================
    # MVP: SIMPLE DEPOSITS & WITHDRAWALS
    # ===========================================
    
    async def create_deposit_task(
        self, 
        user_id: str,
        vault_address: str,
        amount_usdt: float,  # Changed from amount_usdc to amount_usdt
        max_gas_usd: float = 2.0
    ) -> EngineeringTask:
        """
        Create a simple deposit task (ERC-4626 vault)
        
        PRIMARY ASSET: USDT (Hedge Fund Focus)
        
        Steps:
        1. Approve USDT to vault
        2. Call vault.deposit()
        
        Much simpler than multi-asset LP zaps!
        """
        task_id = self._generate_task_id(user_id, "deposit")
        
        # USDT on Base (PRIMARY ASSET)
        usdt_address = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
        
        task = EngineeringTask(
            id=task_id,
            user_id=user_id,
            task_type=TaskType.SIMPLE_DEPOSIT,
            steps=[
                TransactionStep(
                    action="approve",
                    contract_address=usdt_address,
                    function_name="approve",
                    # calldata would be: approve(vault_address, amount)
                    # For MVP, this is a placeholder
                ),
                TransactionStep(
                    action="deposit",
                    contract_address=vault_address,
                    function_name="deposit",
                    # calldata: deposit(amount, receiver)
                ),
            ],
            max_gas_cost_usd=max_gas_usd,
            max_gas_gwei=10,  # Base is <1 gwei usually
            min_output_amount=amount_usdt * 0.999  # 0.1% slippage tolerance
        )
        
        self.pending_tasks.append(task)
        logger.info(f"✅ Created deposit task {task_id} for ${amount_usdt} USDT (Primary Asset)")
        
        return task
    
    async def create_withdraw_task(
        self,
        user_id: str,
        vault_address: str,
        shares_amount: float,
        max_gas_usd: float = 2.0
    ) -> EngineeringTask:
        """
        Create a withdrawal task (ERC-4626)
        
        Steps:
        1. Call vault.withdraw() or vault.redeem()
        """
        task_id = self._generate_task_id(user_id, "withdraw")
        
        task = EngineeringTask(
            id=task_id,
            user_id=user_id,
            task_type=TaskType.SIMPLE_WITHDRAW,
            steps=[
                TransactionStep(
                    action="withdraw",
                    contract_address=vault_address,
                    function_name="redeem",  # ERC-4626: redeem(shares, receiver, owner)
                ),
            ],
            max_gas_cost_usd=max_gas_usd,
            max_gas_gwei=10
        )
        
        self.pending_tasks.append(task)
        logger.info(f"✅ Created withdrawal task {task_id}")
        
        return task
    
    async def create_pro_deposit_task(
        self,
        user_id: str,
        vault_address: str,
        amount_usdt: float,
        pro_config: Dict[str, Any],
        max_gas_usd: float = 2.0
    ) -> EngineeringTask:
        """
        Create a Pro Mode deposit task with advanced settings
        
        Pro Config includes:
        - leverage: float (1.0 to 3.0)
        - rebalance_threshold: int (percentage)
        - stop_loss_percent: int
        - take_profit_amount: float
        - volatility_guard: bool
        - gas_strategy: str (standard/smart/gas-saver)
        - duration: Dict with value and unit
        - custom_instructions: str
        """
        task_id = self._generate_task_id(user_id, "pro_deposit")
        
        # Extract Pro Mode settings
        leverage = pro_config.get('leverage', 1.0)
        stop_loss = pro_config.get('stopLossPercent', 15)
        take_profit = pro_config.get('takeProfitAmount', None)
        volatility_guard = pro_config.get('volatilityGuard', True)
        duration = pro_config.get('duration', {'value': 30, 'unit': 'days'})
        custom_instructions = pro_config.get('customInstructions', '')
        
        logger.info(f"🔥 PRO MODE Task Created:")
        logger.info(f"   Leverage: {leverage}x")
        logger.info(f"   Stop Loss: {stop_loss}%")
        logger.info(f"   Take Profit: ${take_profit if take_profit else 'None'}")
        logger.info(f"   Volatility Guard: {volatility_guard}")
        logger.info(f"   Duration: {duration.get('value')} {duration.get('unit')}")
        if custom_instructions:
            logger.info(f"   Custom: {custom_instructions[:50]}...")
        
        # USDT on Base
        usdt_address = "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2"
        
        # Build steps based on leverage
        steps = [
            TransactionStep(
                action="approve",
                contract_address=usdt_address,
                function_name="approve",
            ),
        ]
        
        # If leveraged, add loop steps
        if leverage > 1.0:
            # For Smart Looping: deposit, borrow, deposit again
            loop_iterations = int((leverage - 1) * 2)  # Approximate number of loops
            logger.info(f"   Loop iterations: {loop_iterations}")
            
            for i in range(loop_iterations):
                steps.append(TransactionStep(
                    action="deposit_loop",
                    contract_address=vault_address,
                    function_name="supply",
                ))
                steps.append(TransactionStep(
                    action="borrow_loop", 
                    contract_address=vault_address,
                    function_name="borrow",
                ))
        else:
            steps.append(TransactionStep(
                action="deposit",
                contract_address=vault_address,
                function_name="deposit",
            ))
        
        task = EngineeringTask(
            id=task_id,
            user_id=user_id,
            task_type=TaskType.SIMPLE_DEPOSIT,  # Can add PRO_DEPOSIT later
            steps=steps,
            max_gas_cost_usd=max_gas_usd,
            max_gas_gwei=10,
            min_output_amount=amount_usdt * 0.999
        )
        
        # Store pro config for monitoring
        task.pro_config = pro_config  # type: ignore
        
        self.pending_tasks.append(task)
        logger.info(f"✅ Created PRO deposit task {task_id} for ${amount_usdt} USDT @ {leverage}x")
        
        return task
    
    # ===========================================
    # GAS OPTIMIZATION LOOP
    # ===========================================
    
    async def _gas_optimization_loop(self):
        """
        Continuously monitor gas prices
        Execute tasks when gas is below threshold
        """
        while self.is_running:
            try:
                # Get current gas price
                self.current_gas_gwei = await self._get_gas_price()
                
                # Check if any queued tasks can execute
                for task in self.pending_tasks:
                    if task.status == TaskStatus.QUEUED:
                        if self.current_gas_gwei <= task.max_gas_gwei:
                            logger.info(f"✅ Gas price OK ({self.current_gas_gwei} gwei) - executing task {task.id}")
                            task.status = TaskStatus.EXECUTING
                        else:
                            task.status = TaskStatus.WAITING_GAS
                            logger.debug(f"⏳ Task {task.id} waiting for gas: {self.current_gas_gwei} > {task.max_gas_gwei}")
                
            except Exception as e:
                logger.error(f"Gas monitoring failed: {e}")
            
            await asyncio.sleep(self.gas_check_interval)
    
    async def _get_gas_price(self) -> float:
        """
        Get current gas price in gwei
        
        MVP: Returns mock low price (Base is very cheap)
        Production: Should query Base gas price oracle
        """
        # For MVP, simulate very low gas (Base reality)
        return 0.5  # gwei
    
    # ===========================================
    # TASK EXECUTION LOOP
    # ===========================================
    
    async def _task_execution_loop(self):
        """
        Execute tasks that are ready
        """
        while self.is_running:
            try:
                executing_tasks = [
                    t for t in self.pending_tasks 
                    if t.status == TaskStatus.EXECUTING
                ]
                
                for task in executing_tasks:
                    await self._execute_task(task)
                
            except Exception as e:
                logger.error(f"Task execution failed: {e}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def _execute_task(self, task: EngineeringTask):
        """
        Execute a single task
        
        MVP: Simulates execution (no actual Web3 calls)
        Production: Should use Web3.py or ethers.js
        """
        logger.info(f"🔧 Executing task {task.id} ({task.task_type.value})")
        
        try:
            # Simulate execution delay
            await asyncio.sleep(2)
            
            # For MVP, mark as completed
            # In production, this would:
            # 1. Build transaction calldata
            # 2. Sign with user's Smart Account
            # 3. Submit to RPC
            # 4. Wait for confirmation
            # 5. Verify result
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.actual_gas_cost_usd = 0.05  # Simulate cheap Base gas
            task.tx_hashes = ["0xmocked_tx_hash"]
            
            # Move to completed
            self.pending_tasks.remove(task)
            self.completed_tasks.append(task)
            
            logger.info(f"✅ Task {task.id} completed - Gas: ${task.actual_gas_cost_usd}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED_REVERTED
            task.error_message = str(e)
            logger.error(f"❌ Task {task.id} failed: {e}")
    
    # ===========================================
    # FUTURE: CROSS-CHAIN OPERATIONS
    # ===========================================
    
    async def create_cross_chain_task(
        self,
        user_id: str,
        from_chain: str,
        to_chain: str,
        amount: float,
        target_vault: str
    ) -> EngineeringTask:
        """
        FUTURE FEATURE: Cross-chain yield arbitrage
        
        Steps:
        1. Withdraw from source chain vault
        2. Bridge to target chain (Stargate/Across)
        3. Deposit to target chain vault
        
        This is the "Roampal" feature - agents migrating funds
        """
        logger.warning("Cross-chain operations not yet implemented (Phase 2)")
        raise NotImplementedError("Phase 2 feature")
    
    # ===========================================
    # HELPERS
    # ===========================================
    
    def _generate_task_id(self, user_id: str, task_type: str) -> str:
        """Generate unique task ID"""
        timestamp = datetime.now().isoformat()
        data = f"{user_id}-{task_type}-{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a task"""
        # Check pending
        for task in self.pending_tasks:
            if task.id == task_id:
                return {
                    "id": task.id,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat(),
                    "gas_cost": task.actual_gas_cost_usd,
                    "tx_hashes": task.tx_hashes
                }
        
        # Check completed
        for task in self.completed_tasks:
            if task.id == task_id:
                return {
                    "id": task.id,
                    "status": task.status.value,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "gas_cost": task.actual_gas_cost_usd,
                    "tx_hashes": task.tx_hashes
                }
        
        return None
    
    def get_pending_tasks(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get all pending tasks, optionally filtered by user"""
        tasks = self.pending_tasks
        if user_id:
            tasks = [t for t in tasks if t.user_id == user_id]
        
        return [
            {
                "id": t.id,
                "type": t.task_type.value,
                "status": t.status.value,
                "created_at": t.created_at.isoformat()
            }
            for t in tasks
        ]


# Singleton instance
engineer = EngineerAgent()
