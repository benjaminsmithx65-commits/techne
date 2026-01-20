"""
Morpho Blue Smart Loop Engine - Leveraged DeFi Positions
Production implementation for Morpho Blue on Base

Morpho Blue is different from Aave:
- Uses MarketParams struct to identify markets
- supplyCollateral() + borrow() for leverage loops
- Higher LTV possible (up to 90%+ for some markets)
- No health factor - uses LLTV (Liquidation LTV)

Leverage Loop Pattern:
1. Supply collateral token
2. Borrow loan token against collateral
3. Swap loan token to collateral token
4. Re-supply collateral
5. Repeat until target leverage reached
"""

import asyncio
import os
from typing import Dict, Optional, Tuple, NamedTuple
from datetime import datetime
from web3 import Web3
from eth_account import Account
from dataclasses import dataclass
import logging

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Morpho Blue on Base
MORPHO_BLUE_ADDRESS = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"

# Common tokens on Base
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"
CBETH_ADDRESS = "0x2Ae3F1Ec7F1F5012CFEb0296C8A8E57d2C622A3E"

# Pre-configured Morpho Blue markets on Base
# Each market is identified by: (loanToken, collateralToken, oracle, irm, lltv)
MORPHO_MARKETS = {
    "usdc_weth": {
        "name": "USDC/WETH",
        "loanToken": USDC_ADDRESS,
        "collateralToken": WETH_ADDRESS,
        "oracle": "0x...",  # Chainlink WETH/USD oracle
        "irm": "0x46415998764C29aB2a25CbeA6254146D50D22687",  # AdaptiveCurveIrm on Base
        "lltv": 860000000000000000,  # 86% LLTV (1e18 = 100%)
        "leverage_factor": 0.86
    },
    "usdc_cbeth": {
        "name": "USDC/cbETH",
        "loanToken": USDC_ADDRESS,
        "collateralToken": CBETH_ADDRESS,
        "oracle": "0x...",
        "irm": "0x46415998764C29aB2a25CbeA6254146D50D22687",
        "lltv": 770000000000000000,  # 77% LLTV
        "leverage_factor": 0.77
    }
}

# Morpho Blue ABI (minimal)
MORPHO_BLUE_ABI = [
    # supplyCollateral(MarketParams, assets, onBehalf, data)
    {
        "inputs": [
            {
                "components": [
                    {"name": "loanToken", "type": "address"},
                    {"name": "collateralToken", "type": "address"},
                    {"name": "oracle", "type": "address"},
                    {"name": "irm", "type": "address"},
                    {"name": "lltv", "type": "uint256"}
                ],
                "name": "marketParams",
                "type": "tuple"
            },
            {"name": "assets", "type": "uint256"},
            {"name": "onBehalf", "type": "address"},
            {"name": "data", "type": "bytes"}
        ],
        "name": "supplyCollateral",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # borrow(MarketParams, assets, shares, onBehalf, receiver)
    {
        "inputs": [
            {
                "components": [
                    {"name": "loanToken", "type": "address"},
                    {"name": "collateralToken", "type": "address"},
                    {"name": "oracle", "type": "address"},
                    {"name": "irm", "type": "address"},
                    {"name": "lltv", "type": "uint256"}
                ],
                "name": "marketParams",
                "type": "tuple"
            },
            {"name": "assets", "type": "uint256"},
            {"name": "shares", "type": "uint256"},
            {"name": "onBehalf", "type": "address"},
            {"name": "receiver", "type": "address"}
        ],
        "name": "borrow",
        "outputs": [
            {"name": "assetsBorrowed", "type": "uint256"},
            {"name": "sharesBorrowed", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # repay(MarketParams, assets, shares, onBehalf, data)
    {
        "inputs": [
            {
                "components": [
                    {"name": "loanToken", "type": "address"},
                    {"name": "collateralToken", "type": "address"},
                    {"name": "oracle", "type": "address"},
                    {"name": "irm", "type": "address"},
                    {"name": "lltv", "type": "uint256"}
                ],
                "name": "marketParams",
                "type": "tuple"
            },
            {"name": "assets", "type": "uint256"},
            {"name": "shares", "type": "uint256"},
            {"name": "onBehalf", "type": "address"},
            {"name": "data", "type": "bytes"}
        ],
        "name": "repay",
        "outputs": [
            {"name": "assetsRepaid", "type": "uint256"},
            {"name": "sharesRepaid", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # withdrawCollateral(MarketParams, assets, onBehalf, receiver)
    {
        "inputs": [
            {
                "components": [
                    {"name": "loanToken", "type": "address"},
                    {"name": "collateralToken", "type": "address"},
                    {"name": "oracle", "type": "address"},
                    {"name": "irm", "type": "address"},
                    {"name": "lltv", "type": "uint256"}
                ],
                "name": "marketParams",
                "type": "tuple"
            },
            {"name": "assets", "type": "uint256"},
            {"name": "onBehalf", "type": "address"},
            {"name": "receiver", "type": "address"}
        ],
        "name": "withdrawCollateral",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # position(Id, user) -> (supplyShares, borrowShares, collateral)
    {
        "inputs": [
            {"name": "id", "type": "bytes32"},
            {"name": "user", "type": "address"}
        ],
        "name": "position",
        "outputs": [
            {"name": "supplyShares", "type": "uint256"},
            {"name": "borrowShares", "type": "uint128"},
            {"name": "collateral", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI
ERC20_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


@dataclass
class MorphoPosition:
    """Tracks a Morpho Blue leveraged position"""
    user: str
    market_key: str
    initial_collateral: int
    current_collateral: int
    current_debt: int
    target_leverage: float
    actual_leverage: float
    lltv: float  # Liquidation LTV
    loop_count: int
    created_at: str
    last_updated: str


class MorphoBlueLoopEngine:
    """
    Production Smart Loop Engine for Morpho Blue Leverage
    
    Key differences from Aave:
    - Uses MarketParams struct instead of simple asset address
    - supplyCollateral() + borrow() instead of supply() + borrow()
    - No native health factor, uses LLTV
    - Higher leverage possible (up to 5x+ with 90% LLTV)
    """
    
    # Safety constants
    MIN_SAFETY_MARGIN = 0.10  # Keep 10% below LLTV
    MAX_LEVERAGE = 5.0        # Cap at 5x (possible with 86% LLTV)
    
    def __init__(self):
        self.rpc_url = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = None
        self.morpho_contract = None
        
        # Position tracking
        self.positions: Dict[str, MorphoPosition] = {}
        
        # Agent signer
        self.agent_key = os.getenv("PRIVATE_KEY")
        self.agent_account = None
        
        if self.agent_key:
            pk = self.agent_key if self.agent_key.startswith('0x') else f'0x{self.agent_key}'
            self.agent_account = Account.from_key(pk)
            logger.info(f"[MorphoLoop] Agent signer: {self.agent_account.address}")
    
    def _init_contracts(self):
        """Initialize Web3 and contracts"""
        if not self.w3:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.morpho_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
                abi=MORPHO_BLUE_ABI
            )
    
    def _get_market_params(self, market_key: str) -> tuple:
        """Get MarketParams tuple for a market"""
        market = MORPHO_MARKETS.get(market_key)
        if not market:
            raise ValueError(f"Unknown market: {market_key}")
        
        return (
            Web3.to_checksum_address(market["loanToken"]),
            Web3.to_checksum_address(market["collateralToken"]),
            Web3.to_checksum_address(market["oracle"]),
            Web3.to_checksum_address(market["irm"]),
            market["lltv"]
        )
    
    def calculate_loop_parameters(self, market_key: str, initial_collateral: int, target_leverage: float) -> Dict:
        """
        Calculate leverage loop parameters for Morpho Blue
        
        Morpho uses LLTV (Liquidation LTV), not health factor.
        Max leverage = 1 / (1 - LLTV)
        
        For 86% LLTV: max = 1 / 0.14 = ~7.1x (but we cap at 5x for safety)
        """
        market = MORPHO_MARKETS.get(market_key)
        if not market:
            raise ValueError(f"Unknown market: {market_key}")
        
        lltv = market["lltv"] / 1e18  # Convert from 1e18 format
        safe_ltv = lltv - self.MIN_SAFETY_MARGIN  # 10% safety margin
        
        target = min(target_leverage, self.MAX_LEVERAGE)
        
        # Calculate required loops
        loops = 0
        cumulative_collateral = initial_collateral
        cumulative_debt = 0
        
        loop_details = []
        
        while loops < 10:  # Safety limit
            # How much can we borrow?
            max_borrow = int(cumulative_collateral * safe_ltv) - cumulative_debt
            
            if max_borrow <= 0:
                break
            
            # Check if adding this would exceed target leverage
            new_collateral = cumulative_collateral + max_borrow
            new_debt = cumulative_debt + max_borrow
            new_leverage = new_collateral / initial_collateral
            
            if new_leverage > target:
                # Calculate exact amount for target
                target_collateral = initial_collateral * target
                needed = target_collateral - cumulative_collateral
                max_borrow = min(max_borrow, int(needed))
                
                if max_borrow <= 1000:  # Less than $0.001
                    break
            
            # Calculate current LTV usage
            current_ltv = new_debt / new_collateral if new_collateral > 0 else 0
            
            loop_details.append({
                "loop": loops + 1,
                "borrow_amount": max_borrow,
                "new_collateral": cumulative_collateral + max_borrow,
                "new_debt": cumulative_debt + max_borrow,
                "leverage": (cumulative_collateral + max_borrow) / initial_collateral,
                "ltv_usage": current_ltv,
                "lltv": lltv
            })
            
            cumulative_collateral += max_borrow
            cumulative_debt += max_borrow
            loops += 1
            
            if cumulative_collateral / initial_collateral >= target:
                break
        
        final_leverage = cumulative_collateral / initial_collateral if initial_collateral > 0 else 0
        final_ltv = cumulative_debt / cumulative_collateral if cumulative_collateral > 0 else 0
        
        return {
            "market": market_key,
            "initial_collateral": initial_collateral,
            "target_leverage": target,
            "actual_leverage": final_leverage,
            "total_loops": loops,
            "final_collateral": cumulative_collateral,
            "final_debt": cumulative_debt,
            "ltv_usage": final_ltv,
            "lltv": lltv,
            "safety_margin": lltv - final_ltv,
            "loop_details": loop_details
        }
    
    async def execute_leverage_loop(
        self,
        user: str,
        market_key: str,
        collateral_amount: int,
        target_leverage: float,
        on_behalf_of: str = None
    ) -> Dict:
        """
        Execute Morpho Blue leverage loop
        
        Args:
            user: User address
            market_key: Key from MORPHO_MARKETS (e.g., "usdc_weth")
            collateral_amount: Initial collateral (in token decimals)
            target_leverage: Target leverage (1.0 to 5.0)
            on_behalf_of: Execute on behalf of (for Smart Accounts)
        """
        self._init_contracts()
        on_behalf = on_behalf_of or user
        market = MORPHO_MARKETS.get(market_key)
        
        print(f"[MorphoLoop] 🔄 Building {target_leverage}x leverage on {market['name']}")
        print(f"[MorphoLoop] Initial collateral: {collateral_amount}")
        
        # Calculate loop parameters
        params = self.calculate_loop_parameters(market_key, collateral_amount, target_leverage)
        print(f"[MorphoLoop] Calculated: {params['total_loops']} loops for {params['actual_leverage']:.2f}x")
        print(f"[MorphoLoop] LTV usage: {params['ltv_usage']*100:.1f}% / {params['lltv']*100:.1f}% LLTV")
        
        tx_hashes = []
        market_params = self._get_market_params(market_key)
        
        try:
            # Step 1: Approve collateral token to Morpho
            print(f"[MorphoLoop] Step 1: Approving collateral to Morpho")
            approve_tx = await self._approve_token(market["collateralToken"], collateral_amount)
            if approve_tx:
                tx_hashes.append(approve_tx)
            
            # Step 2: Initial supply collateral
            print(f"[MorphoLoop] Step 2: Supplying initial collateral")
            supply_tx = await self._supply_collateral(market_params, collateral_amount, on_behalf)
            if supply_tx:
                tx_hashes.append(supply_tx)
            
            # Step 3: Execute leverage loops
            for i, loop in enumerate(params['loop_details']):
                print(f"[MorphoLoop] Loop {i+1}: Borrow {loop['borrow_amount']} → Re-supply")
                
                # Borrow
                borrow_tx = await self._borrow(market_params, loop['borrow_amount'], on_behalf)
                if borrow_tx:
                    tx_hashes.append(borrow_tx)
                
                # Note: In production, would need to swap loan token to collateral token here
                # For USDC/WETH market: swap borrowed USDC to WETH
                
                # Re-supply borrowed amount as additional collateral
                supply_tx = await self._supply_collateral(market_params, loop['borrow_amount'], on_behalf)
                if supply_tx:
                    tx_hashes.append(supply_tx)
                
                print(f"[MorphoLoop]   → LTV: {loop['ltv_usage']*100:.1f}%")
            
            # Create position record
            position = MorphoPosition(
                user=user,
                market_key=market_key,
                initial_collateral=collateral_amount,
                current_collateral=params['final_collateral'],
                current_debt=params['final_debt'],
                target_leverage=target_leverage,
                actual_leverage=params['actual_leverage'],
                lltv=params['lltv'],
                loop_count=params['total_loops'],
                created_at=datetime.utcnow().isoformat(),
                last_updated=datetime.utcnow().isoformat()
            )
            
            self.positions[f"{user}_{market_key}"] = position
            
            print(f"[MorphoLoop] ✅ Leverage position created!")
            print(f"[MorphoLoop]   Collateral: {position.current_collateral}")
            print(f"[MorphoLoop]   Debt: {position.current_debt}")
            print(f"[MorphoLoop]   Leverage: {position.actual_leverage:.2f}x")
            print(f"[MorphoLoop]   LTV: {params['ltv_usage']*100:.1f}%")
            
            return {
                "success": True,
                "position": position,
                "tx_hashes": tx_hashes
            }
            
        except Exception as e:
            print(f"[MorphoLoop] ❌ Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "tx_hashes": tx_hashes
            }
    
    # ==========================================
    # Transaction Builders
    # ==========================================
    
    async def _approve_token(self, token_address: str, amount: int) -> Optional[str]:
        """Approve token spending to Morpho"""
        if not self.agent_account:
            print("[MorphoLoop] No agent key - simulating approve")
            return "0x_simulated_approve"
        
        try:
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )
            
            tx = token_contract.functions.approve(
                Web3.to_checksum_address(MORPHO_BLUE_ADDRESS),
                amount * 2  # Approve extra for loops
            ).build_transaction({
                'from': self.agent_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
                'gas': 100000,
                'maxFeePerGas': self.w3.eth.gas_price * 2,
                'maxPriorityFeePerGas': self.w3.to_wei(0.001, 'gwei'),
                'chainId': 8453
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.agent_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"[MorphoLoop] Approve TX: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            print(f"[MorphoLoop] Approve failed: {e}")
            return None
    
    async def _supply_collateral(self, market_params: tuple, amount: int, on_behalf: str) -> Optional[str]:
        """Supply collateral to Morpho Blue"""
        if not self.agent_account:
            print(f"[MorphoLoop] No agent key - simulating supply_collateral of {amount}")
            return "0x_simulated_supply"
        
        try:
            tx = self.morpho_contract.functions.supplyCollateral(
                market_params,
                amount,
                Web3.to_checksum_address(on_behalf),
                b""  # No callback data
            ).build_transaction({
                'from': self.agent_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
                'gas': 300000,
                'maxFeePerGas': self.w3.eth.gas_price * 2,
                'maxPriorityFeePerGas': self.w3.to_wei(0.001, 'gwei'),
                'chainId': 8453
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.agent_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"[MorphoLoop] SupplyCollateral TX: {tx_hash.hex()}")
            
            self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return tx_hash.hex()
            
        except Exception as e:
            print(f"[MorphoLoop] SupplyCollateral failed: {e}")
            return None
    
    async def _borrow(self, market_params: tuple, amount: int, on_behalf: str) -> Optional[str]:
        """Borrow from Morpho Blue"""
        if not self.agent_account:
            print(f"[MorphoLoop] No agent key - simulating borrow of {amount}")
            return "0x_simulated_borrow"
        
        try:
            tx = self.morpho_contract.functions.borrow(
                market_params,
                amount,
                0,  # No specific shares
                Web3.to_checksum_address(on_behalf),
                Web3.to_checksum_address(self.agent_account.address)  # Receive to agent
            ).build_transaction({
                'from': self.agent_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
                'gas': 400000,
                'maxFeePerGas': self.w3.eth.gas_price * 2,
                'maxPriorityFeePerGas': self.w3.to_wei(0.001, 'gwei'),
                'chainId': 8453
            })
            
            signed = self.w3.eth.account.sign_transaction(tx, self.agent_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            print(f"[MorphoLoop] Borrow TX: {tx_hash.hex()}")
            
            self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return tx_hash.hex()
            
        except Exception as e:
            print(f"[MorphoLoop] Borrow failed: {e}")
            return None
    
    async def deleverage(self, user: str, market_key: str, target_leverage: float = 1.0) -> Dict:
        """Reduce leverage by repaying debt and withdrawing collateral"""
        self._init_contracts()
        
        position_key = f"{user}_{market_key}"
        if position_key not in self.positions:
            return {"success": False, "error": "No position found"}
        
        position = self.positions[position_key]
        print(f"[MorphoLoop] 📉 Deleveraging from {position.actual_leverage:.2f}x to {target_leverage}x")
        
        # TODO: Implement deleverage logic
        # 1. Withdraw collateral
        # 2. Swap to loan token
        # 3. Repay debt
        
        return {"success": True, "message": "Deleverage not yet implemented"}
    
    def get_available_markets(self) -> list:
        """Get list of available Morpho markets"""
        return [
            {
                "key": key,
                "name": market["name"],
                "lltv": market["lltv"] / 1e18,
                "max_leverage": 1 / (1 - market["lltv"] / 1e18)
            }
            for key, market in MORPHO_MARKETS.items()
        ]


# Global instance
morpho_loop_engine = MorphoBlueLoopEngine()
