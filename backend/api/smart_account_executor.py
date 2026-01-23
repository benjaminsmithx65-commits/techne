"""
Smart Account Executor - Unified On-Chain Operations

Replaces direct PRIVATE_KEY usage with Smart Account session key execution.
All DeFi operations go through user's Smart Account with limited permissions.

Key Functions:
- exit_position: Withdraw all from Aave (existing V4.3.4 function)
- harvest_rewards: Collect LP rewards
- supply_to_aave: Deposit to Aave lending
- withdraw_from_aave: Partial withdraw from Aave
- swap_cowswap: MEV-protected swap via CoWSwap
"""

import os
import asyncio
from typing import Optional, Tuple, Dict, Any
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
FACTORY_ADDRESS = os.getenv("TECHNE_FACTORY_ADDRESS", "0x33f5e2F6d194869ACc60C965C2A24eDC5de8a216")
PIMLICO_URL = os.getenv("PIMLICO_BUNDLER_URL", "")

# Protocol addresses on Base mainnet
AAVE_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
COWSWAP_SETTLEMENT = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH = "0x4200000000000000000000000000000000000006"

# Old Techne Wallet (for backward compatibility during migration)
LEGACY_TECHNE_WALLET = "0xC83E01e39A56Ec8C56Dd45236E58eE7a139cCDD4"

# Function selectors
SELECTORS = {
    "aave_supply": "0xe8eda9df",      # supply(address,uint256,address,uint16)
    "aave_withdraw": "0x69328dec",     # withdraw(address,uint256,address)
    "erc20_approve": "0x095ea7b3",     # approve(address,uint256)
    "erc20_transfer": "0xa9059cbb",    # transfer(address,uint256)
}

# Smart Account ABI (minimal for execution)
SMART_ACCOUNT_ABI = [
    {
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"}
        ],
        "name": "execute",
        "outputs": [{"name": "", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "key", "type": "address"}],
        "name": "getSessionKeyInfo",
        "outputs": [
            {"name": "active", "type": "bool"},
            {"name": "validUntil", "type": "uint48"},
            {"name": "dailyLimitUSD", "type": "uint256"},
            {"name": "spentTodayUSD", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# Factory ABI
FACTORY_ABI = [
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "getAccounts",
        "outputs": [{"name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "salt", "type": "bytes32"}],
        "name": "createAccount",
        "outputs": [{"name": "account", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "salt", "type": "bytes32"}
        ],
        "name": "getAddress",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class SmartAccountExecutor:
    """
    Executes DeFi operations through user's Smart Account.
    
    Modes:
    1. OWNER MODE: User signs directly (frontend wallet)
    2. SESSION KEY MODE: Backend signs with session key (automated)
    3. LEGACY MODE: Falls back to old Techne Wallet (migration period)
    """
    
    def __init__(self, user_address: str, agent_id: str = None):
        self.user_address = Web3.to_checksum_address(user_address)
        self.agent_id = agent_id
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        # Get user's Smart Account
        self.smart_account = self._get_user_smart_account()
        
        # Session key for automated operations
        self._session_key = None
        if agent_id:
            self._load_session_key()
    
    def _get_user_smart_account(self) -> Optional[str]:
        """Get user's Smart Account address from factory."""
        try:
            factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(FACTORY_ADDRESS),
                abi=FACTORY_ABI
            )
            accounts = factory.functions.getAccounts(self.user_address).call()
            if accounts:
                return accounts[0]  # Return first account
            return None
        except Exception as e:
            print(f"[SmartAccountExecutor] Error getting account: {e}")
            return None
    
    def _load_session_key(self):
        """Load session key signer for this agent."""
        try:
            from api.session_key_signer import SessionKeySigner
            self._session_key = SessionKeySigner(self.agent_id, self.user_address)
        except Exception as e:
            print(f"[SmartAccountExecutor] Could not load session key: {e}")
    
    @property
    def is_smart_account_active(self) -> bool:
        """Check if user has an active Smart Account."""
        return self.smart_account is not None
    
    @property
    def can_use_session_key(self) -> bool:
        """Check if session key is available and valid."""
        if not self._session_key or not self.smart_account:
            return False
        
        try:
            contract = self.w3.eth.contract(
                address=self.smart_account,
                abi=SMART_ACCOUNT_ABI
            )
            active, valid_until, _, _ = contract.functions.getSessionKeyInfo(
                self._session_key.address
            ).call()
            import time
            return active and valid_until > time.time()
        except Exception:
            return False
    
    # ============================================
    # AAVE OPERATIONS
    # ============================================
    
    async def exit_position_aave(self) -> Dict[str, Any]:
        """
        Exit entire Aave position - withdraw all to user's wallet.
        
        Uses Smart Account if available, falls back to legacy Techne Wallet.
        """
        print(f"[ExitPosition] User: {self.user_address}")
        print(f"[ExitPosition] Smart Account: {self.smart_account}")
        
        if self.smart_account:
            # New path: Use Smart Account
            return await self._exit_via_smart_account()
        else:
            # Legacy path: Use old Techne Wallet
            return await self._exit_via_legacy_wallet()
    
    async def _exit_via_smart_account(self) -> Dict[str, Any]:
        """Exit via Smart Account (owner must sign)."""
        # Build withdraw calldata for Aave
        # withdraw(address asset, uint256 amount, address to)
        # amount = type(uint256).max for full withdrawal
        
        withdraw_data = self._encode_aave_withdraw(
            asset=USDC,
            amount=2**256 - 1,  # max uint256 = withdraw all
            recipient=self.user_address
        )
        
        # This needs to be signed by owner (frontend)
        return {
            "success": True,
            "mode": "smart_account",
            "smart_account": self.smart_account,
            "calldata": {
                "target": AAVE_POOL,
                "value": 0,
                "data": withdraw_data.hex()
            },
            "message": "Transaction prepared. Owner signature required."
        }
    
    async def _exit_via_legacy_wallet(self) -> Dict[str, Any]:
        """Exit via legacy Techne Wallet (uses PRIVATE_KEY)."""
        agent_key = os.getenv("PRIVATE_KEY")
        if not agent_key:
            return {"success": False, "error": "No PRIVATE_KEY configured"}
        
        try:
            account = Account.from_key(agent_key)
            
            # Legacy exitPosition ABI (V4.3.4)
            legacy_abi = [{
                "inputs": [
                    {"name": "user", "type": "address"},
                    {"name": "lendingProtocol", "type": "address"}
                ],
                "name": "exitPosition",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }]
            
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(LEGACY_TECHNE_WALLET),
                abi=legacy_abi
            )
            
            tx = contract.functions.exitPosition(
                self.user_address,
                Web3.to_checksum_address(AAVE_POOL)
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[ExitPosition] Legacy TX sent: {tx_hash.hex()}")
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt.status == 1,
                "mode": "legacy",
                "tx_hash": tx_hash.hex(),
                "block": receipt.blockNumber
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "mode": "legacy"}
    
    async def supply_to_aave(self, amount: int, asset: str = USDC) -> Dict[str, Any]:
        """
        Supply assets to Aave lending pool.
        
        Args:
            amount: Amount in smallest units (e.g., USDC with 6 decimals)
            asset: Token address to supply
        """
        if not self.smart_account:
            return {"success": False, "error": "No Smart Account found"}
        
        # First, need approval
        approve_data = self._encode_erc20_approve(AAVE_POOL, amount)
        
        # Then supply
        supply_data = self._encode_aave_supply(asset, amount, self.smart_account)
        
        return {
            "success": True,
            "mode": "smart_account",
            "steps": [
                {"target": asset, "value": 0, "data": approve_data.hex(), "desc": "Approve"},
                {"target": AAVE_POOL, "value": 0, "data": supply_data.hex(), "desc": "Supply"}
            ],
            "message": "Multi-step transaction prepared. Owner signature required."
        }
    
    async def withdraw_from_aave(self, amount: int, asset: str = USDC) -> Dict[str, Any]:
        """
        Withdraw specific amount from Aave.
        
        Args:
            amount: Amount to withdraw (in smallest units)
            asset: Token address to withdraw
        """
        if not self.smart_account:
            return await self._exit_via_legacy_wallet()
        
        withdraw_data = self._encode_aave_withdraw(asset, amount, self.user_address)
        
        return {
            "success": True,
            "mode": "smart_account",
            "calldata": {
                "target": AAVE_POOL,
                "value": 0,
                "data": withdraw_data.hex()
            }
        }
    
    # ============================================
    # HARVEST OPERATIONS
    # ============================================
    
    async def harvest_rewards(self, protocol: str = "aerodrome") -> Dict[str, Any]:
        """
        Harvest rewards from LP positions.
        
        For Aerodrome: Claims AERO rewards from gauge contracts.
        """
        if not self.smart_account:
            # Legacy mode - simulate
            return {
                "success": True,
                "mode": "simulated",
                "harvested_usd": 0,
                "message": "No Smart Account - harvest simulated"
            }
        
        # TODO: Implement actual gauge.getReward() call
        # This requires knowing which gauges the user has staked in
        
        return {
            "success": True,
            "mode": "smart_account",
            "harvested_usd": 0,
            "message": "Harvest prepared - needs gauge addresses"
        }
    
    # ============================================
    # ENCODING HELPERS
    # ============================================
    
    def _encode_aave_supply(self, asset: str, amount: int, on_behalf_of: str) -> bytes:
        """Encode Aave supply(address,uint256,address,uint16) call."""
        from eth_abi import encode
        selector = bytes.fromhex(SELECTORS["aave_supply"][2:])
        params = encode(
            ['address', 'uint256', 'address', 'uint16'],
            [asset, amount, on_behalf_of, 0]  # referralCode = 0
        )
        return selector + params
    
    def _encode_aave_withdraw(self, asset: str, amount: int, recipient: str) -> bytes:
        """Encode Aave withdraw(address,uint256,address) call."""
        from eth_abi import encode
        selector = bytes.fromhex(SELECTORS["aave_withdraw"][2:])
        params = encode(
            ['address', 'uint256', 'address'],
            [asset, amount, recipient]
        )
        return selector + params
    
    def _encode_erc20_approve(self, spender: str, amount: int) -> bytes:
        """Encode ERC20 approve(address,uint256) call."""
        from eth_abi import encode
        selector = bytes.fromhex(SELECTORS["erc20_approve"][2:])
        params = encode(
            ['address', 'uint256'],
            [spender, amount]
        )
        return selector + params
    
    def _encode_erc20_transfer(self, recipient: str, amount: int) -> bytes:
        """Encode ERC20 transfer(address,uint256) call."""
        from eth_abi import encode
        selector = bytes.fromhex(SELECTORS["erc20_transfer"][2:])
        params = encode(
            ['address', 'uint256'],
            [recipient, amount]
        )
        return selector + params


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

async def execute_exit_position(user_address: str, agent_id: str = None) -> Dict[str, Any]:
    """Helper to exit position for a user."""
    executor = SmartAccountExecutor(user_address, agent_id)
    return await executor.exit_position_aave()


async def execute_supply(user_address: str, amount: int, asset: str = USDC) -> Dict[str, Any]:
    """Helper to supply to Aave."""
    executor = SmartAccountExecutor(user_address)
    return await executor.supply_to_aave(amount, asset)


async def execute_withdraw(user_address: str, amount: int, asset: str = USDC) -> Dict[str, Any]:
    """Helper to withdraw from Aave."""
    executor = SmartAccountExecutor(user_address)
    return await executor.withdraw_from_aave(amount, asset)


def get_user_smart_account(user_address: str) -> Optional[str]:
    """Get user's Smart Account address."""
    executor = SmartAccountExecutor(user_address)
    return executor.smart_account
