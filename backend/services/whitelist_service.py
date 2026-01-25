"""
Auto-Whitelist Service for V4.3.2 Contract
Automatically whitelists users when they deploy an agent
"""

import os
from web3 import Web3
from eth_account import Account
import logging

logger = logging.getLogger(__name__)

# V4.3.2 Contract ABI (only whitelist function)
WHITELIST_ABI = [
    {
        "inputs": [{"name": "user", "type": "address"}],
        "name": "whitelistUser",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "role", "type": "bytes32"}, {"name": "account", "type": "address"}],
        "name": "hasRole",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# WHITELISTED_ROLE = keccak256("WHITELISTED_ROLE")
WHITELISTED_ROLE = Web3.keccak(text="WHITELISTED_ROLE").hex()


class WhitelistService:
    """Service to auto-whitelist users on V4.3.2 contract"""
    
    def __init__(self):
        self.rpc_url = os.getenv(
            "ALCHEMY_RPC_URL",
            "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb"
        )
        self.private_key = os.getenv("PRIVATE_KEY")
        self.contract_address = os.getenv(
            "AGENT_WALLET_V43_ADDRESS",
            "0x1ff18a7b56d7fd3b07ce789e47ac587de2f14e0d"  # V4.3.3 (2026-01-25)
        )
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address),
            abi=WHITELIST_ABI
        )
        
        if self.private_key:
            pk = self.private_key if self.private_key.startswith('0x') else f'0x{self.private_key}'
            self.account = Account.from_key(pk)
            logger.info(f"[Whitelist] Service initialized. Signer: {self.account.address}")
        else:
            self.account = None
            logger.warning("[Whitelist] No PRIVATE_KEY configured - whitelist will be disabled")
    
    def is_whitelisted(self, user_address: str) -> bool:
        """Check if user is already whitelisted"""
        try:
            user = Web3.to_checksum_address(user_address)
            return self.contract.functions.hasRole(WHITELISTED_ROLE, user).call()
        except Exception as e:
            logger.error(f"[Whitelist] Failed to check role: {e}")
            return False
    
    def whitelist_user(self, user_address: str) -> dict:
        """
        Whitelist a user on the contract
        Returns: {"success": bool, "tx_hash": str, "message": str}
        """
        if not self.account:
            return {
                "success": False,
                "tx_hash": None,
                "message": "Whitelist service not configured (no PRIVATE_KEY)"
            }
        
        try:
            user = Web3.to_checksum_address(user_address)
            
            # Check if already whitelisted
            if self.is_whitelisted(user):
                logger.info(f"[Whitelist] User {user[:10]}... already whitelisted")
                return {
                    "success": True,
                    "tx_hash": None,
                    "message": "User already whitelisted"
                }
            
            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            tx = self.contract.functions.whitelistUser(user).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': 100000,
                'maxFeePerGas': self.w3.eth.gas_price * 2,
                'maxPriorityFeePerGas': self.w3.to_wei(0.001, 'gwei'),
                'chainId': 8453  # Base mainnet
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"[Whitelist] Whitelisted {user[:10]}... | TX: {tx_hash.hex()}")
            
            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "message": f"User whitelisted successfully"
            }
            
        except Exception as e:
            logger.error(f"[Whitelist] Failed to whitelist {user_address}: {e}")
            return {
                "success": False,
                "tx_hash": None,
                "message": str(e)
            }


# Singleton instance
_whitelist_service = None

def get_whitelist_service() -> WhitelistService:
    global _whitelist_service
    if _whitelist_service is None:
        _whitelist_service = WhitelistService()
    return _whitelist_service
