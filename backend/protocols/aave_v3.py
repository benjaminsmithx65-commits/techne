"""
Aave V3 Protocol Integration for Base Network
Handles deposits (supply), withdrawals, and partial withdrawals for Techne Finance.
"""
import logging
from typing import Optional, Dict, Any
from web3 import Web3
from eth_account import Account
import os

logger = logging.getLogger(__name__)

# ==========================================
# AAVE V3 BASE MAINNET ADDRESSES
# ==========================================
AAVE_V3_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
AUSDC_ADDRESS = "0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB"  # aToken

# Pool discovery contracts (like Aerodrome Sugar)
UI_POOL_DATA_PROVIDER = "0x174446a6741300cD2E7C1b1A636Fee99c8F83502"
POOL_ADDRESSES_PROVIDER = "0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D"

# ==========================================
# AAVE V3 POOL ABI (minimal for supply/withdraw)
# ==========================================
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
            {"name": "to", "type": "address"}
        ],
        "name": "withdraw",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "user", "type": "address"}
        ],
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

# ERC20 ABI for approvals and balance checks
ERC20_ABI = [
    {
        "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ==========================================
# UI POOL DATA PROVIDER ABI (for pool discovery like Aerodrome Sugar)
# Returns all reserves with APY, TVL, liquidity
# ==========================================
UI_POOL_DATA_PROVIDER_ABI = [
    {
        "inputs": [{"name": "provider", "type": "address"}],
        "name": "getReservesData",
        "outputs": [
            {
                "components": [
                    {"name": "underlyingAsset", "type": "address"},
                    {"name": "name", "type": "string"},
                    {"name": "symbol", "type": "string"},
                    {"name": "decimals", "type": "uint256"},
                    {"name": "baseLTVasCollateral", "type": "uint256"},
                    {"name": "reserveLiquidationThreshold", "type": "uint256"},
                    {"name": "reserveLiquidationBonus", "type": "uint256"},
                    {"name": "reserveFactor", "type": "uint256"},
                    {"name": "usageAsCollateralEnabled", "type": "bool"},
                    {"name": "borrowingEnabled", "type": "bool"},
                    {"name": "stableBorrowRateEnabled", "type": "bool"},
                    {"name": "isActive", "type": "bool"},
                    {"name": "isFrozen", "type": "bool"},
                    {"name": "liquidityIndex", "type": "uint128"},
                    {"name": "variableBorrowIndex", "type": "uint128"},
                    {"name": "liquidityRate", "type": "uint128"},  # Supply APY in Ray (1e27)
                    {"name": "variableBorrowRate", "type": "uint128"},
                    {"name": "stableBorrowRate", "type": "uint128"},
                    {"name": "lastUpdateTimestamp", "type": "uint40"},
                    {"name": "aTokenAddress", "type": "address"},
                    {"name": "stableDebtTokenAddress", "type": "address"},
                    {"name": "variableDebtTokenAddress", "type": "address"},
                    {"name": "interestRateStrategyAddress", "type": "address"},
                    {"name": "availableLiquidity", "type": "uint256"},  # Available to borrow
                    {"name": "totalPrincipalStableDebt", "type": "uint256"},
                    {"name": "averageStableRate", "type": "uint256"},
                    {"name": "stableDebtLastUpdateTimestamp", "type": "uint256"},
                    {"name": "totalScaledVariableDebt", "type": "uint256"},
                    {"name": "priceInMarketReferenceCurrency", "type": "uint256"},
                    {"name": "priceOracle", "type": "address"},
                    {"name": "variableRateSlope1", "type": "uint256"},
                    {"name": "variableRateSlope2", "type": "uint256"},
                    {"name": "stableRateSlope1", "type": "uint256"},
                    {"name": "stableRateSlope2", "type": "uint256"},
                    {"name": "baseStableBorrowRate", "type": "uint256"},
                    {"name": "baseVariableBorrowRate", "type": "uint256"},
                    {"name": "optimalUsageRatio", "type": "uint256"},
                    {"name": "isPaused", "type": "bool"},
                    {"name": "isSiloedBorrowing", "type": "bool"},
                    {"name": "accruedToTreasury", "type": "uint128"},
                    {"name": "unbacked", "type": "uint128"},
                    {"name": "isolationModeTotalDebt", "type": "uint128"},
                    {"name": "flashLoanEnabled", "type": "bool"},
                    {"name": "debtCeiling", "type": "uint256"},
                    {"name": "debtCeilingDecimals", "type": "uint256"},
                    {"name": "eModeCategoryId", "type": "uint8"},
                    {"name": "borrowCap", "type": "uint256"},
                    {"name": "supplyCap", "type": "uint256"},
                    {"name": "eModeLtv", "type": "uint16"},
                    {"name": "eModeLiquidationThreshold", "type": "uint16"},
                    {"name": "eModeLiquidationBonus", "type": "uint16"},
                    {"name": "eModePriceSource", "type": "address"},
                    {"name": "eModeLabel", "type": "string"},
                    {"name": "borrowableInIsolation", "type": "bool"}
                ],
                "name": "",
                "type": "tuple[]"
            },
            {
                "components": [
                    {"name": "marketReferenceCurrencyUnit", "type": "uint256"},
                    {"name": "marketReferenceCurrencyPriceInUsd", "type": "int256"},
                    {"name": "networkBaseTokenPriceInUsd", "type": "int256"},
                    {"name": "networkBaseTokenPriceDecimals", "type": "uint8"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


class AaveV3Protocol:
    """
    Aave V3 Protocol handler for Base network.
    Supports supply, withdraw, and partial withdraw operations.
    """
    
    def __init__(self, rpc_url: Optional[str] = None):
        """Initialize with RPC connection."""
        self.rpc_url = rpc_url or os.getenv("ALCHEMY_RPC_URL") or os.getenv("BASE_RPC_URL")
        if not self.rpc_url:
            raise ValueError("RPC URL required for Aave V3 integration")
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Initialize contracts
        self.pool = self.w3.eth.contract(
            address=Web3.to_checksum_address(AAVE_V3_POOL),
            abi=AAVE_POOL_ABI
        )
        self.usdc = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI
        )
        self.ausdc = self.w3.eth.contract(
            address=Web3.to_checksum_address(AUSDC_ADDRESS),
            abi=ERC20_ABI
        )
        
        # UI Pool Data Provider (like Aerodrome Sugar - returns all pools with APY/TVL)
        self.ui_data_provider = self.w3.eth.contract(
            address=Web3.to_checksum_address(UI_POOL_DATA_PROVIDER),
            abi=UI_POOL_DATA_PROVIDER_ABI
        )
        
        logger.info(f"🔷 Aave V3 Protocol initialized on Base")
    
    def get_reserves_data(self) -> list[Dict[str, Any]]:
        """
        Get all Aave V3 reserves (pools) with live APY and TVL.
        Similar to Aerodrome Sugar.byAddress() but for lending pools.
        
        Returns:
            List of reserve data dicts with APY, TVL, asset info
        """
        try:
            # Call getReservesData with Pool Addresses Provider
            result = self.ui_data_provider.functions.getReservesData(
                Web3.to_checksum_address(POOL_ADDRESSES_PROVIDER)
            ).call()
            
            reserves_data, base_currency_info = result
            logger.info(f"🔷 Aave V3: Got {len(reserves_data)} raw reserves")
            
            pools = []
            for i, reserve in enumerate(reserves_data):
                try:
                    # Reserve is a tuple - access by index matching ABI order
                    # Index mapping based on ABI:
                    # 0: underlyingAsset, 1: name, 2: symbol, 3: decimals
                    # 11: isActive, 12: isFrozen
                    # 15: liquidityRate (supply APY in Ray 1e27)
                    # 19: aTokenAddress
                    # 23: availableLiquidity
                    
                    symbol = reserve[2]
                    decimals = int(reserve[3])
                    is_active = reserve[11]
                    is_frozen = reserve[12]
                    
                    # Skip frozen/inactive reserves
                    if is_frozen or not is_active:
                        continue
                    
                    # liquidityRate is in Ray (1e27) - convert to APY %
                    liquidity_rate_ray = int(reserve[15])
                    supply_apy = (liquidity_rate_ray / 1e27) * 100
                    
                    # Available liquidity (TVL proxy)
                    available_liquidity = int(reserve[23])
                    tvl_usd = available_liquidity / (10 ** decimals)
                    
                    atoken_address = reserve[19]
                    
                    pools.append({
                        "id": f"aave_v3_{symbol.lower()}",
                        "protocol": "aave_v3",
                        "name": f"Aave V3 {symbol}",
                        "asset": symbol,
                        "underlying_asset": reserve[0],
                        "atoken_address": atoken_address,
                        "decimals": decimals,
                        "apy": round(supply_apy, 2),
                        "tvl": tvl_usd,
                        "pool_type": "single",
                        "risk_level": "low",
                        "is_lending": True,
                        "is_active": is_active,
                        "is_frozen": is_frozen,
                        "audited": True,
                        "implemented": True
                    })
                    
                except Exception as inner_e:
                    logger.warning(f"⚠️ Error parsing reserve {i}: {inner_e}")
                    continue
            
            logger.info(f"🔷 Aave V3: Fetched {len(pools)} active reserves on-chain")
            return pools
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch Aave reserves: {e}")
            return []
    
    def get_usdc_balance(self, user_address: str) -> int:
        """Get USDC balance in wei (6 decimals)."""
        return self.usdc.functions.balanceOf(
            Web3.to_checksum_address(user_address)
        ).call()
    
    def get_ausdc_balance(self, user_address: str) -> int:
        """Get aUSDC balance (deposited amount + interest)."""
        return self.ausdc.functions.balanceOf(
            Web3.to_checksum_address(user_address)
        ).call()
    
    def get_position(self, user_address: str) -> Dict[str, Any]:
        """Get user's Aave position details."""
        ausdc_balance = self.get_ausdc_balance(user_address)
        usdc_balance = self.get_usdc_balance(user_address)
        
        return {
            "deposited_ausdc": ausdc_balance,
            "deposited_usdc_value": ausdc_balance / 1e6,  # 6 decimals
            "available_usdc": usdc_balance,
            "available_usdc_value": usdc_balance / 1e6
        }
    
    def build_approve_tx(
        self, 
        user_address: str,
        amount: int,
        nonce: Optional[int] = None
    ) -> Dict:
        """Build USDC approval transaction for Aave Pool."""
        user = Web3.to_checksum_address(user_address)
        
        # Check current allowance
        current_allowance = self.usdc.functions.allowance(user, AAVE_V3_POOL).call()
        if current_allowance >= amount:
            return None  # Already approved
        
        tx = self.usdc.functions.approve(
            Web3.to_checksum_address(AAVE_V3_POOL),
            amount
        ).build_transaction({
            'from': user,
            'nonce': nonce or self.w3.eth.get_transaction_count(user),
            'gas': 100000,
            'maxFeePerGas': self.w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': self.w3.to_wei(0.001, 'gwei')
        })
        
        return tx
    
    def build_supply_tx(
        self,
        user_address: str,
        amount: int,
        nonce: Optional[int] = None
    ) -> Dict:
        """
        Build supply (deposit) transaction.
        
        Args:
            user_address: Address supplying USDC
            amount: Amount in USDC wei (6 decimals)
            nonce: Optional nonce override
        
        Returns:
            Transaction dict ready for signing
        """
        user = Web3.to_checksum_address(user_address)
        
        tx = self.pool.functions.supply(
            Web3.to_checksum_address(USDC_ADDRESS),
            amount,
            user,  # onBehalfOf
            0      # referralCode
        ).build_transaction({
            'from': user,
            'nonce': nonce or self.w3.eth.get_transaction_count(user),
            'gas': 300000,
            'maxFeePerGas': self.w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': self.w3.to_wei(0.001, 'gwei')
        })
        
        return tx
    
    def build_withdraw_tx(
        self,
        user_address: str,
        amount: int,
        nonce: Optional[int] = None
    ) -> Dict:
        """
        Build withdraw transaction.
        
        Args:
            user_address: Address to receive withdrawn USDC
            amount: Amount in USDC wei, or max uint256 for full withdraw
            nonce: Optional nonce override
        
        Returns:
            Transaction dict ready for signing
        """
        user = Web3.to_checksum_address(user_address)
        
        tx = self.pool.functions.withdraw(
            Web3.to_checksum_address(USDC_ADDRESS),
            amount,
            user  # to
        ).build_transaction({
            'from': user,
            'nonce': nonce or self.w3.eth.get_transaction_count(user),
            'gas': 300000,
            'maxFeePerGas': self.w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': self.w3.to_wei(0.001, 'gwei')
        })
        
        return tx
    
    def build_withdraw_percent_tx(
        self,
        user_address: str,
        percent: int,
        nonce: Optional[int] = None
    ) -> Dict:
        """
        Build partial withdraw transaction (25%, 50%, 100%).
        
        Args:
            user_address: Address with Aave position
            percent: 25, 50, or 100
            nonce: Optional nonce override
        
        Returns:
            Transaction dict ready for signing
        """
        if percent not in [25, 50, 100]:
            raise ValueError("Percent must be 25, 50, or 100")
        
        user = Web3.to_checksum_address(user_address)
        
        # Get current aUSDC balance
        ausdc_balance = self.get_ausdc_balance(user)
        
        if ausdc_balance == 0:
            raise ValueError("No Aave position to withdraw from")
        
        if percent == 100:
            # Use max uint256 for full withdraw
            amount = 2**256 - 1
        else:
            amount = (ausdc_balance * percent) // 100
        
        return self.build_withdraw_tx(user, amount, nonce)
    
    async def supply(
        self,
        user_address: str,
        amount_usdc: float,
        private_key: str
    ) -> Dict[str, Any]:
        """
        Execute supply (deposit) to Aave.
        
        Args:
            user_address: Smart Account address
            amount_usdc: Amount in USDC (human readable, e.g. 100.0)
            private_key: Private key for signing
        
        Returns:
            Dict with tx_hash and status
        """
        try:
            amount_wei = int(amount_usdc * 1e6)  # USDC has 6 decimals
            user = Web3.to_checksum_address(user_address)
            
            # Step 1: Approve if needed
            nonce = self.w3.eth.get_transaction_count(user)
            approve_tx = self.build_approve_tx(user, amount_wei, nonce)
            
            if approve_tx:
                signed_approve = Account.sign_transaction(approve_tx, private_key)
                approve_hash = self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
                self.w3.eth.wait_for_transaction_receipt(approve_hash)
                logger.info(f"✅ USDC approved for Aave: {approve_hash.hex()}")
                nonce += 1
            
            # Step 2: Supply
            supply_tx = self.build_supply_tx(user, amount_wei, nonce)
            signed_supply = Account.sign_transaction(supply_tx, private_key)
            supply_hash = self.w3.eth.send_raw_transaction(signed_supply.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(supply_hash)
            
            logger.info(f"✅ Aave supply successful: {supply_hash.hex()}")
            
            return {
                "success": True,
                "tx_hash": supply_hash.hex(),
                "amount_usdc": amount_usdc,
                "gas_used": receipt['gasUsed'],
                "protocol": "aave_v3"
            }
            
        except Exception as e:
            logger.error(f"❌ Aave supply failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "protocol": "aave_v3"
            }
    
    async def withdraw(
        self,
        user_address: str,
        amount_usdc: Optional[float],
        private_key: str
    ) -> Dict[str, Any]:
        """
        Execute withdraw from Aave.
        
        Args:
            user_address: Smart Account address
            amount_usdc: Amount in USDC, or None for full withdraw
            private_key: Private key for signing
        
        Returns:
            Dict with tx_hash and status
        """
        try:
            user = Web3.to_checksum_address(user_address)
            
            if amount_usdc is None:
                # Full withdraw - use max uint256
                amount_wei = 2**256 - 1
            else:
                amount_wei = int(amount_usdc * 1e6)
            
            nonce = self.w3.eth.get_transaction_count(user)
            withdraw_tx = self.build_withdraw_tx(user, amount_wei, nonce)
            signed_tx = Account.sign_transaction(withdraw_tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            logger.info(f"✅ Aave withdraw successful: {tx_hash.hex()}")
            
            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "amount_usdc": amount_usdc or "full",
                "gas_used": receipt['gasUsed'],
                "protocol": "aave_v3"
            }
            
        except Exception as e:
            logger.error(f"❌ Aave withdraw failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "protocol": "aave_v3"
            }
    
    async def withdraw_percent(
        self,
        user_address: str,
        percent: int,
        private_key: str
    ) -> Dict[str, Any]:
        """
        Execute partial withdraw from Aave (for Portfolio close buttons).
        
        Args:
            user_address: Smart Account address
            percent: 25, 50, or 100
            private_key: Private key for signing
        
        Returns:
            Dict with tx_hash and status
        """
        try:
            user = Web3.to_checksum_address(user_address)
            
            nonce = self.w3.eth.get_transaction_count(user)
            withdraw_tx = self.build_withdraw_percent_tx(user, percent, nonce)
            signed_tx = Account.sign_transaction(withdraw_tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            logger.info(f"✅ Aave {percent}% withdraw successful: {tx_hash.hex()}")
            
            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "percent_withdrawn": percent,
                "gas_used": receipt['gasUsed'],
                "protocol": "aave_v3"
            }
            
        except Exception as e:
            logger.error(f"❌ Aave {percent}% withdraw failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "protocol": "aave_v3"
            }


# Singleton instance
_aave_protocol: Optional[AaveV3Protocol] = None

def get_aave_protocol() -> AaveV3Protocol:
    """Get or create Aave V3 Protocol singleton."""
    global _aave_protocol
    if _aave_protocol is None:
        _aave_protocol = AaveV3Protocol()
    return _aave_protocol
