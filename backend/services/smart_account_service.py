"""
Smart Account Service for ERC-4337 Integration

This service handles:
- Deploying new smart accounts for users via Factory
- Adding backend as SessionKey
- Executing operations via UserOperations (Bundler)
"""

import os
from pathlib import Path
from web3 import Web3
from eth_account import Account
import logging
import json

logger = logging.getLogger(__name__)

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
BUNDLER_URL = os.getenv("PIMLICO_BUNDLER_URL", "https://api.pimlico.io/v2/8453/rpc?apikey=pim_demo_key")

# Contract addresses (update after deployment)
FACTORY_ADDRESS = os.getenv("TECHNE_FACTORY_ADDRESS", "0xc1ee3090330ad3f946eee995f975e9fe541aa676")
ENTRYPOINT_V07 = "0x0000000071727De22E5E9d8BAf0edAc6f37da032"

# Factory ABI (minimal)
FACTORY_ABI = [
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "createAccount",
        "outputs": [{"name": "account", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "getAddress",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "hasAccount",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "accountOf",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Smart Account ABI (minimal for operations)
ACCOUNT_ABI = [
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
        "inputs": [
            {"name": "targets", "type": "address[]"},
            {"name": "values", "type": "uint256[]"},
            {"name": "dataArray", "type": "bytes[]"}
        ],
        "name": "executeBatch",
        "outputs": [{"name": "", "type": "bytes[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class SmartAccountService:
    """Service for managing ERC-4337 Smart Accounts"""
    
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        if PRIVATE_KEY:
            pk = PRIVATE_KEY if PRIVATE_KEY.startswith('0x') else f'0x{PRIVATE_KEY}'
            self.signer = Account.from_key(pk)
            logger.info(f"[SmartAccount] Service initialized. Signer: {self.signer.address}")
        else:
            self.signer = None
            logger.warning("[SmartAccount] No PRIVATE_KEY configured")
        
        self.factory = self.w3.eth.contract(
            address=Web3.to_checksum_address(FACTORY_ADDRESS),
            abi=FACTORY_ABI
        ) if FACTORY_ADDRESS != "0x0000000000000000000000000000000000000000" else None
    
    def get_account_address(self, user_address: str) -> str:
        """
        Get deterministic smart account address for a user.
        Works even if account not deployed yet (counterfactual).
        """
        if not self.factory:
            raise ValueError("Factory not configured")
        
        user = Web3.to_checksum_address(user_address)
        return self.factory.functions.getAddress(user).call()
    
    def has_account(self, user_address: str) -> bool:
        """Check if user already has a deployed smart account"""
        if not self.factory:
            return False
        
        user = Web3.to_checksum_address(user_address)
        return self.factory.functions.hasAccount(user).call()
    
    def get_account(self, user_address: str) -> str | None:
        """Get deployed account address, or None if not deployed"""
        if not self.factory:
            return None
        
        user = Web3.to_checksum_address(user_address)
        account = self.factory.functions.accountOf(user).call()
        
        if account == "0x0000000000000000000000000000000000000000":
            return None
        return account
    
    def create_account(self, user_address: str) -> dict:
        """
        Deploy a new smart account for a user.
        
        Returns:
            {
                "success": bool,
                "account_address": str,
                "tx_hash": str,
                "message": str
            }
        """
        if not self.factory or not self.signer:
            return {
                "success": False,
                "account_address": None,
                "tx_hash": None,
                "message": "Factory or signer not configured"
            }
        
        user = Web3.to_checksum_address(user_address)
        
        # Check if already exists
        if self.has_account(user):
            existing = self.get_account(user)
            return {
                "success": True,
                "account_address": existing,
                "tx_hash": None,
                "message": "Account already exists"
            }
        
        try:
            # Build transaction
            tx = self.factory.functions.createAccount(user).build_transaction({
                "from": self.signer.address,
                "nonce": self.w3.eth.get_transaction_count(self.signer.address),
                "gas": 500000,  # Account creation uses ~400K gas
                "maxFeePerGas": self.w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, 'gwei'),
                "chainId": 8453
            })
            
            # Sign and send
            signed = self.signer.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] != 1:
                return {
                    "success": False,
                    "account_address": None,
                    "tx_hash": tx_hash.hex(),
                    "message": "Transaction failed"
                }
            
            # Get created account from event logs
            account_address = self.get_account(user)
            
            logger.info(f"[SmartAccount] Created account for {user[:10]}... → {account_address}")
            
            return {
                "success": True,
                "account_address": account_address,
                "tx_hash": tx_hash.hex(),
                "message": "Account created successfully"
            }
            
        except Exception as e:
            logger.error(f"[SmartAccount] Failed to create account: {e}")
            return {
                "success": False,
                "account_address": None,
                "tx_hash": None,
                "message": str(e)
            }
    
    def execute_for_user(
        self,
        user_address: str,
        target: str,
        value: int,
        calldata: bytes
    ) -> dict:
        """
        Execute a call on behalf of user's smart account.
        
        This uses direct execution (backend as SessionKey).
        For full ERC-4337, use build_user_operation() + bundler.
        """
        account_address = self.get_account(user_address)
        if not account_address:
            return {
                "success": False,
                "tx_hash": None,
                "message": "User has no smart account"
            }
        
        account = self.w3.eth.contract(
            address=Web3.to_checksum_address(account_address),
            abi=ACCOUNT_ABI
        )
        
        try:
            tx = account.functions.execute(
                Web3.to_checksum_address(target),
                value,
                calldata
            ).build_transaction({
                "from": self.signer.address,
                "nonce": self.w3.eth.get_transaction_count(self.signer.address),
                "gas": 300000,
                "maxFeePerGas": self.w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, 'gwei'),
                "chainId": 8453
            })
            
            signed = self.signer.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt['status'] == 1,
                "tx_hash": tx_hash.hex(),
                "message": "Executed" if receipt['status'] == 1 else "Failed"
            }
            
        except Exception as e:
            logger.error(f"[SmartAccount] Execution failed: {e}")
            return {
                "success": False,
                "tx_hash": None,
                "message": str(e)
            }


# Singleton
_smart_account_service = None

def get_smart_account_service() -> SmartAccountService:
    global _smart_account_service
    if _smart_account_service is None:
        _smart_account_service = SmartAccountService()
    return _smart_account_service
