"""
Smart Loop Engine - Leveraged DeFi Positions
Production implementation for Aave V3 on Base

Leverage Loop Pattern:
1. Deposit collateral (USDC)
2. Borrow against collateral (USDC)
3. Re-deposit borrowed USDC
4. Repeat until target leverage reached

Safety Features:
- Health Factor monitoring (min 1.5)
- Max leverage cap (3x)
- Emergency deleveraging
"""

import asyncio
import os
from typing import Dict, Optional, Tuple
from datetime import datetime
from web3 import Web3
from eth_account import Account
from dataclasses import dataclass
import logging

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Aave V3 on Base
AAVE_POOL_ADDRESS = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
AAVE_ORACLE_ADDRESS = "0x2Cc0Fc26eD4563A5ce5e8bdcfe1A2878676Ae156"
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
AUSDC_ADDRESS = "0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB"  # aUSDC on Base

# Aave V3 Pool ABI (minimal)
AAVE_POOL_ABI = [
    {
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
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "interestRateMode", "type": "uint256"},
            {"name": "referralCode", "type": "uint16"},
            {"name": "onBehalfOf", "type": "address"}
        ],
        "name": "borrow",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "interestRateMode", "type": "uint256"},
            {"name": "onBehalfOf", "type": "address"}
        ],
        "name": "repay",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "to", "type": "address"}
        ],
        "name": "withdraw",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"name": "totalCollateralBase", "type": "uint256"},
            {"name": "totalDebtBase", "type": "uint256"},
            {"name": "availableBorrowsBase", "type": "uint256"},
            {"name": "currentLiquidationThreshold", "type": "uint256"},
            {"name": "ltv", "type": "uint256"},
            {"name": "healthFactor", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI for approvals
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
class LoopPosition:
    """Tracks a leveraged position"""
    user: str
    initial_deposit: int  # in USDC (6 decimals)
    current_collateral: int
    current_debt: int
    target_leverage: float
    actual_leverage: float
    health_factor: float
    loop_count: int
    created_at: str
    last_updated: str


class SmartLoopEngine:
    """
    Production Smart Loop Engine for Aave V3 Leverage
    
    Features:
    - Real Web3 transactions
    - Health factor monitoring
    - Iterative leverage building
    - Emergency deleverage
    """
    
    # Safety constants
    MIN_HEALTH_FACTOR = 1.5  # Never go below this
    MAX_LEVERAGE = 3.0       # Cap at 3x
    USDC_LTV = 0.77          # Aave USDC loan-to-value (77%)
    
    def __init__(self):
        self.rpc_url = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = None
        self.pool_contract = None
        self.usdc_contract = None
        
        # Position tracking
        self.positions: Dict[str, LoopPosition] = {}
        
        # Agent signer
        self.agent_key = os.getenv("PRIVATE_KEY")
        self.agent_account = None
        
        if self.agent_key:
            pk = self.agent_key if self.agent_key.startswith('0x') else f'0x{self.agent_key}'
            self.agent_account = Account.from_key(pk)
            logger.info(f"[SmartLoop] Agent signer: {self.agent_account.address}")
    
    def _init_contracts(self):
        """Initialize Web3 and contracts"""
        if not self.w3:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            self.pool_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(AAVE_POOL_ADDRESS),
                abi=AAVE_POOL_ABI
            )
            self.usdc_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(USDC_ADDRESS),
                abi=ERC20_ABI
            )
    
    def calculate_loop_parameters(self, initial_amount: int, target_leverage: float) -> Dict:
        """
        Calculate how many loops needed and amounts per loop
        
        Leverage formula:
        With LTV of 77%, each loop adds ~77% more exposure.
        Total leverage after n loops = 1 + 0.77 + 0.77^2 + ... ≈ 1/(1-0.77) = ~4.3x max
        
        Safe leverage with health factor 1.5:
        Max safe = ~2.5x (to maintain HF > 1.5)
        """
        target = min(target_leverage, self.MAX_LEVERAGE)
        
        # Calculate required loops
        # Each loop: deposit X, borrow X * LTV, re-deposit
        loops = 0
        cumulative_collateral = initial_amount
        cumulative_debt = 0
        
        loop_details = []
        
        while True:
            # How much can we borrow?
            available_borrow = int(cumulative_collateral * self.USDC_LTV) - cumulative_debt
            
            if available_borrow <= 0:
                break
            
            # Check if adding this would exceed target leverage
            new_collateral = cumulative_collateral + available_borrow
            new_debt = cumulative_debt + available_borrow
            new_leverage = new_collateral / initial_amount
            
            # Calculate health factor
            # HF = (collateral * liquidation_threshold) / debt
            liquidation_threshold = 0.80  # USDC on Aave
            hf = (new_collateral * liquidation_threshold) / new_debt if new_debt > 0 else float('inf')
            
            if new_leverage > target or hf < self.MIN_HEALTH_FACTOR:
                # Reduce borrow to hit target safely
                if cumulative_debt == 0:
                    # First loop, calculate exact amount for target
                    target_debt = initial_amount * (target - 1)
                    safe_debt = (cumulative_collateral * liquidation_threshold) / self.MIN_HEALTH_FACTOR
                    available_borrow = min(target_debt, safe_debt, available_borrow)
                else:
                    break
            
            if available_borrow <= 1000:  # Less than $0.001 USDC
                break
            
            loop_details.append({
                "loop": loops + 1,
                "borrow_amount": available_borrow,
                "new_collateral": cumulative_collateral + available_borrow,
                "new_debt": cumulative_debt + available_borrow,
                "leverage": (cumulative_collateral + available_borrow) / initial_amount,
                "health_factor": hf
            })
            
            cumulative_collateral += available_borrow
            cumulative_debt += available_borrow
            loops += 1
            
            if loops >= 10:  # Safety limit
                break
        
        final_leverage = cumulative_collateral / initial_amount if initial_amount > 0 else 0
        final_hf = (cumulative_collateral * 0.80) / cumulative_debt if cumulative_debt > 0 else float('inf')
        
        return {
            "initial_amount": initial_amount,
            "target_leverage": target,
            "actual_leverage": final_leverage,
            "total_loops": loops,
            "final_collateral": cumulative_collateral,
            "final_debt": cumulative_debt,
            "health_factor": final_hf,
            "loop_details": loop_details
        }
    
    async def execute_leverage_loop(
        self,
        user: str,
        amount: int,
        target_leverage: float,
        on_behalf_of: str = None
    ) -> Dict:
        """
        Execute the smart loop to build leveraged position
        
        Args:
            user: User address
            amount: Initial USDC amount (6 decimals)
            target_leverage: Target leverage (1.0 to 3.0)
            on_behalf_of: Execute on behalf of (for Smart Accounts)
        
        Returns:
            Position details
        """
        self._init_contracts()
        on_behalf = on_behalf_of or user
        
        print(f"[SmartLoop] 🔄 Building {target_leverage}x leverage for {user[:10]}...")
        print(f"[SmartLoop] Initial deposit: ${amount / 1e6:.2f} USDC")
        
        # Calculate loop parameters
        params = self.calculate_loop_parameters(amount, target_leverage)
        print(f"[SmartLoop] Calculated: {params['total_loops']} loops for {params['actual_leverage']:.2f}x leverage")
        print(f"[SmartLoop] Final HF: {params['health_factor']:.2f}")
        
        tx_hashes = []
        
        try:
            # Step 1: Initial deposit
            print(f"[SmartLoop] Step 1: Initial deposit of ${amount / 1e6:.2f} USDC")
            
            # Approve USDC to Aave Pool
            approve_tx = await self._approve_usdc(amount)
            if approve_tx:
                tx_hashes.append(approve_tx)
            
            # Supply to Aave
            supply_tx = await self._supply_usdc(amount, on_behalf)
            if supply_tx:
                tx_hashes.append(supply_tx)
            
            # Step 2: Execute loops
            for i, loop in enumerate(params['loop_details']):
                print(f"[SmartLoop] Loop {i+1}: Borrow ${loop['borrow_amount'] / 1e6:.2f} → Re-deposit")
                
                # Borrow
                borrow_tx = await self._borrow_usdc(loop['borrow_amount'], on_behalf)
                if borrow_tx:
                    tx_hashes.append(borrow_tx)
                
                # Re-deposit borrowed amount
                supply_tx = await self._supply_usdc(loop['borrow_amount'], on_behalf)
                if supply_tx:
                    tx_hashes.append(supply_tx)
                
                # Check health factor
                hf = await self._get_health_factor(on_behalf)
                print(f"[SmartLoop]   → Health Factor: {hf:.2f}")
                
                if hf < self.MIN_HEALTH_FACTOR:
                    print(f"[SmartLoop] ⚠️ Health factor too low, stopping loops")
                    break
            
            # Get final position data
            account_data = await self._get_account_data(on_behalf)
            
            position = LoopPosition(
                user=user,
                initial_deposit=amount,
                current_collateral=account_data['collateral'],
                current_debt=account_data['debt'],
                target_leverage=target_leverage,
                actual_leverage=account_data['collateral'] / amount if amount > 0 else 0,
                health_factor=account_data['health_factor'],
                loop_count=len(params['loop_details']),
                created_at=datetime.utcnow().isoformat(),
                last_updated=datetime.utcnow().isoformat()
            )
            
            self.positions[user] = position
            
            print(f"[SmartLoop] ✅ Leverage position created!")
            print(f"[SmartLoop]   Collateral: ${position.current_collateral / 1e6:.2f}")
            print(f"[SmartLoop]   Debt: ${position.current_debt / 1e6:.2f}")
            print(f"[SmartLoop]   Leverage: {position.actual_leverage:.2f}x")
            print(f"[SmartLoop]   Health Factor: {position.health_factor:.2f}")
            
            return {
                "success": True,
                "position": position,
                "tx_hashes": tx_hashes
            }
            
        except Exception as e:
            print(f"[SmartLoop] ❌ Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "tx_hashes": tx_hashes
            }
    
    async def deleverage(self, user: str, target_leverage: float = 1.0) -> Dict:
        """
        Reduce leverage by repaying debt and withdrawing collateral
        """
        self._init_contracts()
        
        if user not in self.positions:
            return {"success": False, "error": "No position found"}
        
        position = self.positions[user]
        print(f"[SmartLoop] 📉 Deleveraging {user[:10]}... from {position.actual_leverage:.2f}x to {target_leverage}x")
        
        tx_hashes = []
        
        try:
            # Calculate how much to repay
            current_debt = position.current_debt
            target_debt = position.initial_deposit * (target_leverage - 1)
            repay_amount = max(0, current_debt - target_debt)
            
            if repay_amount > 0:
                # Withdraw to repay
                withdraw_tx = await self._withdraw_usdc(repay_amount, user)
                if withdraw_tx:
                    tx_hashes.append(withdraw_tx)
                
                # Repay debt
                repay_tx = await self._repay_usdc(repay_amount, user)
                if repay_tx:
                    tx_hashes.append(repay_tx)
            
            # Update position
            account_data = await self._get_account_data(user)
            position.current_collateral = account_data['collateral']
            position.current_debt = account_data['debt']
            position.actual_leverage = account_data['collateral'] / position.initial_deposit
            position.health_factor = account_data['health_factor']
            position.last_updated = datetime.utcnow().isoformat()
            
            print(f"[SmartLoop] ✅ Deleverage complete: {position.actual_leverage:.2f}x, HF: {position.health_factor:.2f}")
            
            return {
                "success": True,
                "position": position,
                "tx_hashes": tx_hashes
            }
            
        except Exception as e:
            print(f"[SmartLoop] ❌ Deleverage error: {e}")
            return {"success": False, "error": str(e), "tx_hashes": tx_hashes}
    
    # ==========================================
    # Transaction Builders
    # ==========================================
    
    async def _approve_usdc(self, amount: int) -> Optional[str]:
        """Approve USDC spending to Aave Pool"""
        if not self.agent_account:
            print("[SmartLoop] No agent key - simulating approve")
            return "0x_simulated_approve"
        
        try:
            tx = self.usdc_contract.functions.approve(
                Web3.to_checksum_address(AAVE_POOL_ADDRESS),
                amount
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
            print(f"[SmartLoop] Approve TX: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            print(f"[SmartLoop] Approve failed: {e}")
            return None
    
    async def _supply_usdc(self, amount: int, on_behalf_of: str) -> Optional[str]:
        """Supply USDC to Aave"""
        if not self.agent_account:
            print(f"[SmartLoop] No agent key - simulating supply of ${amount/1e6:.2f}")
            return "0x_simulated_supply"
        
        try:
            tx = self.pool_contract.functions.supply(
                Web3.to_checksum_address(USDC_ADDRESS),
                amount,
                Web3.to_checksum_address(on_behalf_of),
                0  # referral code
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
            print(f"[SmartLoop] Supply TX: {tx_hash.hex()}")
            
            # Wait for confirmation
            self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return tx_hash.hex()
            
        except Exception as e:
            print(f"[SmartLoop] Supply failed: {e}")
            return None
    
    async def _borrow_usdc(self, amount: int, on_behalf_of: str) -> Optional[str]:
        """Borrow USDC from Aave"""
        if not self.agent_account:
            print(f"[SmartLoop] No agent key - simulating borrow of ${amount/1e6:.2f}")
            return "0x_simulated_borrow"
        
        try:
            # Interest rate mode: 2 = variable rate
            tx = self.pool_contract.functions.borrow(
                Web3.to_checksum_address(USDC_ADDRESS),
                amount,
                2,  # variable rate
                0,  # referral
                Web3.to_checksum_address(on_behalf_of)
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
            print(f"[SmartLoop] Borrow TX: {tx_hash.hex()}")
            
            self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return tx_hash.hex()
            
        except Exception as e:
            print(f"[SmartLoop] Borrow failed: {e}")
            return None
    
    async def _withdraw_usdc(self, amount: int, to: str) -> Optional[str]:
        """Withdraw USDC from Aave"""
        if not self.agent_account:
            return "0x_simulated_withdraw"
        
        try:
            tx = self.pool_contract.functions.withdraw(
                Web3.to_checksum_address(USDC_ADDRESS),
                amount,
                Web3.to_checksum_address(to)
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
            return tx_hash.hex()
            
        except Exception as e:
            print(f"[SmartLoop] Withdraw failed: {e}")
            return None
    
    async def _repay_usdc(self, amount: int, on_behalf_of: str) -> Optional[str]:
        """Repay USDC to Aave"""
        if not self.agent_account:
            return "0x_simulated_repay"
        
        try:
            tx = self.pool_contract.functions.repay(
                Web3.to_checksum_address(USDC_ADDRESS),
                amount,
                2,  # variable rate
                Web3.to_checksum_address(on_behalf_of)
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
            return tx_hash.hex()
            
        except Exception as e:
            print(f"[SmartLoop] Repay failed: {e}")
            return None
    
    # ==========================================
    # Health Factor Monitoring
    # ==========================================
    
    async def _get_health_factor(self, user: str) -> float:
        """Get user's current health factor"""
        self._init_contracts()
        
        try:
            data = self.pool_contract.functions.getUserAccountData(
                Web3.to_checksum_address(user)
            ).call()
            
            # healthFactor is in 1e18 format
            return data[5] / 1e18
            
        except Exception as e:
            print(f"[SmartLoop] Get HF failed: {e}")
            return float('inf')
    
    async def _get_account_data(self, user: str) -> Dict:
        """Get full account data from Aave"""
        self._init_contracts()
        
        try:
            data = self.pool_contract.functions.getUserAccountData(
                Web3.to_checksum_address(user)
            ).call()
            
            return {
                "collateral": data[0],  # in base currency (USD, 8 decimals)
                "debt": data[1],
                "available_borrow": data[2],
                "ltv": data[4] / 100,  # in percentage
                "health_factor": data[5] / 1e18
            }
            
        except Exception as e:
            print(f"[SmartLoop] Get account data failed: {e}")
            return {
                "collateral": 0,
                "debt": 0,
                "available_borrow": 0,
                "ltv": 0,
                "health_factor": float('inf')
            }
    
    async def monitor_positions(self):
        """Background task to monitor health factors"""
        while True:
            for user, position in list(self.positions.items()):
                try:
                    hf = await self._get_health_factor(user)
                    
                    if hf < 1.2:
                        print(f"[SmartLoop] ⚠️ CRITICAL: {user[:10]} HF={hf:.2f} - AUTO DELEVERAGE!")
                        await self.deleverage(user, 1.5)
                    elif hf < 1.5:
                        print(f"[SmartLoop] ⚠️ WARNING: {user[:10]} HF={hf:.2f} - Consider deleveraging")
                    
                    position.health_factor = hf
                    position.last_updated = datetime.utcnow().isoformat()
                    
                except Exception as e:
                    print(f"[SmartLoop] Monitor error for {user}: {e}")
            
            await asyncio.sleep(60)  # Check every minute


# Global instance
smart_loop_engine = SmartLoopEngine()
