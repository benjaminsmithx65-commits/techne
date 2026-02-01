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

# Contract addresses - Factory V2 (executeWithSessionKey - no bundler!) 2026-02-01
FACTORY_ADDRESS = os.getenv("TECHNE_FACTORY_ADDRESS", "0x9192DC52445E3d6e85EbB53723cFC2Eb9dD6e02A")
ENTRYPOINT_V07 = "0x0000000071727De22E5E9d8BAf0edAc6f37da032"

# Factory ABI (with salt support for 1 agent = 1 smart account)
FACTORY_ABI = [
    # Create account with salt (1 agent = 1 wallet)
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "agentSalt", "type": "uint256"}
        ],
        "name": "createAccount",
        "outputs": [{"name": "account", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Get address with salt
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "agentSalt", "type": "uint256"}
        ],
        "name": "getAddress",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    # accounts mapping (owner -> agentSalt -> account)
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "agentSalt", "type": "uint256"}
        ],
        "name": "accounts",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    # Check if account exists with salt
    {
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "agentSalt", "type": "uint256"}
        ],
        "name": "hasAccount",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    # Get all accounts for owner
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "getAccountsForOwner",
        "outputs": [{"name": "", "type": "address[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    # Get account count for owner
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "getAccountCount",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    # Legacy: create with default salt
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "createAccount",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Legacy: get address with default salt
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "getAddress",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    # Legacy: has account with default salt
    {
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "hasAccount",
        "outputs": [{"name": "", "type": "bool"}],
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
    },
    # NEW: Direct session key execution (no bundler needed!)
    {
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
            {"name": "estimatedValueUSD", "type": "uint256"},
            {"name": "signature", "type": "bytes"}
        ],
        "name": "executeWithSessionKey",
        "outputs": [{"name": "", "type": "bytes"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # Helper to get hash for session key signing
    {
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"}
        ],
        "name": "getSessionKeyCallHash",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function"
    },
    # Nonce for replay protection
    {
        "inputs": [],
        "name": "nonce",
        "outputs": [{"name": "", "type": "uint256"}],
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
    
    def _agent_id_to_salt(self, agent_id: str) -> int:
        """Convert agent_id (UUID string) to uint256 salt for CREATE2"""
        if not agent_id:
            return 0  # Default salt for legacy accounts
        # Hash the agent_id to get a deterministic uint256
        agent_bytes = agent_id.encode('utf-8')
        hash_bytes = Web3.keccak(agent_bytes)
        return int.from_bytes(hash_bytes[:32], 'big')
    
    def get_account_for_agent(self, user_address: str, agent_id: str) -> str:
        """
        Get deterministic smart account address for a specific agent.
        Uses agent_id as CREATE2 salt for unique address per agent.
        """
        if not self.factory:
            raise ValueError("Factory not configured")
        
        user = Web3.to_checksum_address(user_address)
        salt = self._agent_id_to_salt(agent_id)
        
        try:
            # Use salt-based getAddress for unique address per agent
            return self.factory.functions.getAddress(user, salt).call()
        except Exception as e:
            logger.error(f"[SmartAccount] getAddress failed for agent: {e}")
            raise ValueError(f"Cannot get address for agent: {e}")
    
    def create_account(self, user_address: str, agent_id: str = None) -> dict:
        """
        Get counterfactual smart account address for a user/agent pair.
        
        Uses CREATE2 to calculate the address deterministically WITHOUT on-chain deployment.
        Actual deployment happens lazily on first deposit (gas-efficient pattern).
        
        Args:
            user_address: Owner wallet address
            agent_id: Unique agent ID (used as CREATE2 salt for unique address)
        
        Returns:
            {
                "success": bool,
                "account_address": str,
                "tx_hash": str (always None for counterfactual),
                "message": str
            }
        """
        if not self.factory:
            return {
                "success": False,
                "account_address": None,
                "tx_hash": None,
                "message": "Factory not configured"
            }
        
        try:
            user = Web3.to_checksum_address(user_address)
            salt = self._agent_id_to_salt(agent_id)
            
            # Get counterfactual address using CREATE2 (no gas needed!)
            predicted_address = self.factory.functions.getAddress(user, salt).call()
            
            # Check if already deployed on-chain (optional info)
            code = self.w3.eth.get_code(predicted_address)
            is_deployed = code and len(code) > 2
            
            logger.info(f"[SmartAccount] Counterfactual address for agent {agent_id[:20] if agent_id else 'default'}... → {predicted_address} (deployed: {is_deployed})")
            
            return {
                "success": True,
                "account_address": predicted_address,
                "tx_hash": None,  # No on-chain tx - counterfactual only
                "message": f"Counterfactual address generated. Actual deployment on first deposit.",
                "is_deployed_onchain": is_deployed
            }
            
        except Exception as e:
            logger.error(f"[SmartAccount] Failed to get counterfactual address: {e}")
            return {
                "success": False,
                "account_address": None,
                "tx_hash": None,
                "message": str(e)
            }
    
    def build_deploy_transaction(self, user_address: str, agent_id: str = None) -> dict:
        """
        Build unsigned transaction for user to deploy their agent smart account.
        Returns raw tx data for MetaMask - USER PAYS GAS.
        
        Args:
            user_address: Owner wallet address (will sign and pay gas)
            agent_id: Unique agent ID (used as CREATE2 salt)
        
        Returns:
            {
                "success": bool,
                "transaction": {
                    "to": factory_address,
                    "data": calldata,
                    "gas": hex_gas_estimate,
                    "value": "0x0"
                },
                "predicted_address": str,
                "message": str
            }
        """
        if not self.factory:
            return {
                "success": False,
                "transaction": None,
                "predicted_address": None,
                "message": "Factory not configured"
            }
        
        try:
            user = Web3.to_checksum_address(user_address)
            salt = self._agent_id_to_salt(agent_id)
            
            # Get predicted address first
            predicted_address = self.factory.functions.getAddress(user, salt).call()
            
            # Check if already deployed
            code = self.w3.eth.get_code(predicted_address)
            if code and len(code) > 2:
                return {
                    "success": True,
                    "transaction": None,  # No tx needed - already deployed
                    "predicted_address": predicted_address,
                    "message": "Agent already deployed on-chain",
                    "already_deployed": True
                }
            
            # Build createAccount transaction
            tx_data = self.factory.functions.createAccount(user, salt).build_transaction({
                "from": user,
                "gas": 500000,  # Will be overridden by estimate
                "value": 0,
                "chainId": 8453  # Base mainnet
            })
            
            # Estimate gas
            try:
                gas_estimate = self.w3.eth.estimate_gas({
                    "from": user,
                    "to": self.factory.address,
                    "data": tx_data["data"],
                    "value": 0
                })
                # Add 20% buffer for safety
                gas_estimate = int(gas_estimate * 1.2)
            except Exception as e:
                logger.warning(f"[SmartAccount] Gas estimation failed, using default: {e}")
                gas_estimate = 350000  # Default for createAccount
            
            logger.info(f"[SmartAccount] Built deploy tx for agent {agent_id[:20] if agent_id else 'default'}... → {predicted_address}, gas: {gas_estimate}")
            
            return {
                "success": True,
                "transaction": {
                    "to": self.factory.address,
                    "data": tx_data["data"],
                    "gas": hex(gas_estimate),
                    "value": "0x0"
                },
                "predicted_address": predicted_address,
                "message": "Transaction ready - user must sign and pay gas",
                "already_deployed": False
            }
            
        except Exception as e:
            logger.error(f"[SmartAccount] Failed to build deploy transaction: {e}")
            return {
                "success": False,
                "transaction": None,
                "predicted_address": None,
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

    def execute_with_session_key(
        self,
        smart_account: str,
        target: str,
        value: int,
        calldata: bytes,
        session_key_private: str,
        estimated_value_usd: int = 0
    ) -> dict:
        """
        Execute a call via session key signature - NO BUNDLER NEEDED!
        
        This is the new flow that allows autonomous operations without
        depending on ERC-4337 bundler. Backend signs with session key,
        then submits directly.
        
        Args:
            smart_account: The smart account address
            target: Contract to call
            value: ETH value to send
            calldata: Encoded call data
            session_key_private: Session key private key (hex)
            estimated_value_usd: Estimated USD value for limit tracking
        
        Returns:
            {success, tx_hash, message}
        """
        from eth_account.messages import encode_defunct
        
        try:
            account_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(smart_account),
                abi=ACCOUNT_ABI
            )
            
            # Get the hash that needs to be signed
            call_hash = account_contract.functions.getSessionKeyCallHash(
                Web3.to_checksum_address(target),
                value,
                calldata
            ).call()
            
            logger.info(f"[SmartAccount] Session key call hash: {call_hash.hex()}")
            
            # Sign with session key (EIP-191 personal sign)
            sk_account = Account.from_key(session_key_private)
            message = encode_defunct(call_hash)
            signature = sk_account.sign_message(message)
            
            logger.info(f"[SmartAccount] Session key signer: {sk_account.address}")
            
            # Build the transaction - anyone can submit but signature proves session key auth
            tx = account_contract.functions.executeWithSessionKey(
                Web3.to_checksum_address(target),
                value,
                calldata,
                estimated_value_usd,
                signature.signature
            ).build_transaction({
                "from": self.signer.address,  # Backend pays gas
                "nonce": self.w3.eth.get_transaction_count(self.signer.address),
                "gas": 500000,  # Will estimate
                "maxFeePerGas": self.w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": self.w3.to_wei(0.01, 'gwei'),
                "chainId": 8453
            })
            
            # Estimate gas
            try:
                estimate = self.w3.eth.estimate_gas(tx)
                tx['gas'] = int(estimate * 1.3)  # 30% buffer
            except Exception as e:
                logger.warning(f"[SmartAccount] Gas estimate failed: {e}")
            
            # Sign and send
            signed = self.signer.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            logger.info(f"[SmartAccount] Session key TX sent: {tx_hash.hex()}")
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt['status'] == 1,
                "tx_hash": tx_hash.hex(),
                "message": "Session key execution complete" if receipt['status'] == 1 else "Transaction reverted"
            }
            
        except Exception as e:
            logger.error(f"[SmartAccount] Session key execution failed: {e}")
            import traceback
            traceback.print_exc()
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
