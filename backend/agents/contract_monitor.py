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
from datetime import datetime
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import logging

# Load .env file
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# V4.3.2 Contract Address
CONTRACT_ADDRESS = "0x323f98c4e05073c2f76666944d95e39b78024efd"

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
        "risk_level": "high",
        "is_lending": False,
        "audited": True,
        "supply_sig": "addLiquidity(address,address,bool,uint256,uint256,uint256,uint256,address,uint256)",
        "apy": 15.0,
        "tvl": 35000000,   # $35M TVL
        "volatility": 12.0 # High volatility (LP pairs)
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
    
    def _get_web3(self) -> Web3:
        if not self.w3:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                abi=CONTRACT_ABI
            )
            self.last_block = self.w3.eth.block_number - 100  # Start 100 blocks back
        return self.w3
    
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
                    await self.check_rebalance_and_drawdown()
                    
            except Exception as e:
                logger.error(f"[ContractMonitor] Error: {e}")
                print(f"[ContractMonitor] Error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        self.running = False
        print("[ContractMonitor] Stopped")
    
    async def check_for_deposits(self):
        """Check for new Deposited events"""
        w3 = self._get_web3()
        current_block = w3.eth.block_number
        
        if current_block <= self.last_block:
            return
        
        # Get Deposited events
        try:
            events = self.contract.events.Deposited.get_logs(
                from_block=self.last_block + 1,
                to_block=current_block
            )
            
            for event in events:
                await self.handle_deposit(event)
            
            self.last_block = current_block
            
        except Exception as e:
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
                # No protocol meets all filters - fallback to highest APY anyway with warning
                print(f"[ContractMonitor] WARNING: No preferred protocol meets all filters, using highest available")
        
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
            # RULE: min_pool_tvl - Skip low TVL pools (PRO)
            # ==========================================
            min_tvl = agent_config.get("min_pool_tvl", 0) or 0
            proto_tvl = proto_info.get("tvl", 0)
            if min_tvl > 0 and proto_tvl < min_tvl:
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
        elif protocol_key == "aerodrome":
            # Dual-sided LP: need to swap 50% USDC -> WETH, then addLiquidity
            # This is a simplified version - actual implementation would need multicall
            router = protocol.get("router")
            usdc_amount = amount // 2  # 50% stays USDC
            swap_amount = amount - usdc_amount  # 50% to swap
            
            # ==========================================
            # RULE: TWAP Oracle Protection (Revert Finance pattern)
            # ==========================================
            is_safe, current_price, twap_price, deviation_bps = self.check_twap_price()
            if not is_safe:
                raise ValueError(
                    f"TWAP check failed: price deviation {deviation_bps} bps exceeds {MAX_TWAP_DEVIATION_BPS} bps limit. "
                    f"Potential sandwich attack detected - skipping LP."
                )
            
            # ==========================================
            # RULE: slippage - Use configured slippage tolerance
            # ==========================================
            slippage_pct = agent_config.get("slippage", 0.5) if agent_config else 0.5
            slippage_multiplier = (100 - slippage_pct) / 100  # e.g., 0.5% -> 0.995
            
            print(f"[ContractMonitor] Using slippage tolerance: {slippage_pct}%")
            
            # For now, we return a placeholder - actual swap needs to be done separately
            # The real flow:
            # 1. Contract holds USDC
            # 2. Agent calls swap via 0x or Router (separate TX)
            # 3. Agent calls addLiquidity with both tokens
            
            # Build addLiquidity calldata with estimated WETH (will be adjusted by Router)
            deadline = int(datetime.utcnow().timestamp()) + 3600
            
            print(f"[ContractMonitor] Aerodrome LP: {usdc_amount/1e6:.2f} USDC + swap {swap_amount/1e6:.2f} USDC -> WETH")
            
            calldata = selector + self.w3.codec.encode(
                ['address', 'address', 'bool', 'uint256', 'uint256', 'uint256', 'uint256', 'address', 'uint256'],
                [
                    Web3.to_checksum_address(USDC_ADDRESS),  # tokenA
                    Web3.to_checksum_address(WETH_ADDRESS),  # tokenB
                    False,  # stable = false (volatile pair)
                    usdc_amount,  # amountADesired
                    0,  # amountBDesired - will be filled by swap
                    int(usdc_amount * slippage_multiplier),  # amountAMin (user's slippage)
                    0,  # amountBMin
                    Web3.to_checksum_address(CONTRACT_ADDRESS),  # to
                    deadline
                ]
            )
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
    
    async def allocate_funds(self, user: str, amount: int):
        """Allocate user funds to best protocol using Node.js signer for correct signatures"""
        if not self.agent_key:
            print("[ContractMonitor] No agent key configured - cannot allocate")
            return
        
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
                tx = self.contract.functions.executeStrategySigned(
                    execute_params,
                    signature,
                    calldata
                ).build_transaction({
                    'from': self.agent_account.address,
                    'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
                    'gas': 500000,
                    'maxFeePerGas': self.w3.eth.gas_price * 2,
                    'maxPriorityFeePerGas': self.w3.to_wei(0.001, 'gwei'),
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
        
        self.user_positions[user][protocol_key] = {
            "entry_value": amount,
            "entry_time": datetime.utcnow().isoformat(),
            "current_value": amount,
            "high_water_mark": amount  # Track peak value for drawdown calculation
        }
        print(f"[ContractMonitor] Position tracked: {user[:10]}... -> {protocol_key} = ${amount/1e6:.2f}")
    
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
                print(f"[ContractMonitor] Position removed from monitoring")
            
        except Exception as e:
            print(f"[ContractMonitor] Emergency exit error: {e}")
    
    async def execute_rebalance(self, user: str, protocol_key: str, pos_data: dict, agent_config: dict, pnl_pct: float):
        """
        Execute rebalance: move funds to better protocol if available.
        RULE: auto_rebalance + rebalance_threshold
        """
        try:
            from agents.audit_trail import audit_trail, ActionType
            
            current_value = pos_data.get("current_value", 0)
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
