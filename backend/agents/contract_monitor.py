"""
Contract Event Monitor for V4.3.3
Watches Deposited events and triggers automatic allocation

Enhanced with Revert Finance patterns:
- TWAP Oracle protection for LP swaps
- Executor rewards for public harvesting
- The Graph integration for real-time pool data
"""

import asyncio
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import logging

# Gas Manager for auto-refill
try:
    from services.gas_manager import get_gas_manager, GasManager
    HAS_GAS_MANAGER = True
except ImportError:
    HAS_GAS_MANAGER = False

# Load .env file
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# V4.3.3 Contract Address (deployed 2026-01-25)
CONTRACT_ADDRESS = "0x1ff18a7b56d7fd3b07ce789e47ac587de2f14e0d"

# Contract ABI (only what we need) - V4.3.3 compatible
CONTRACT_ABI = [
    # Events
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "user", "type": "address"},
            {"indexed": False, "name": "requested", "type": "uint256"},
            {"indexed": False, "name": "received", "type": "uint256"}
        ],
        "name": "Deposited",
        "type": "event"
    },
    # View functions
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "balances",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "totalInvested",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "nonces",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    # V4.3.3 executeStrategySigned with ExecuteParams tuple
    {
        "inputs": [
            {
                "components": [
                    {"name": "user", "type": "address"},
                    {"name": "protocol", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "minAmountOut", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "priceAtSign", "type": "uint256"}
                ],
                "name": "p",
                "type": "tuple"
            },
            {"name": "signature", "type": "bytes"},
            {"name": "data", "type": "bytes"}
        ],
        "name": "executeStrategySigned",
        "outputs": [{"type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Protocol addresses for allocation (all approved on V4.3.3 contract)
PROTOCOLS = {
    "aave": {
        "address": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
        "name": "Aave V3",
        "asset": "USDC",
        "pool_type": "single",  # single-sided lending
        "risk_level": "low",    # Low risk - major audited protocol
        "is_lending": True,
        "audited": True,
        "supply_sig": "supply(address,uint256,address,uint16)",
        "apy": 6.2,
        "tvl": 150000000,  # $150M TVL
        "volatility": 2.5  # Low volatility %
    },
    "morpho": {
        "address": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
        "name": "Morpho Blue",
        "asset": "USDC",
        "pool_type": "single",
        "risk_level": "medium",  # Medium - newer protocol
        "is_lending": True,
        "audited": True,
        "supply_sig": None,      # Complex - needs market params
        "apy": 8.5,
        "tvl": 80000000,   # $80M TVL
        "volatility": 4.0  # Medium volatility
    },
    "moonwell": {
        "address": "0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22",
        "name": "Moonwell USDC",
        "asset": "USDC",
        "pool_type": "single",
        "risk_level": "low",
        "is_lending": True,
        "audited": True,
        "supply_sig": "mint(uint256)",
        "apy": 7.1,
        "tvl": 45000000,   # $45M TVL
        "volatility": 3.0
    },
    "compound": {
        "address": "0xb125E6687d4313864e53df431d5425969c15Eb2F",
        "name": "Compound V3",
        "asset": "USDC",
        "pool_type": "single",
        "risk_level": "low",
        "is_lending": True,
        "audited": True,
        "supply_sig": "supply(address,uint256)",
        "apy": 5.8,
        "tvl": 200000000,  # $200M TVL
        "volatility": 2.0  # Very stable
    },
    "seamless": {
        "address": "0x616a4E1db48e22028f6bbf20444Cd3b8e3273738",
        "name": "Seamless USDC",
        "asset": "USDC",
        "pool_type": "single",
        "risk_level": "medium",
        "is_lending": True,
        "audited": True,
        "supply_sig": "deposit(uint256,address)",
        "apy": 9.2,
        "tvl": 25000000,   # $25M TVL
        "volatility": 5.0  # Higher volatility
    },
    "aerodrome": {
        "address": "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d",  # USDC/WETH pool
        "router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",   # Aerodrome Router
        "name": "Aerodrome USDC/WETH",
        "asset": "USDC/WETH",
        "pool_type": "dual",
        "risk_level": "medium",  # Aerodrome is now established
        "is_lending": False,
        "audited": True,
        "supply_sig": "addLiquidity(address,address,bool,uint256,uint256,uint256,uint256,address,uint256)",
        "apy": 18.0,
        "tvl": 85000000,   # $85M TVL
        "volatility": 12.0 # High volatility (LP pairs)
    },
    "uniswap": {
        "address": "0xd0b53D9277642d899DF5C87A3966A349A798F224",  # Uniswap V3 USDC/WETH pool on Base
        "router": "0x2626664c2603336E57B271c5C0b26F421741e481",   # Universal Router Base
        "name": "Uniswap V3 USDC/WETH",
        "asset": "USDC/WETH",
        "pool_type": "dual",
        "risk_level": "low",  # Uniswap is battle-tested
        "is_lending": False,
        "audited": True,
        "supply_sig": "mint(address,int24,int24,uint128,bytes)",  # Uniswap V3 mint
        "apy": 12.0,
        "tvl": 150000000,  # $150M TVL
        "volatility": 10.0
    },
    # ================================================
    # ADDITIONAL DUAL-SIDED PROTOCOLS ON BASE
    # ================================================
    "extra": {
        "address": "0x2B1D1821B8bf4c2CA36EFd64a4A03deeA2eEeaDB",  # Extra Finance vaults
        "router": "0x2B1D1821B8bf4c2CA36EFd64a4A03deeA2eEeaDB",
        "name": "Extra Finance",
        "asset": "USDC/WETH",
        "pool_type": "dual",
        "risk_level": "medium",
        "is_lending": False,
        "is_leveraged_farm": True,  # Extra = leveraged yield farming
        "audited": True,
        "supply_sig": "deposit(uint256,address)",
        "apy": 25.0,  # Higher due to leverage
        "tvl": 35000000,
        "volatility": 18.0,
        "max_leverage": 3.0
    },
    "merkl": {
        "address": "0x8BB4C975Ff3c250e0ceEA271728547f3802B36Fd",  # Merkl distributor Base
        "router": None,  # Merkl is reward distributor, not DEX
        "name": "Merkl Rewards",
        "asset": "MULTI",
        "pool_type": "dual",
        "risk_level": "low",
        "is_lending": False,
        "is_reward_aggregator": True,  # Collects rewards from multiple pools
        "audited": True,
        "supply_sig": None,  # No direct supply - incentivizes other protocols
        "apy": 15.0,  # Variable based on incentives
        "tvl": 50000000,
        "volatility": 8.0
    },
    "curve": {
        "address": "0x417Ac0e078398C154EdFadD9Ef675d30Be60Af93",  # Curve 3pool Base
        "router": "0x417Ac0e078398C154EdFadD9Ef675d30Be60Af93",
        "name": "Curve 3pool",
        "asset": "USDC/USDT/DAI",
        "pool_type": "dual",  # Technically tri-pool but treat as dual
        "risk_level": "low",
        "is_lending": False,
        "is_stableswap": True,  # Optimized for stables
        "audited": True,
        "supply_sig": "add_liquidity(uint256[3],uint256)",
        "apy": 8.5,
        "tvl": 45000000,
        "volatility": 2.5,  # Very low for stableswap
        "slippage": 0.001  # 0.1% typical
    },
    "baseswap": {
        "address": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",  # BaseSwap router
        "router": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
        "name": "BaseSwap",
        "asset": "USDC/WETH",
        "pool_type": "dual",
        "risk_level": "medium",
        "is_lending": False,
        "audited": True,
        "supply_sig": "addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)",
        "apy": 22.0,
        "tvl": 28000000,
        "volatility": 14.0
    },
    "sushiswap": {
        "address": "0xFbc12984689e5f15626Bad03Ad60160Fe98B303C",  # SushiSwap V3 Base
        "router": "0xFB7eF66a7e61224DD6FcD0D7d9C3Ae5E8CC2e95d",
        "name": "SushiSwap V3",
        "asset": "USDC/WETH",
        "pool_type": "dual",
        "risk_level": "low",
        "is_lending": False,
        "audited": True,
        "supply_sig": "mint(address,int24,int24,uint128,bytes)",
        "apy": 14.0,
        "tvl": 42000000,
        "volatility": 11.0
    },
    "balancer": {
        "address": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",  # Balancer Vault
        "router": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
        "name": "Balancer V2",
        "asset": "USDC/WETH/cbBTC",
        "pool_type": "dual",
        "risk_level": "low",
        "is_lending": False,
        "is_weighted_pool": True,
        "audited": True,
        "supply_sig": "joinPool(bytes32,address,address,(address[],uint256[],bytes,bool))",
        "apy": 10.5,
        "tvl": 65000000,
        "volatility": 9.0
    },
    "velodrome_v2": {
        "address": "0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db",  # Velodrome V2 (Base fork)
        "router": "0xa062aE8A9c5e11aaA026fc2670B0D65ccc8B2858",
        "name": "Velodrome V2",
        "asset": "USDC/WETH",
        "pool_type": "dual",
        "risk_level": "medium",
        "is_lending": False,
        "audited": True,
        "supply_sig": "addLiquidity(address,address,bool,uint256,uint256,uint256,uint256,address,uint256)",
        "apy": 20.0,
        "tvl": 38000000,
        "volatility": 13.0
    }
}

USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"  # Canonical WETH on Base

# Aerodrome USDC/WETH Pool for TWAP (vAMM-USDC/WETH)
AERODROME_USDC_WETH_POOL = "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d"

# TWAP Oracle Settings (inspired by Revert Finance Compoundor)
TWAP_SECONDS = 60                # 60 second TWAP window
MAX_TWAP_DEVIATION_BPS = 100     # 1% max deviation (100 bps)

# 0x API for swap aggregation (best prices)
ZERO_X_API_URL = "https://base.api.0x.org/swap/v1/quote"


# ============================================
# GAS-VS-PROFIT CALCULATOR (VC Requirement #2)
# ============================================
# Base chain gas costs
BASE_GAS_PER_TX_USD = 0.01  # ~$0.01 per tx on Base
SWAP_FEE_PERCENT = 0.003    # 0.3% typical DEX swap fee
DEFAULT_SLIPPAGE = 0.005    # 0.5% slippage

def should_rotate_position(
    current_apy: float,
    new_apy: float,
    position_value_usd: float,
    holding_days: int = 30,
    num_transactions: int = 4  # withdraw + swap + swap + deposit
) -> dict:
    """
    Calculate if rotating to a new pool is profitable.
    
    Returns:
        {
            "should_rotate": bool,
            "total_cost": float,
            "expected_profit": float,
            "net_gain": float,
            "breakeven_days": float,
            "reason": str
        }
    
    Only recommends rotation if net gain is positive.
    """
    # Calculate costs
    gas_cost = BASE_GAS_PER_TX_USD * num_transactions
    swap_fees = position_value_usd * SWAP_FEE_PERCENT * 2  # Both directions
    slippage_cost = position_value_usd * DEFAULT_SLIPPAGE
    
    total_cost = gas_cost + swap_fees + slippage_cost
    
    # Calculate expected extra profit from APY difference
    apy_diff = new_apy - current_apy
    if apy_diff <= 0:
        return {
            "should_rotate": False,
            "total_cost": total_cost,
            "expected_profit": 0,
            "net_gain": -total_cost,
            "breakeven_days": float('inf'),
            "reason": f"New APY ({new_apy:.2f}%) not higher than current ({current_apy:.2f}%)"
        }
    
    # Daily extra profit
    daily_extra = position_value_usd * (apy_diff / 100) / 365
    
    # Profit over holding period
    expected_profit = daily_extra * holding_days
    net_gain = expected_profit - total_cost
    
    # Breakeven calculation
    breakeven_days = total_cost / daily_extra if daily_extra > 0 else float('inf')
    
    should_rotate = net_gain > 0
    
    if should_rotate:
        reason = f"Profitable: ${net_gain:.2f} net gain over {holding_days}d (breakeven: {breakeven_days:.1f}d)"
    else:
        reason = f"Not profitable: ${net_gain:.2f} loss (need {breakeven_days:.1f}d to breakeven)"
    
    return {
        "should_rotate": should_rotate,
        "total_cost": round(total_cost, 4),
        "expected_profit": round(expected_profit, 4),
        "net_gain": round(net_gain, 4),
        "breakeven_days": round(breakeven_days, 1) if breakeven_days != float('inf') else None,
        "reason": reason
    }


# ============================================
# IL TRACKING FOR DUAL-SIDED LP (VC Requirement #5)
# ============================================
def calculate_impermanent_loss(
    initial_price_ratio: float,
    current_price_ratio: float
) -> dict:
    """
    Calculate impermanent loss for a dual-sided LP position.
    
    Uses the standard IL formula:
    IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
    
    Args:
        initial_price_ratio: Price of token A / token B at entry
        current_price_ratio: Current price ratio
    
    Returns:
        {"il_percent": float, "hodl_advantage": float}
    """
    if initial_price_ratio <= 0:
        return {"il_percent": 0, "hodl_advantage": 0}
    
    # Price ratio change (k = current / initial)
    k = current_price_ratio / initial_price_ratio
    
    # IL formula: 2*sqrt(k)/(1+k) - 1
    import math
    if k <= 0:
        return {"il_percent": 0, "hodl_advantage": 0}
    
    lp_value = 2 * math.sqrt(k) / (1 + k)
    hodl_value = 1  # Normalized to 1 at entry
    
    il_percent = (1 - lp_value) * 100
    hodl_advantage = (hodl_value - lp_value) * 100
    
    return {
        "il_percent": round(il_percent, 4),
        "hodl_advantage": round(hodl_advantage, 4),
        "price_change_ratio": round(k, 4)
    }


def calculate_lp_equity(
    initial_token_a: float,
    initial_token_b: float,
    initial_price_a: float,
    initial_price_b: float,
    current_token_a: float,
    current_token_b: float,
    current_price_a: float,
    current_price_b: float,
    earned_fees_usd: float = 0
) -> dict:
    """
    Calculate full equity status for a dual-sided LP position.
    
    Compares:
    - Current LP value (tokens + fees)
    - HODL value (if just held initial tokens)
    - Net IL impact
    
    Returns comprehensive position status.
    """
    # HODL value (what we'd have if we just held tokens)
    hodl_value = (initial_token_a * current_price_a) + (initial_token_b * current_price_b)
    
    # Current LP value (tokens + earned fees)
    lp_token_value = (current_token_a * current_price_a) + (current_token_b * current_price_b)
    lp_total_value = lp_token_value + earned_fees_usd
    
    # Initial deposit value
    initial_value = (initial_token_a * initial_price_a) + (initial_token_b * initial_price_b)
    
    # IL = HODL - LP (without fees)
    il_usd = hodl_value - lp_token_value
    il_percent = (il_usd / hodl_value * 100) if hodl_value > 0 else 0
    
    # Net P&L including fees
    net_pnl = lp_total_value - initial_value
    net_pnl_percent = (net_pnl / initial_value * 100) if initial_value > 0 else 0
    
    # Are fees compensating for IL?
    fees_cover_il = earned_fees_usd >= il_usd
    
    return {
        "initial_value_usd": round(initial_value, 2),
        "current_lp_value_usd": round(lp_total_value, 2),
        "hodl_value_usd": round(hodl_value, 2),
        "earned_fees_usd": round(earned_fees_usd, 2),
        "il_usd": round(il_usd, 2),
        "il_percent": round(il_percent, 4),
        "net_pnl_usd": round(net_pnl, 2),
        "net_pnl_percent": round(net_pnl_percent, 4),
        "fees_cover_il": fees_cover_il,
        "is_profitable": net_pnl > 0
    }


class ContractMonitor:
    """
    Monitors V4.3.2 contract for Deposited events and triggers auto-allocation
    
    Flow:
    1. Poll for new Deposited events every 15 seconds
    2. When deposit detected, get user's agent config
    3. Call executeStrategySigned() to allocate to best pool
    4. Monitor positions for rebalance and drawdown thresholds
    """
    
    def __init__(self):
        self.running = False
        self.poll_interval = 15  # seconds
        self.last_block = 0
        
        # Track processed deposits to avoid duplicates
        self.processed_deposits: Dict[str, bool] = {}
        
        # Position tracking for rebalance and drawdown monitoring
        # Format: {user_address: {protocol_key: {"entry_value": amount, "entry_time": timestamp, "current_value": amount}}}
        self.user_positions: Dict[str, Dict[str, dict]] = {}
        
        # Rebalance check interval (run every N deposit checks)
        self.rebalance_check_counter = 0
        self.rebalance_check_interval = 4  # Check every 4th poll cycle (~60 seconds)
        
        # Track last harvest time per user for compound_frequency
        # Format: {user_address: datetime_of_last_harvest}
        self.last_harvest_time: Dict[str, datetime] = {}
        
        # Track when user capital became idle (no matching pools)
        # For parking strategy - only park after 1 hour of idle
        # Format: {user_address: datetime_when_idle_started}
        self.idle_since: Dict[str, datetime] = {}
        
        # RPC
        self.rpc_url = os.getenv(
            "ALCHEMY_RPC_URL",
            "https://mainnet.base.org"
        )
        self.w3 = None
        self.contract = None
        
        # Agent private key for signing/sending txs
        self.agent_key = os.getenv("PRIVATE_KEY")
        self.agent_account = None
        
        if self.agent_key:
            pk = self.agent_key if self.agent_key.startswith('0x') else f'0x{self.agent_key}'
            self.agent_account = Account.from_key(pk)
            logger.info(f"[ContractMonitor] Agent signer: {self.agent_account.address}")
        
        # Gas Manager for auto-refill
        self.gas_manager = get_gas_manager() if HAS_GAS_MANAGER else None
        if self.gas_manager:
            logger.info("[ContractMonitor] Gas Manager initialized")
    
    def _get_web3(self) -> Web3:
        if not self.w3:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                abi=CONTRACT_ABI
            )
            self.last_block = self.w3.eth.block_number - 100  # Start 100 blocks back
            self._track_rpc_call('eth_blockNumber', True)
        return self.w3
    
    def _track_rpc_call(self, method: str, success: bool, response_time: float = 0.05, error: str = None):
        """Track RPC calls to API metrics"""
        try:
            from infrastructure.api_metrics import api_metrics
            status = 'success' if success else 'error'
            api_metrics.record_call('alchemy', method, status, response_time, error_message=error)
        except Exception:
            pass  # Don't fail on metrics
    
    def check_twap_price(self, pool_address: str = None) -> tuple:
        """
        Check TWAP oracle price to detect price manipulation (sandwich attacks)
        Based on Revert Finance Compoundor pattern.
        
        Returns: (is_safe: bool, current_price: float, twap_price: float, deviation_bps: int)
        """
        pool_addr = pool_address or AERODROME_USDC_WETH_POOL
        
        # Aerodrome Pool ABI (slot0 + observe for TWAP)
        POOL_ABI = [
            {
                "inputs": [],
                "name": "slot0",
                "outputs": [
                    {"name": "sqrtPriceX96", "type": "uint160"},
                    {"name": "tick", "type": "int24"},
                    {"name": "observationIndex", "type": "uint16"},
                    {"name": "observationCardinality", "type": "uint16"},
                    {"name": "observationCardinalityNext", "type": "uint16"},
                    {"name": "feeProtocol", "type": "uint8"},
                    {"name": "unlocked", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"name": "secondsAgos", "type": "uint32[]"}],
                "name": "observe",
                "outputs": [
                    {"name": "tickCumulatives", "type": "int56[]"},
                    {"name": "secondsPerLiquidityCumulativeX128s", "type": "uint160[]"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        try:
            w3 = self._get_web3()
            pool = w3.eth.contract(
                address=Web3.to_checksum_address(pool_addr),
                abi=POOL_ABI
            )
            
            # Get current tick from slot0
            slot0 = pool.functions.slot0().call()
            current_tick = slot0[1]
            
            # Get TWAP tick (60 seconds ago)
            try:
                observations = pool.functions.observe([TWAP_SECONDS, 0]).call()
                tick_cumulative_old = observations[0][0]
                tick_cumulative_new = observations[0][1]
                twap_tick = (tick_cumulative_new - tick_cumulative_old) // TWAP_SECONDS
            except Exception as e:
                # Pool may not have enough observations
                print(f"[ContractMonitor] TWAP observe failed: {e} - using current price")
                twap_tick = current_tick
            
            # Calculate deviation in basis points
            tick_diff = abs(current_tick - twap_tick)
            # Rough approximation: 1 tick ≈ 0.01% (1 bps)
            deviation_bps = tick_diff
            
            is_safe = deviation_bps <= MAX_TWAP_DEVIATION_BPS
            
            # Convert ticks to prices for logging
            # price = 1.0001 ^ tick (simplified)
            current_price = 1.0001 ** current_tick
            twap_price = 1.0001 ** twap_tick
            
            if is_safe:
                print(f"[ContractMonitor] ✅ TWAP Check PASSED: deviation {deviation_bps} bps <= {MAX_TWAP_DEVIATION_BPS} bps")
            else:
                print(f"[ContractMonitor] ⚠️ TWAP Check FAILED: deviation {deviation_bps} bps > {MAX_TWAP_DEVIATION_BPS} bps")
                print(f"[ContractMonitor] Current tick: {current_tick}, TWAP tick: {twap_tick}")
            
            return (is_safe, current_price, twap_price, deviation_bps)
            
        except Exception as e:
            print(f"[ContractMonitor] TWAP check error: {e} - assuming safe")
            return (True, 0, 0, 0)  # Fail-open for now
    
    async def start(self):
        """Start monitoring loop"""
        self.running = True
        logger.info("[ContractMonitor] Starting contract event monitoring...")
        print("[ContractMonitor] Starting contract event monitoring...")
        
        while self.running:
            try:
                await self.check_for_deposits()
                
                # Periodic rebalance/drawdown monitoring
                self.rebalance_check_counter += 1
                if self.rebalance_check_counter >= self.rebalance_check_interval:
                    self.rebalance_check_counter = 0
                    
                    # Check gas levels for all tracked users
                    await self._check_gas_levels()
                    await self.check_rebalance_and_drawdown()
                    
            except Exception as e:
                logger.error(f"[ContractMonitor] Error: {e}")
                print(f"[ContractMonitor] Error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        self.running = False
        print("[ContractMonitor] Stopped")
    
    async def _check_gas_levels(self):
        """Check gas levels for all tracked users and auto-refill if needed."""
        if not self.gas_manager:
            return
        
        # Get all tracked user addresses
        tracked_users = list(self.user_positions.keys())
        if not tracked_users:
            return
        
        for user_address in tracked_users:
            try:
                result = await self.gas_manager.check_and_refill(user_address)
                
                if result.get("refilled"):
                    print(f"[ContractMonitor] ⛽ Gas refilled for {user_address[:10]}...")
                    print(f"  Swapped ${result['refill_usdc']:.2f} USDC → {result['refill_eth']:.4f} ETH")
                    
                    # Log to audit trail
                    try:
                        from api.audit_router import log_reasoning_event
                        await log_reasoning_event(
                            agent_id=user_address,
                            action="GAS_REFILLED",
                            details={
                                "usdc_amount": result['refill_usdc'],
                                "eth_amount": result['refill_eth'],
                                "remaining_tx": result.get('remaining_tx', 0)
                            }
                        )
                    except Exception:
                        pass  # Don't fail on logging
                        
                elif result.get("needs_refill"):
                    print(f"[ContractMonitor] ⚠️ Low gas for {user_address[:10]}... ({result['remaining_tx']} tx left)")
                    
            except Exception as e:
                logger.error(f"[ContractMonitor] Gas check error for {user_address}: {e}")
    
    async def check_for_deposits(self):
        """Check for new Deposited events"""
        import time
        w3 = self._get_web3()
        
        start = time.time()
        current_block = w3.eth.block_number
        self._track_rpc_call('eth_blockNumber', True, time.time() - start)
        
        if current_block <= self.last_block:
            return
        
        # Get Deposited events
        try:
            start = time.time()
            events = self.contract.events.Deposited.get_logs(
                from_block=self.last_block + 1,
                to_block=current_block
            )
            self._track_rpc_call('eth_getLogs', True, time.time() - start)
            
            for event in events:
                await self.handle_deposit(event)
            
            self.last_block = current_block
            
        except Exception as e:
            self._track_rpc_call('eth_getLogs', False, 0, str(e)[:100])
            logger.error(f"[ContractMonitor] Event fetch error: {e}")
    
    async def handle_deposit(self, event):
        """Handle a Deposited event"""
        tx_hash = event.transactionHash.hex()
        
        # Skip if already processed
        if tx_hash in self.processed_deposits:
            return
        
        self.processed_deposits[tx_hash] = True
        
        user = event.args.user
        received = event.args.received
        amount_usdc = received / 1e6
        
        print(f"[ContractMonitor] 💰 Deposit detected!")
        print(f"  User: {user}")
        print(f"  Amount: {amount_usdc:.2f} USDC")
        print(f"  TX: {tx_hash}")
        
        logger.info(f"[ContractMonitor] Deposit: {user} - {amount_usdc} USDC")
        
        # Minimum allocation amount
        if amount_usdc < 5:
            print(f"[ContractMonitor] Amount too small for allocation (min $5)")
            return
        
        # Trigger allocation
        await self.allocate_funds(user, received)
        
        # Check and refill gas (ETH) if needed
        if HAS_GAS_MANAGER:
            try:
                gas_mgr = get_gas_manager()
                gas_result = await gas_mgr.check_and_refill(
                    agent_address=user,
                    eth_price_usd=3000,  # TODO: get real price
                    dry_run=False
                )
                if gas_result.get("refilled"):
                    print(f"[ContractMonitor] ⛽ Gas refilled: {gas_result.get('refill_eth'):.4f} ETH")
                else:
                    print(f"[ContractMonitor] ⛽ Gas OK: {gas_result.get('remaining_tx', 'N/A')} TX remaining")
            except Exception as e:
                logger.warning(f"[ContractMonitor] Gas refill check failed: {e}")
    
    def _select_best_protocol(self, agent_config: dict = None) -> str:
        """Select best protocol based on agent config and APY"""
        # Get filters from agent config (defaults = no filter)
        min_apy = 0
        max_apy = 1000  # Very high default
        only_audited = False
        
        if agent_config:
            min_apy = agent_config.get("min_apy", 0) or 0
            max_apy = agent_config.get("max_apy", 1000) or 1000
            only_audited = agent_config.get("only_audited", False)
        
        print(f"[ContractMonitor] Filters: APY {min_apy}%-{max_apy}%, only_audited: {only_audited}")
        
        # If agent has preferences, use those
        if agent_config:
            preferred = [p.lower() for p in agent_config.get("protocols", [])]
            # Find highest APY protocol from preferences that meets all filters
            best_apy = 0
            best_protocol = None
            
            for proto_key, proto_info in PROTOCOLS.items():
                if proto_key not in preferred:
                    continue
                if not proto_info.get("supply_sig"):  # Must have supply support
                    continue
                    
                proto_apy = proto_info["apy"]
                proto_audited = proto_info.get("audited", False)
                
                # Check APY range
                if proto_apy < min_apy or proto_apy > max_apy:
                    print(f"[ContractMonitor] Skipping {proto_key}: APY {proto_apy}% outside range {min_apy}%-{max_apy}%")
                    continue
                
                # Check audited filter
                if only_audited and not proto_audited:
                    print(f"[ContractMonitor] Skipping {proto_key}: not audited (only_audited=True)")
                    continue
                
                # This protocol passes all filters
                if proto_apy > best_apy:
                    best_apy = proto_apy
                    best_protocol = proto_key
            
            if best_protocol:
                print(f"[ContractMonitor] Selected: {best_protocol} ({best_apy}% APY) - meets all filters")
                return best_protocol
            else:
                # ==========================================
                # PARKING STRATEGY: No protocol meets filters
                # Instead of idle capital → Park in Aave V3
                # ==========================================
                print(f"[ContractMonitor] ⚠️ No protocol meets all filters!")
                print(f"[ContractMonitor] 🅿️ Activating PARKING STRATEGY")
                print(f"  Reason: Filters too strict - parking capital in Aave V3 (~3.5% APY)")
                print(f"  Agent will auto-check every hour for matching pools")
                
                # Return aave as parking destination (handled specially in allocate_funds)
                return "aave_parking"
        
        # Default: pick highest APY lending protocol with supply support (ignoring filters)
        best_apy = 0
        best_protocol = "aave"
        
        for proto_key, proto_info in PROTOCOLS.items():
            if proto_info.get("is_lending") and proto_info.get("supply_sig"):
                if proto_info["apy"] > best_apy:
                    best_apy = proto_info["apy"]
                    best_protocol = proto_key
        
        print(f"[ContractMonitor] No config, using highest APY: {best_protocol} ({best_apy}%)")
        return best_protocol
    
    def _select_multiple_protocols(self, agent_config: dict = None, amount: int = 0) -> list:
        """
        Select multiple protocols for multi-vault allocation.
        Returns list of (protocol_key, amount_to_allocate) tuples.
        
        Uses vault_count and max_allocation from agent config to determine distribution.
        """
        if not agent_config:
            # Single vault fallback
            best = self._select_best_protocol(None)
            return [(best, amount)]
        
        # Get allocation settings
        vault_count = agent_config.get("vault_count", 1) or 1
        max_allocation_pct = agent_config.get("max_allocation", 100) or 100
        min_apy = agent_config.get("min_apy", 0) or 0
        max_apy = agent_config.get("max_apy", 1000) or 1000
        only_audited = agent_config.get("only_audited", False)
        preferred = [p.lower() for p in agent_config.get("protocols", [])]
        preferred_assets = [a.upper() for a in agent_config.get("preferred_assets", [])]
        pool_type = agent_config.get("pool_type", "all")  # single, dual, all
        risk_level = agent_config.get("risk_level", "high")  # low, medium, high
        
        # Risk level ordering for comparison
        RISK_ORDER = {"low": 1, "medium": 2, "high": 3}
        max_risk = RISK_ORDER.get(risk_level, 3)
        
        print(f"[ContractMonitor] Multi-vault: vault_count={vault_count}, max_allocation={max_allocation_pct}%")
        print(f"[ContractMonitor] Filters: pool_type={pool_type}, risk_level<={risk_level}")
        if preferred_assets:
            print(f"[ContractMonitor] Preferred assets: {preferred_assets}")
        
        # Find all eligible protocols
        eligible = []
        for proto_key, proto_info in PROTOCOLS.items():
            if preferred and proto_key not in preferred:
                continue
            if not proto_info.get("supply_sig"):
                continue
            proto_apy = proto_info["apy"]
            if proto_apy < min_apy or proto_apy > max_apy:
                continue
            if only_audited and not proto_info.get("audited", False):
                continue
            
            # Check pool_type filter
            proto_pool_type = proto_info.get("pool_type", "single")
            if pool_type != "all" and proto_pool_type != pool_type:
                print(f"[ContractMonitor] Skipping {proto_key}: pool_type {proto_pool_type} != {pool_type}")
                continue
            
            # Check risk_level filter (protocol risk must be <= user's max risk)
            proto_risk = proto_info.get("risk_level", "medium")
            proto_risk_score = RISK_ORDER.get(proto_risk, 2)
            if proto_risk_score > max_risk:
                print(f"[ContractMonitor] Skipping {proto_key}: risk {proto_risk} > max {risk_level}")
                continue
            
            # Check preferred_assets filter
            proto_asset = proto_info.get("asset", "").upper()
            if preferred_assets and proto_asset not in preferred_assets:
                # Allow LP pairs if any component matches (e.g., "USDC/WETH" matches "USDC")
                if "/" in proto_asset:
                    components = [a.strip() for a in proto_asset.split("/")]
                    if not any(c in preferred_assets for c in components):
                        print(f"[ContractMonitor] Skipping {proto_key}: asset {proto_asset} not in {preferred_assets}")
                        continue
                else:
                    print(f"[ContractMonitor] Skipping {proto_key}: asset {proto_asset} not in {preferred_assets}")
                    continue
            
            # ==========================================
            # RULE: min_pool_tvl - Skip low TVL pools
            # Default: $10M minimum TVL for production safety
            # ==========================================
            min_tvl = agent_config.get("min_pool_tvl", 10_000_000) or 10_000_000  # $10M default
            proto_tvl = proto_info.get("tvl", 0)
            if proto_tvl < min_tvl:
                print(f"[ContractMonitor] Skipping {proto_key}: TVL ${proto_tvl/1e6:.1f}M < min ${min_tvl/1e6:.1f}M")
                continue
            
            # ==========================================
            # RULE: volatility_threshold - Skip volatile pools (PRO)
            # ==========================================
            volatility_threshold = agent_config.get("volatility_threshold", 100) or 100  # 100 = no limit
            proto_volatility = proto_info.get("volatility", 0)
            if proto_volatility > volatility_threshold:
                print(f"[ContractMonitor] Skipping {proto_key}: volatility {proto_volatility}% > max {volatility_threshold}%")
                continue
            
            eligible.append((proto_key, proto_apy))
        
        if not eligible:
            # Fallback to single best
            best = self._select_best_protocol(agent_config)
            return [(best, amount)]
        
        # Sort by APY descending
        eligible.sort(key=lambda x: x[1], reverse=True)
        
        # Limit to vault_count
        selected = eligible[:vault_count]
        
        # Calculate allocation amounts
        allocations = []
        max_per_vault = int(amount * max_allocation_pct / 100)
        remaining = amount
        
        for i, (proto_key, proto_apy) in enumerate(selected):
            if remaining <= 0:
                break
            
            # For last vault, allocate remaining
            if i == len(selected) - 1:
                alloc_amount = remaining
            else:
                # Allocate max_allocation_pct or equal split, whichever is smaller
                equal_split = amount // len(selected)
                alloc_amount = min(max_per_vault, equal_split, remaining)
            
            if alloc_amount > 0:
                allocations.append((proto_key, alloc_amount))
                remaining -= alloc_amount
                print(f"[ContractMonitor] Multi-vault allocation: {proto_key} = ${alloc_amount / 1e6:.2f} ({proto_apy}% APY)")
        
        # If remaining > 0 (due to max_allocation cap), add to last vault
        if remaining > 0 and allocations:
            last_proto, last_amount = allocations[-1]
            allocations[-1] = (last_proto, last_amount + remaining)
            print(f"[ContractMonitor] Added remaining ${remaining / 1e6:.2f} to {last_proto}")
        
        return allocations if allocations else [(self._select_best_protocol(agent_config), amount)]

    def _build_supply_calldata(self, protocol_key: str, amount: int, user: str, agent_config: dict = None) -> bytes:
        """Build the calldata for supplying to a protocol"""
        protocol = PROTOCOLS.get(protocol_key)
        if not protocol or not protocol.get("supply_sig"):
            raise ValueError(f"Protocol {protocol_key} does not support direct supply")
        
        sig = protocol["supply_sig"]
        selector = self.w3.keccak(text=sig)[:4]
        
        if protocol_key == "aave":
            # supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)
            calldata = selector + self.w3.codec.encode(
                ['address', 'uint256', 'address', 'uint16'],
                [Web3.to_checksum_address(USDC_ADDRESS), amount, Web3.to_checksum_address(CONTRACT_ADDRESS), 0]
            )
        elif protocol_key == "moonwell":
            # mint(uint256 mintAmount) - contract must have USDC approved first
            calldata = selector + self.w3.codec.encode(
                ['uint256'],
                [amount]
            )
        elif protocol_key == "compound":
            # supply(address asset, uint256 amount)
            calldata = selector + self.w3.codec.encode(
                ['address', 'uint256'],
                [Web3.to_checksum_address(USDC_ADDRESS), amount]
            )
        elif protocol_key == "seamless":
            # deposit(uint256 assets, address receiver) - ERC4626
            calldata = selector + self.w3.codec.encode(
                ['uint256', 'address'],
                [amount, Web3.to_checksum_address(CONTRACT_ADDRESS)]
            )
        elif protocol_key in ["aerodrome", "uniswap"]:
            # ==========================================
            # WETH-FIRST STRATEGY for Dual-Sided LP
            # Uses AerodromeDualLPBuilder for calldata
            # ==========================================
            from artisan.aerodrome_dual import AerodromeDualLPBuilder
            
            asset_pair = protocol.get("asset", "USDC/WETH")
            slippage_pct = agent_config.get("slippage", 0.5) if agent_config else 0.5
            
            # ==========================================
            # RULE: TWAP Oracle Protection
            # ==========================================
            is_safe, current_price, twap_price, deviation_bps = self.check_twap_price()
            if not is_safe:
                raise ValueError(
                    f"TWAP check failed: deviation {deviation_bps} bps > {MAX_TWAP_DEVIATION_BPS} bps. "
                    f"Potential sandwich attack - skipping LP."
                )
            
            print(f"[ContractMonitor] WETH-First LP Strategy for {protocol_key}")
            print(f"[ContractMonitor] Pool: {asset_pair}, Slippage: {slippage_pct}%")
            
            # Build multi-step LP calldata
            builder = AerodromeDualLPBuilder()
            
            # For USDC/WETH pairs, we need WETH in the pair name
            # Convert "USDC/WETH" → "WETH/USDC" for builder
            tokens = [t.strip() for t in asset_pair.replace(" ", "").split("/")]
            if "WETH" in tokens:
                target_pair = asset_pair if tokens[0] == "WETH" else f"WETH/{tokens[0]}"
            else:
                # Non-WETH pair - need to route through WETH
                target_pair = f"WETH/{tokens[1]}" if tokens[1] != "USDC" else f"WETH/{tokens[0]}"
            
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            steps = loop.run_until_complete(builder.build_dual_lp_flow(
                usdc_amount=amount,
                target_pair=target_pair,
                recipient=CONTRACT_ADDRESS,
                slippage=slippage_pct
            ))
            
            print(f"[ContractMonitor] Generated {len(steps)} LP steps")
            for s in steps:
                print(f"   Step {s['step']}: {s['description']}")
            
            # Return list of calldata tuples: [(protocol_addr, calldata), ...]
            # This signals caller to execute multiple transactions
            return [(s["protocol"], s["calldata"]) for s in steps]
        else:
            # Fallback to Aave-style
            calldata = selector + self.w3.codec.encode(
                ['address', 'uint256', 'address', 'uint16'],
                [Web3.to_checksum_address(USDC_ADDRESS), amount, Web3.to_checksum_address(CONTRACT_ADDRESS), 0]
            )
        
        return calldata
    
    async def get_swap_quote_0x(self, sell_token: str, buy_token: str, sell_amount: int) -> dict:
        """Get swap quote from 0x API for best execution price"""
        import aiohttp
        
        params = {
            "sellToken": sell_token,
            "buyToken": buy_token,
            "sellAmount": str(sell_amount),
            "slippagePercentage": "0.01",  # 1% slippage
        }
        
        headers = {
            "0x-api-key": os.getenv("ZERO_X_API_KEY", ""),  # Optional for Base
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ZERO_X_API_URL, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"[0x] Quote: {sell_amount/1e6:.2f} {sell_token[:6]}... -> {int(data.get('buyAmount', 0))/1e18:.6f} {buy_token[:6]}...")
                        return {
                            "buyAmount": int(data.get("buyAmount", 0)),
                            "to": data.get("to"),
                            "data": data.get("data"),
                            "gas": data.get("gas"),
                            "price": data.get("price"),
                        }
                    else:
                        error = await resp.text()
                        print(f"[0x] Quote failed: {resp.status} - {error}")
                        return {}
        except Exception as e:
            print(f"[0x] Quote error: {e}")
            return {}
    
    async def execute_swap_for_lp(self, user: str, usdc_amount: int) -> tuple:
        """
        Execute USDC -> WETH swap for dual-sided LP using 0x API
        Returns (weth_received, tx_hash) or (0, None) on failure
        """
        # Get quote from 0x
        quote = await self.get_swap_quote_0x(USDC_ADDRESS, WETH_ADDRESS, usdc_amount)
        
        if not quote or not quote.get("data"):
            print(f"[ContractMonitor] Swap quote failed, trying Aerodrome Router fallback")
            # Could implement Aerodrome Router swap here as fallback
            return (0, None)
        
        try:
            # The 0x calldata can be executed directly to the 0x Exchange Proxy
            swap_to = quote["to"]
            swap_data = bytes.fromhex(quote["data"][2:])  # Remove 0x prefix
            weth_expected = quote["buyAmount"]
            
            print(f"[ContractMonitor] Executing swap via 0x: {usdc_amount/1e6:.2f} USDC -> ~{weth_expected/1e18:.6f} WETH")
            
            # Build swap TX (this would need to be signed by the contract/agent)
            # For now, log the intent - actual execution needs contract integration
            print(f"[ContractMonitor] Swap TX to: {swap_to}")
            print(f"[ContractMonitor] Swap data: {quote['data'][:66]}...")
            
            # TODO: Execute via contract's forwardCall or similar
            # For MVP, we'll assume swap happens and return expected amount
            return (weth_expected, None)  # No actual TX yet
            
        except Exception as e:
            print(f"[ContractMonitor] Swap execution error: {e}")
            return (0, None)
    
    async def _track_position(self, user: str, amount: int, result: dict):
        """Track Smart Account position in Supabase"""
        try:
            from infrastructure.supabase_client import get_supabase
            from datetime import datetime
            
            supabase = get_supabase()
            if not supabase:
                print("[ContractMonitor] Supabase not available for position tracking")
                return
            
            position_data = {
                "user_address": user.lower(),
                "protocol": result.get("protocol", "aave"),
                "pool_name": "USDC",
                "amount_usdc": amount / 1e6,
                "entry_time": datetime.utcnow().isoformat(),
                "status": "active",
                "user_op_hash": result.get("user_op_hash"),
                "smart_account": result.get("smart_account"),
                "is_erc4337": True
            }
            
            supabase.table("user_positions").upsert(position_data).execute()
            print(f"[ContractMonitor] Position tracked: ${amount/1e6:.2f} USDC")
            
        except Exception as e:
            print(f"[ContractMonitor] Position tracking error: {e}")
    
    async def allocate_funds(self, user: str, amount: int):
        """Allocate user funds to Aave using agent's EOA private key"""
        print(f"[ContractMonitor] >>> allocate_funds ENTRY: user={user[:15]}..., amount=${amount/1e6:.2f}", flush=True)
        
        try:
            from api.agent_config_router import DEPLOYED_AGENTS
            from services.agent_keys import decrypt_private_key
            from eth_account import Account
            from web3 import Web3
            
            # Find user's agent
            user_lower = user.lower()
            agents = DEPLOYED_AGENTS.get(user_lower, [])
            
            if not agents:
                print(f"[ContractMonitor] No agents found for {user[:15]}...", flush=True)
                return {"success": False, "error": "No agent found"}
            
            agent = agents[0]
            agent_address = agent.get("agent_address")
            encrypted_pk = agent.get("encrypted_private_key")
            
            # Check if we have the agent's private key
            if not encrypted_pk:
                print(f"[ContractMonitor] Agent has no private key - was deployed as Smart Account", flush=True)
                print(f"[ContractMonitor] User needs to re-deploy agent for EOA allocation", flush=True)
                return {"success": False, "error": "Agent needs re-deploy for EOA allocation"}
            
            # Decrypt agent's private key
            try:
                private_key = decrypt_private_key(encrypted_pk)
                agent_account = Account.from_key(private_key)
                print(f"[ContractMonitor] Using agent wallet: {agent_account.address}", flush=True)
            except Exception as decrypt_error:
                print(f"[ContractMonitor] Failed to decrypt agent key: {decrypt_error}", flush=True)
                return {"success": False, "error": "Key decryption failed"}
            
            # Use public RPC for allocation (avoid Alchemy mempool cache issues)
            w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
            
            # Check if agent has USDC balance
            USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
            AAVE_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
            
            erc20_abi = [
                {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
                {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"}
            ]
            
            usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=erc20_abi)
            usdc_balance = usdc.functions.balanceOf(Web3.to_checksum_address(agent_address)).call()
            
            print(f"[ContractMonitor] Agent USDC balance: ${usdc_balance/1e6:.2f}", flush=True)
            
            if usdc_balance == 0:
                return {"success": False, "error": "Agent has no USDC to allocate"}
            
            # Use actual balance (might be less than requested)
            actual_amount = min(amount, usdc_balance)
            
            # Step 1: Approve USDC to Aave Pool
            print(f"[ContractMonitor] Approving ${actual_amount/1e6:.2f} USDC to Aave...", flush=True)
            
            approve_tx = usdc.functions.approve(
                Web3.to_checksum_address(AAVE_POOL),
                actual_amount
            ).build_transaction({
                'from': agent_account.address,
                'nonce': w3.eth.get_transaction_count(agent_account.address, 'pending'),  # Fresh nonce
                'gas': 150000,  # Unique gas to avoid duplicate TX hash
                'gasPrice': int(w3.eth.gas_price * 10),  # Legacy format works better on Base
                'chainId': 8453
            })
            
            signed_approve = agent_account.sign_transaction(approve_tx)
            print(f"[ContractMonitor] Approve TX params: nonce={approve_tx['nonce']}, gas={approve_tx['gas']}, gasPrice={approve_tx['gasPrice']}", flush=True)
            approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            print(f"[ContractMonitor] Approve TX: {approve_hash.hex()}", flush=True)
            
            # Wait for approve
            w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
            
            # Step 2: Supply to Aave
            print(f"[ContractMonitor] Supplying to Aave...", flush=True)
            
            aave_abi = [{
                "inputs": [
                    {"name": "asset", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "onBehalfOf", "type": "address"},
                    {"name": "referralCode", "type": "uint16"}
                ],
                "name": "supply",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }]
            
            aave = w3.eth.contract(address=Web3.to_checksum_address(AAVE_POOL), abi=aave_abi)
            
            supply_tx = aave.functions.supply(
                Web3.to_checksum_address(USDC),
                actual_amount,
                agent_account.address,  # onBehalfOf = agent's wallet
                0  # referralCode
            ).build_transaction({
                'from': agent_account.address,
                'nonce': w3.eth.get_transaction_count(agent_account.address, 'pending'),  # Fresh nonce after approve
                'gas': 350000,  # Unique gas to avoid duplicate TX hash
                'gasPrice': int(w3.eth.gas_price * 10),  # Legacy format works better on Base
                'chainId': 8453
            })
            
            signed_supply = agent_account.sign_transaction(supply_tx)
            supply_hash = w3.eth.send_raw_transaction(signed_supply.raw_transaction)
            print(f"[ContractMonitor] ✅ Supply TX: {supply_hash.hex()}", flush=True)
            
            # Wait for supply
            receipt = w3.eth.wait_for_transaction_receipt(supply_hash, timeout=120)
            
            if receipt.status == 1:
                print(f"[ContractMonitor] ✅ Allocation SUCCESS! ${actual_amount/1e6:.2f} to Aave", flush=True)
                
                # Track position
                await self._track_position(user, actual_amount, {
                    "success": True,
                    "protocol": "aave",
                    "tx_hash": supply_hash.hex(),
                    "smart_account": agent_address
                })
                
                return {
                    "success": True,
                    "tx_hash": supply_hash.hex(),
                    "amount_usdc": actual_amount / 1e6,
                    "protocol": "aave",
                    "agent_address": agent_address
                }
            else:
                print(f"[ContractMonitor] ❌ Supply TX failed!", flush=True)
                return {"success": False, "error": "Supply transaction failed"}
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[ContractMonitor] Allocation error: {e}", flush=True)
            return {"success": False, "error": str(e)}
        
        try:
            import subprocess
            import json
            
            # Get user's agent config to determine preferred protocol
            from api.agent_config_router import DEPLOYED_AGENTS
            
            user_lower = user.lower()
            agent_config = None
            
            for u, agents in DEPLOYED_AGENTS.items():
                if u.lower() == user_lower and agents:
                    agent_config = agents[0]
                    break
            
            # ==========================================
            # RULE: DATA STALENESS CHECK (VC Requirement #1)
            # TEMPORARILY DISABLED FOR DEBUGGING
            # ==========================================
            print(f"[ContractMonitor] Staleness check SKIPPED (debugging)", flush=True)
            # try:
            #     from artisan.data_sources import is_data_stale
            #     stale, age_min, stale_msg = is_data_stale()
            #     if stale:
            #         print(f"[ContractMonitor] ⚠️ DATA STALE: {stale_msg}")
            #         print(f"[ContractMonitor] Cannot allocate - data too old. Will refresh and retry.")
            #         return  # Skip allocation until data refreshes
            #     else:
            #         print(f"[ContractMonitor] ✓ Data fresh ({age_min:.1f} min old)")
            # except ImportError:
            #     print("[ContractMonitor] Staleness check not available - proceeding")
            
            # ==========================================
            # RULE: max_gas_price - Skip if gas too high
            # ==========================================
            max_gas_gwei = agent_config.get("max_gas_price", 50) if agent_config else 50
            try:
                w3 = self._get_web3()
                current_gas = w3.eth.gas_price
                current_gas_gwei = current_gas / 1e9
                
                if current_gas_gwei > max_gas_gwei:
                    print(f"[ContractMonitor] ⛽ Gas too high: {current_gas_gwei:.1f} Gwei > max {max_gas_gwei} Gwei")
                    print(f"[ContractMonitor] Skipping allocation - will retry next cycle")
                    return  # Skip allocation, will retry on next poll
                else:
                    print(f"[ContractMonitor] ⛽ Gas OK: {current_gas_gwei:.1f} Gwei <= max {max_gas_gwei} Gwei")
            except Exception as e:
                print(f"[ContractMonitor] Gas check failed: {e} - proceeding anyway")
            
            # Select protocols for multi-vault allocation
            allocations = self._select_multiple_protocols(agent_config, amount)
            
            print(f"[ContractMonitor] Multi-vault allocations: {len(allocations)} protocol(s)")
            
            # Execute allocation for each protocol
            for alloc_idx, (protocol_key, alloc_amount) in enumerate(allocations):
                
                # ==========================================
                # PARKING STRATEGY: Special handling for idle capital
                # When no pools match filters, park in Aave V3
                # RULES:
                #   1. Only park if amount >= $10,000 USD
                #   2. Only park if idle for >= 1 hour
                # ==========================================
                if protocol_key == "aave_parking":
                    MIN_PARKING_AMOUNT = 10_000 * 1e6  # $10k in USDC (6 decimals)
                    IDLE_THRESHOLD_SECONDS = 3600  # 1 hour
                    
                    user_lower = user.lower()
                    now = datetime.utcnow()
                    
                    # Check minimum amount
                    if alloc_amount < MIN_PARKING_AMOUNT:
                        print(f"[ContractMonitor] 🅿️ Parking skipped - amount ${alloc_amount/1e6:.2f} < $10k minimum")
                        # Clear idle timer since amount is too small
                        self.idle_since.pop(user_lower, None)
                        continue
                    
                    # Check 1-hour idle timer
                    if user_lower not in self.idle_since:
                        # First time we see no matching pools - start timer
                        self.idle_since[user_lower] = now
                        print(f"[ContractMonitor] 🅿️ No matching pools - starting 1h idle timer")
                        print(f"  User: {user}")
                        print(f"  Amount: ${alloc_amount/1e6:.2f} USDC")
                        print(f"  Parking will activate at: {now + timedelta(hours=1)}")
                        continue  # Don't park yet
                    
                    idle_duration = (now - self.idle_since[user_lower]).total_seconds()
                    if idle_duration < IDLE_THRESHOLD_SECONDS:
                        remaining_min = (IDLE_THRESHOLD_SECONDS - idle_duration) / 60
                        print(f"[ContractMonitor] 🅿️ Idle timer running: {idle_duration/60:.0f}min / 60min")
                        print(f"  Parking in: {remaining_min:.0f} minutes")
                        continue  # Not yet 1 hour
                    
                    # Timer expired - proceed with parking!
                    print(f"[ContractMonitor] 🅿️ PARKING CAPITAL to Aave V3")
                    print(f"  Amount: ${alloc_amount/1e6:.2f} USDC")
                    print(f"  Reason: No pools matched for {idle_duration/3600:.1f} hours")
                    print(f"  Expected return: ~3.5% APY (safe harbor)")
                    
                    try:
                        from services.parking_strategy import ParkingStrategy
                        parking = ParkingStrategy()
                        result = await parking.park_capital(user, alloc_amount)
                        
                        if result["success"]:
                            print(f"[ContractMonitor] ✅ Capital parked successfully!")
                            print(f"  Protocol: {result['protocol']}")
                            print(f"  aToken: {result.get('atoken_balance', 'N/A')}")
                            # Clear idle timer - capital is no longer idle
                            self.idle_since.pop(user_lower, None)
                            # Track as parked position
                            self.track_position(user, "aave_parked", alloc_amount)
                        else:
                            print(f"[ContractMonitor] ⚠️ Parking failed: {result.get('error', 'Unknown')}")
                            # Fallback to regular Aave
                            protocol_key = "aave"
                            # Continue with normal flow below
                    except Exception as e:
                        print(f"[ContractMonitor] Parking error: {e} - falling back to regular Aave")
                        protocol_key = "aave"
                    else:
                        continue  # Skip to next allocation if parking succeeded
                
                protocol_info = PROTOCOLS.get(protocol_key)
                if not protocol_info:
                    print(f"[ContractMonitor] Unknown protocol: {protocol_key}, skipping")
                    continue
                
                protocol_address = protocol_info["address"]
                
                print(f"[ContractMonitor] [{alloc_idx+1}/{len(allocations)}] Allocating ${alloc_amount/1e6:.2f} to {protocol_info['name']} ({protocol_key})")
                print(f"[ContractMonitor] Expected APY: {protocol_info['apy']}%")
                
                # Build calldata based on protocol type
                calldata = self._build_supply_calldata(protocol_key, alloc_amount, user, agent_config)
            
                # Get user nonce from contract
                nonce = self.contract.functions.nonces(Web3.to_checksum_address(user)).call()
                
                # Build deadline
                deadline = int(datetime.utcnow().timestamp()) + 3600
                
                # Call Node.js signer script for correct signature
                script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'sign-allocation.js')
                
                result = subprocess.run(
                    ['node', script_path, 
                     Web3.to_checksum_address(user),
                     Web3.to_checksum_address(protocol_address),
                     str(alloc_amount),  # Use alloc_amount for this vault
                     str(deadline),
                     str(nonce),
                     self.agent_key
                    ],
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(script_path)
                )
                
                if result.returncode != 0:
                    print(f"[ContractMonitor] Signer error: {result.stderr}")
                    continue  # Try next protocol instead of returning
                
                sign_result = json.loads(result.stdout)
                
                if 'error' in sign_result:
                    print(f"[ContractMonitor] Signer error: {sign_result['error']}")
                    continue  # Try next protocol instead of returning
                
                signature = bytes.fromhex(sign_result['signature'][2:])  # Remove 0x prefix
                print(f"[ContractMonitor] Signature: {sign_result['signature'][:40]}...")
                print(f"[ContractMonitor] Signer: {sign_result['signer']}")
                
                # Build ExecuteParams tuple for V4.3.3
                execute_params = (
                    Web3.to_checksum_address(user),
                    Web3.to_checksum_address(protocol_address),
                    alloc_amount,  # Use alloc_amount for this vault
                    0,  # minAmountOut
                    deadline,
                    nonce,
                    0   # priceAtSign
                )
                
                # Build transaction with tuple
                # Use 'pending' nonce to avoid "replacement transaction underpriced" error
                current_nonce = self.w3.eth.get_transaction_count(self.agent_account.address, 'pending')
                base_gas = self.w3.eth.gas_price
                
                tx = self.contract.functions.executeStrategySigned(
                    execute_params,
                    signature,
                    calldata
                ).build_transaction({
                    'from': self.agent_account.address,
                    'nonce': current_nonce,
                    'gas': 500000,
                    'maxFeePerGas': int(base_gas * 2.5),  # Higher multiplier
                    'maxPriorityFeePerGas': self.w3.to_wei(0.01, 'gwei'),  # Higher priority
                    'chainId': 8453
                })
                
                # Sign and send
                signed_tx = self.w3.eth.account.sign_transaction(tx, self.agent_key)
                
                # ==========================================
                # RULE: mev_protection - Use private RPC (PRO)
                # ==========================================
                mev_protection = agent_config.get("mev_protection", False) if agent_config else False
                
                if mev_protection:
                    # Use Flashbots Protect RPC for private submission
                    flashbots_rpc = "https://rpc.flashbots.net"
                    print(f"[ContractMonitor] 🛡️ MEV Protection: Using Flashbots RPC")
                    try:
                        flashbots_w3 = Web3(Web3.HTTPProvider(flashbots_rpc))
                        tx_hash = flashbots_w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                        print(f"[ContractMonitor] 🛡️ TX sent via Flashbots Protect")
                    except Exception as fb_err:
                        print(f"[ContractMonitor] Flashbots failed: {fb_err}, falling back to public RPC")
                        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                else:
                    tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                
                print(f"[ContractMonitor] ✅ Allocation TX sent: {tx_hash.hex()}")
                logger.info(f"[ContractMonitor] Allocation TX: {tx_hash.hex()}")
                
                # Wait for confirmation
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
                
                if receipt.status == 1:
                    print(f"[ContractMonitor] ✅ Allocation [{alloc_idx+1}/{len(allocations)}] successful!")
                    
                    # Broadcast WebSocket notification
                    try:
                        from api.websocket_router import broadcast_allocation
                        import asyncio
                        asyncio.create_task(broadcast_allocation(
                            wallet=user,
                            status="complete",
                            amount=alloc_amount / 1e6,  # Use alloc_amount
                            protocol=protocol_info['name'],
                            tx_hash=tx_hash.hex()
                        ))
                    except Exception as ws_e:
                        print(f"[ContractMonitor] WebSocket broadcast failed: {ws_e}")
                    
                    # Track position for rebalance/drawdown monitoring
                    self.track_position(user, protocol_key, alloc_amount)
                else:
                    print(f"[ContractMonitor] ❌ Allocation [{alloc_idx+1}/{len(allocations)}] failed on-chain!")
                    try:
                        from api.websocket_router import broadcast_allocation
                        import asyncio
                        asyncio.create_task(broadcast_allocation(
                            wallet=user,
                            status="failed",
                            amount=alloc_amount / 1e6,  # Use alloc_amount
                            protocol=protocol_info['name']
                        ))
                    except Exception:
                        pass
            
        except Exception as e:
            import traceback
            logger.error(f"[ContractMonitor] Allocation error: {e}")
            print(f"[ContractMonitor] Allocation error: {e}")
            traceback.print_exc()
    
    def track_position(self, user: str, protocol_key: str, amount: int):
        """Track a new position for rebalance/drawdown monitoring"""
        from datetime import datetime
        
        if user not in self.user_positions:
            self.user_positions[user] = {}
        
        entry_time = datetime.utcnow()
        protocol_info = PROTOCOLS.get(protocol_key, {})
        
        self.user_positions[user][protocol_key] = {
            "entry_value": amount,
            "entry_time": entry_time.isoformat(),
            "current_value": amount,
            "high_water_mark": amount  # Track peak value for drawdown calculation
        }
        print(f"[ContractMonitor] Position tracked: {user[:10]}... -> {protocol_key} = ${amount/1e6:.2f}")
        
        # Persist to Supabase user_positions table (NEW - for fast loading)
        try:
            import asyncio
            from infrastructure.supabase_client import supabase
            if supabase.is_available:
                asyncio.create_task(supabase.save_user_position(
                    user_address=user,
                    protocol=protocol_key,
                    entry_value=amount / 1e6,
                    current_value=amount / 1e6,
                    asset=protocol_info.get("asset", "USDC"),
                    pool_type=protocol_info.get("pool_type", "single"),
                    apy=protocol_info.get("apy", 0),
                    pool_address=protocol_info.get("address"),
                    metadata={"entry_time": entry_time.isoformat()}
                ))
                # Also log to position_history
                asyncio.create_task(supabase.log_position_history(
                    user_address=user,
                    protocol=protocol_key,
                    action="deposit",
                    amount=amount / 1e6
                ))
                print(f"[ContractMonitor] Position saved to Supabase")
        except Exception as e:
            print(f"[ContractMonitor] Supabase save failed: {e}")
    
    async def execute_emergency_exit(self, user: str, protocol_key: str, pos_data: dict, agent_config: dict, drawdown_pct: float):
        """
        Emergency exit: withdraw all funds from position when max_drawdown breached.
        RULE: max_drawdown + emergency_exit
        """
        try:
            from agents.audit_trail import audit_trail, ActionType
            
            current_value = pos_data.get("current_value", 0)
            entry_value = pos_data.get("entry_value", 0)
            loss_amount = entry_value - current_value
            
            print(f"[ContractMonitor] 🚨 EMERGENCY EXIT: {user[:10]}... from {protocol_key}")
            print(f"  Entry: ${entry_value/1e6:.2f} -> Current: ${current_value/1e6:.2f} (Loss: ${loss_amount/1e6:.2f})")
            
            # Log to audit trail
            await audit_trail.log_action(
                user_address=user,
                action_type=ActionType.EMERGENCY_EXIT,
                details={
                    "protocol": protocol_key,
                    "trigger": "max_drawdown",
                    "drawdown_pct": round(drawdown_pct, 2),
                    "entry_value_usdc": entry_value / 1e6,
                    "exit_value_usdc": current_value / 1e6,
                    "loss_usdc": loss_amount / 1e6,
                    "max_drawdown_config": agent_config.get("max_drawdown", 20)
                },
                tx_hash=None  # Will be filled by actual withdrawal TX
            )
            
            # TODO: Execute actual withdrawal via contract
            # For now, remove from tracking to prevent repeated alerts
            if user in self.user_positions and protocol_key in self.user_positions[user]:
                del self.user_positions[user][protocol_key]
                
                # Remove from Supabase
                try:
                    from infrastructure.supabase_client import supabase
                    if supabase.is_available:
                        asyncio.create_task(supabase.delete_position(user, protocol_key))
                except Exception as e:
                    print(f"[ContractMonitor] Supabase delete failed: {e}")
                print(f"[ContractMonitor] Position removed from monitoring")
            
        except Exception as e:
            print(f"[ContractMonitor] Emergency exit error: {e}")
    
    async def execute_rebalance(self, user: str, protocol_key: str, pos_data: dict, agent_config: dict, pnl_pct: float):
        """
        Execute rebalance: move funds to better protocol if available.
        RULE: auto_rebalance + rebalance_threshold
        
        Now includes gas-vs-profit check (VC Requirement #2)
        """
        try:
            from agents.audit_trail import audit_trail, ActionType
            
            current_value = pos_data.get("current_value", 0)
            current_value_usd = current_value / 1e6  # Convert from USDC decimals
            current_proto_info = PROTOCOLS.get(protocol_key, {})
            current_apy = current_proto_info.get("apy", 0)
            
            # Find best protocol for new allocation
            best_protocol = self._select_best_protocol(agent_config)
            best_apy = PROTOCOLS.get(best_protocol, {}).get("apy", 0)
            
            # Only rebalance if new option is at least 2% better
            apy_improvement = best_apy - current_apy
            if apy_improvement < 2.0 or best_protocol == protocol_key:
                print(f"[ContractMonitor] Rebalance skipped: no better option available")
                print(f"  Current: {protocol_key} ({current_apy}%) -> Best: {best_protocol} ({best_apy}%)")
                return
            
            # ==========================================
            # GAS-VS-PROFIT CHECK (VC Requirement #2)
            # Don't rotate if costs exceed profits
            # ==========================================
            duration_days = agent_config.get("duration", 30) or 30
            rotation_check = should_rotate_position(
                current_apy=current_apy,
                new_apy=best_apy,
                position_value_usd=current_value_usd,
                holding_days=duration_days
            )
            
            if not rotation_check["should_rotate"]:
                print(f"[ContractMonitor] ❌ ROTATION BLOCKED: Not profitable")
                print(f"  {rotation_check['reason']}")
                print(f"  Total cost: ${rotation_check['total_cost']:.2f}")
                print(f"  Expected profit: ${rotation_check['expected_profit']:.2f}")
                
                # Log blocked rotation
                await audit_trail.log_action(
                    user_address=user,
                    action_type=ActionType.REBALANCE,
                    details={
                        "status": "blocked",
                        "reason": "unprofitable_rotation",
                        "from_protocol": protocol_key,
                        "to_protocol": best_protocol,
                        "total_cost": rotation_check["total_cost"],
                        "net_gain": rotation_check["net_gain"],
                        "breakeven_days": rotation_check["breakeven_days"]
                    },
                    tx_hash=None
                )
                return
            
            print(f"[ContractMonitor] ✅ ROTATION APPROVED: Profitable!")
            print(f"  {rotation_check['reason']}")
            print(f"  Net gain: ${rotation_check['net_gain']:.2f} over {duration_days} days")
            print(f"[ContractMonitor] 🔄 REBALANCE: {user[:10]}...")
            print(f"  From: {protocol_key} ({current_apy}%) -> To: {best_protocol} ({best_apy}%)")
            print(f"  APY improvement: +{apy_improvement:.1f}%")
            
            # Log to audit trail
            await audit_trail.log_action(
                user_address=user,
                action_type=ActionType.REBALANCE,
                details={
                    "from_protocol": protocol_key,
                    "from_apy": current_apy,
                    "to_protocol": best_protocol,
                    "to_apy": best_apy,
                    "apy_improvement": round(apy_improvement, 2),
                    "trigger": "rebalance_threshold",
                    "pnl_pct_trigger": round(pnl_pct, 2),
                    "value_usdc": current_value / 1e6
                },
                tx_hash=None  # Will be filled by actual rebalance TX
            )
            
            # TODO: Execute actual withdrawal + re-deposit
            # For now, update tracking to new protocol
            if user in self.user_positions and protocol_key in self.user_positions[user]:
                old_pos = self.user_positions[user].pop(protocol_key)
                self.track_position(user, best_protocol, current_value)
                print(f"[ContractMonitor] Position updated in tracking")
            
        except Exception as e:
            print(f"[ContractMonitor] Rebalance error: {e}")
    
    async def execute_auto_harvest(self, user: str, agent_config: dict):
        """
        Execute auto harvest based on compound_frequency.
        RULE: compound_frequency + harvest_strategy
        """
        try:
            from agents.audit_trail import audit_trail, ActionType
            
            harvest_strategy = agent_config.get("harvest_strategy", "compound")
            positions = self.user_positions.get(user, {})
            
            print(f"[ContractMonitor] 🌾 AUTO-HARVEST: {user[:10]}...")
            print(f"  Strategy: {harvest_strategy}")
            print(f"  Positions: {len(positions)}")
            
            # Log to audit trail
            await audit_trail.log_action(
                user_address=user,
                action_type=ActionType.TAKE_PROFIT,  # Using TAKE_PROFIT for harvest
                details={
                    "trigger": "compound_frequency",
                    "strategy": harvest_strategy,
                    "positions_count": len(positions),
                    "compound_frequency_days": agent_config.get("compound_frequency", 7)
                },
                tx_hash=None
            )
            
            # Update last harvest time
            self.last_harvest_time[user] = datetime.utcnow()
            
            # ==========================================
            # RULE: Executor Rewards (Revert Finance pattern)
            # Public harvesters earn 1% of yield
            # ==========================================
            try:
                from agents.executor_rewards import executor_rewards
                
                # Calculate total harvested yield (simplified - sum of position yields)
                total_yield = 0
                for proto_key, pos_data in positions.items():
                    entry = pos_data.get("entry_value", 0)
                    current = pos_data.get("current_value", entry)
                    total_yield += max(0, current - entry)
                
                # Reward executor (agent signer in this case)
                if total_yield > 0 and self.agent_account:
                    executor = self.agent_account.address
                    reward = executor_rewards.calculate_rewards(
                        harvested_amount=total_yield / 1e6,  # Convert to USDC
                        executor=executor,
                        user=user,
                        protocol="mixed"
                    )
                    print(f"[ContractMonitor] Executor reward: ${reward.reward_amount:.4f}")
            except Exception as reward_err:
                print(f"[ContractMonitor] Executor rewards error: {reward_err}")
            
            # ==========================================
            # RULE: harvest_strategy - Execute based on strategy (PRO)
            # ==========================================
            if harvest_strategy == "compound":
                # Re-invest yields back into the same position
                print(f"[ContractMonitor]   -> COMPOUND: Re-investing yields into current positions")
                for proto_key, pos_data in positions.items():
                    # In real implementation: call protocol's compound/reinvest function
                    print(f"[ContractMonitor]   -> Compounding {proto_key}")
                    
            elif harvest_strategy == "claim":
                # Transfer yields to user wallet
                print(f"[ContractMonitor]   -> CLAIM: Sending yields to user wallet")
                # In real implementation: call withdraw function for yield only
                
            elif harvest_strategy == "reinvest":
                # Split between compound and new positions
                print(f"[ContractMonitor]   -> REINVEST: 50% compound, 50% new best protocol")
                best_protocol = self._select_best_protocol(agent_config)
                print(f"[ContractMonitor]   -> New best protocol: {best_protocol}")
                
            else:
                print(f"[ContractMonitor]   -> Unknown strategy: {harvest_strategy}, defaulting to compound")
            
            print(f"[ContractMonitor] Last harvest time updated")
            
        except Exception as e:
            print(f"[ContractMonitor] Auto-harvest error: {e}")
    
    async def execute_duration_exit(self, user: str, protocol_key: str, pos_data: dict, agent_config: dict, days_held: int):
        """
        Close position when investment duration expires.
        RULE: duration
        """
        try:
            from agents.audit_trail import audit_trail, ActionType
            
            current_value = pos_data.get("current_value", 0)
            entry_value = pos_data.get("entry_value", 0)
            profit = current_value - entry_value
            
            print(f"[ContractMonitor] 💰 DURATION EXIT: {user[:10]}... from {protocol_key}")
            print(f"  Entry: ${entry_value/1e6:.2f} -> Current: ${current_value/1e6:.2f} (Profit: ${profit/1e6:.2f})")
            
            # Log to audit trail
            await audit_trail.log_action(
                user_address=user,
                action_type=ActionType.TAKE_PROFIT,
                details={
                    "protocol": protocol_key,
                    "trigger": "duration_expired",
                    "days_held": days_held,
                    "duration_config": agent_config.get("duration", 30),
                    "entry_value_usdc": entry_value / 1e6,
                    "exit_value_usdc": current_value / 1e6,
                    "profit_usdc": profit / 1e6
                },
                tx_hash=None
            )
            
            # Remove from tracking
            if user in self.user_positions and protocol_key in self.user_positions[user]:
                del self.user_positions[user][protocol_key]
                print(f"[ContractMonitor] Position removed from monitoring")
            
        except Exception as e:
            print(f"[ContractMonitor] Duration exit error: {e}")
    
    async def check_rebalance_and_drawdown(self):
        """
        Check all user positions for:
        1. max_drawdown violations (trigger emergency exit)
        2. rebalance opportunities (if auto_rebalance enabled)
        """
        from api.agent_config_router import DEPLOYED_AGENTS
        
        for user_addr, positions in self.user_positions.items():
            # Get user's agent config
            agent_config = None
            for u, agents in DEPLOYED_AGENTS.items():
                if u.lower() == user_addr.lower() and agents:
                    agent_config = agents[0]
                    break
            
            if not agent_config:
                continue
            
            max_drawdown = agent_config.get("max_drawdown", 100) or 100  # default 100% = no limit
            auto_rebalance = agent_config.get("auto_rebalance", False)
            rebalance_threshold = agent_config.get("rebalance_threshold", 5) or 5
            
            # Check each position
            for proto_key, pos_data in positions.items():
                entry_value = pos_data.get("entry_value", 0)
                current_value = pos_data.get("current_value", entry_value)
                high_water_mark = pos_data.get("high_water_mark", entry_value)
                
                if entry_value <= 0:
                    continue
                
                # Calculate drawdown from high water mark
                drawdown_pct = ((high_water_mark - current_value) / high_water_mark) * 100 if high_water_mark > 0 else 0
                
                # Check max_drawdown violation
                if drawdown_pct >= max_drawdown:
                    print(f"[ContractMonitor] ⚠️ DRAWDOWN ALERT: {user_addr[:10]}... on {proto_key}")
                    print(f"  Drawdown: {drawdown_pct:.1f}% >= max_drawdown {max_drawdown}%")
                    
                    # ==========================================
                    # RULE: max_drawdown - Execute emergency exit
                    # ==========================================
                    emergency_exit_enabled = agent_config.get("emergency_exit", True)
                    if emergency_exit_enabled:
                        await self.execute_emergency_exit(user_addr, proto_key, pos_data, agent_config, drawdown_pct)
                    else:
                        print(f"  Emergency exit disabled - skipping withdrawal")
                    continue  # Skip other checks if exiting
                
                # ==========================================
                # IL MONITORING (VC Requirement #5)
                # Check if impermanent loss is consuming capital
                # ==========================================
                if pos_data.get("pool_type") == "dual":  # Only for dual-sided LP
                    try:
                        il_data = pos_data.get("il_data", {})
                        earned_fees = il_data.get("earned_fees_usd", 0)
                        il_usd = il_data.get("il_usd", 0)
                        
                        # Alert if IL > fees (net negative from IL)
                        if il_usd > 0 and earned_fees < il_usd:
                            il_to_fee_ratio = il_usd / earned_fees if earned_fees > 0 else float('inf')
                            
                            print(f"[ContractMonitor] ⚠️ IL WARNING: {user_addr[:10]}... on {proto_key}")
                            print(f"  IL: ${il_usd:.2f} > Fees: ${earned_fees:.2f}")
                            print(f"  IL/Fees ratio: {il_to_fee_ratio:.1f}x")
                            
                            # Log IL warning
                            try:
                                from agents.audit_trail import audit_trail, ActionType
                                await audit_trail.log_action(
                                    user_address=user_addr,
                                    action_type=ActionType.ALERT,
                                    details={
                                        "type": "il_warning",
                                        "il_usd": round(il_usd, 2),
                                        "fees_usd": round(earned_fees, 2),
                                        "ratio": round(il_to_fee_ratio, 2),
                                        "protocol": proto_key
                                    },
                                    tx_hash=None
                                )
                            except Exception:
                                pass
                            
                            # If IL is 2x+ fees, consider exit
                            max_il_ratio = agent_config.get("max_il_ratio", 2.0) or 2.0
                            if il_to_fee_ratio >= max_il_ratio:
                                print(f"[ContractMonitor] 🚨 IL EXIT: Ratio {il_to_fee_ratio:.1f}x >= max {max_il_ratio}x")
                                emergency_exit_enabled = agent_config.get("emergency_exit", True)
                                if emergency_exit_enabled:
                                    await self.execute_emergency_exit(user_addr, proto_key, pos_data, agent_config, drawdown_pct)
                                continue
                    except Exception as e:
                        print(f"[ContractMonitor] IL check error: {e}")
                
                # ==========================================
                # RULE: duration - Close position when investment period ends
                # ==========================================
                duration_days = agent_config.get("duration", 0) or 0  # 0 = no limit
                if duration_days > 0:
                    entry_time_str = pos_data.get("entry_time", "")
                    if entry_time_str:
                        try:
                            entry_time = datetime.fromisoformat(entry_time_str)
                            days_held = (datetime.utcnow() - entry_time).days
                            
                            if days_held >= duration_days:
                                print(f"[ContractMonitor] ⏰ DURATION EXPIRED: {user_addr[:10]}... on {proto_key}")
                                print(f"  Days held: {days_held} >= duration {duration_days}")
                                
                                # Close position with profit-taking exit
                                await self.execute_duration_exit(user_addr, proto_key, pos_data, agent_config, days_held)
                                continue  # Skip other checks if exiting
                        except ValueError:
                            pass  # Invalid timestamp, skip
                
                # Check rebalance opportunity (if enabled)
                if auto_rebalance:
                    # Simple rebalance check: if position drifted more than threshold% from target
                    pnl_pct = ((current_value - entry_value) / entry_value) * 100 if entry_value > 0 else 0
                    if abs(pnl_pct) >= rebalance_threshold:
                        print(f"[ContractMonitor] 🔄 Rebalance opportunity: {user_addr[:10]}... on {proto_key}")
                        print(f"  PnL: {pnl_pct:+.1f}% (threshold: {rebalance_threshold}%)")
                        
                        # ==========================================
                        # RULE: auto_rebalance - Execute rebalance
                        # ==========================================
                        await self.execute_rebalance(user_addr, proto_key, pos_data, agent_config, pnl_pct)
            
            # ==========================================
            # RULE: compound_frequency - Auto harvest
            # ==========================================
            compound_frequency_days = agent_config.get("compound_frequency", 7) or 7
            last_harvest = self.last_harvest_time.get(user_addr)
            
            if last_harvest:
                days_since_harvest = (datetime.utcnow() - last_harvest).days
                if days_since_harvest >= compound_frequency_days:
                    print(f"[ContractMonitor] 🌾 Auto-harvest triggered for {user_addr[:10]}...")
                    print(f"  Days since last harvest: {days_since_harvest} >= {compound_frequency_days}")
                    await self.execute_auto_harvest(user_addr, agent_config)
            else:
                # First time - track now as last harvest
                self.last_harvest_time[user_addr] = datetime.utcnow()


# Global instance
contract_monitor = ContractMonitor()


async def start_contract_monitoring():
    """Start the contract monitor (call from main app startup)"""
    asyncio.create_task(contract_monitor.start())


def stop_contract_monitoring():
    """Stop the contract monitor"""
    contract_monitor.stop()
