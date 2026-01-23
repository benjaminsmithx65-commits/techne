"""
Session Key Signer for Smart Account Agent Architecture

Manages session keys securely:
- Keys are derived deterministically from master secret
- Never stored in plain text in database
- Limited permissions enforced by on-chain contract
"""

import os
import hashlib
import secrets
from typing import Optional, Tuple
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

# ============================================
# CONFIGURATION
# ============================================

# Master secret for key derivation (from env var, never hardcoded)
MASTER_SECRET = os.getenv("SESSION_KEY_MASTER_SECRET", "")

# Factory address on Base mainnet
FACTORY_ADDRESS = "0x33f5e2F6d194869ACc60C965C2A24eDC5de8a216"

# Key derivation parameters
KEY_DERIVATION_SALT = b"techne_session_key_v1"

# ============================================
# SESSION KEY DERIVATION
# ============================================

def derive_session_key(agent_id: str, user_address: str) -> Tuple[str, str]:
    """
    Derive a deterministic session key for an agent.
    
    Uses HKDF-like derivation from master secret + agent info.
    This allows us to regenerate keys without storing them.
    
    Returns: (private_key_hex, address)
    """
    if not MASTER_SECRET:
        raise ValueError("SESSION_KEY_MASTER_SECRET not set")
    
    # Create deterministic seed from master + agent info
    seed_input = f"{MASTER_SECRET}:{agent_id}:{user_address.lower()}".encode()
    seed = hashlib.pbkdf2_hmac(
        'sha256',
        seed_input,
        KEY_DERIVATION_SALT,
        iterations=100000,
        dklen=32
    )
    
    # Create account from seed
    account = Account.from_key(seed)
    return seed.hex(), account.address


def get_session_key_address(agent_id: str, user_address: str) -> str:
    """Get the session key address for an agent (without exposing private key)."""
    _, address = derive_session_key(agent_id, user_address)
    return address


# ============================================
# SIGNING FOR ERC-4337
# ============================================

class SessionKeySigner:
    """
    Signer for creating UserOperation signatures.
    
    Used by backend to sign transactions that will be
    executed via the Smart Account's session key mechanism.
    """
    
    def __init__(self, agent_id: str, user_address: str):
        self.agent_id = agent_id
        self.user_address = user_address
        self._private_key, self.address = derive_session_key(agent_id, user_address)
        self._account = Account.from_key(bytes.fromhex(self._private_key))
    
    def sign_user_op_hash(self, user_op_hash: bytes) -> bytes:
        """Sign a UserOperation hash for ERC-4337."""
        message = encode_defunct(user_op_hash)
        signed = self._account.sign_message(message)
        return signed.signature
    
    def sign_message(self, message: bytes) -> bytes:
        """Sign an arbitrary message."""
        msg = encode_defunct(message)
        signed = self._account.sign_message(msg)
        return signed.signature
    
    def get_packed_signature(self, user_op_hash: bytes) -> str:
        """Get signature in packed hex format for bundler."""
        sig = self.sign_user_op_hash(user_op_hash)
        return "0x" + sig.hex()


# ============================================
# SMART ACCOUNT INTERACTION
# ============================================

class SmartAccountExecutor:
    """
    Executor for Smart Account transactions.
    
    Handles:
    - Creating UserOperations
    - Submitting to bundler
    - Waiting for execution
    """
    
    def __init__(self, signer: SessionKeySigner, smart_account_address: str, w3: Web3):
        self.signer = signer
        self.smart_account_address = smart_account_address
        self.w3 = w3
        
        # EntryPoint v0.7 on Base
        self.entrypoint = "0x0000000071727De22E5E9d8BAf0edAc6f37da032"
        
        # Bundler URL (Pimlico)
        self.bundler_url = os.getenv("PIMLICO_BUNDLER_URL", "")
    
    def create_user_operation(
        self,
        target: str,
        value: int,
        data: bytes,
        estimated_value_usd: int = 0
    ) -> dict:
        """
        Create a UserOperation for session key execution.
        
        The call will go through executeAsSessionKey on the Smart Account.
        """
        # Encode call to executeAsSessionKey
        execute_calldata = self._encode_execute_call(
            self.signer.address,  # session key
            target,
            value,
            data,
            estimated_value_usd
        )
        
        # Build UserOperation
        user_op = {
            "sender": self.smart_account_address,
            "nonce": self._get_nonce(),
            "callData": execute_calldata.hex(),
            "callGasLimit": "0x50000",
            "verificationGasLimit": "0x20000",
            "preVerificationGas": "0x10000",
            "maxFeePerGas": self._get_gas_price(),
            "maxPriorityFeePerGas": "0x1",
            "paymasterAndData": "0x",  # No paymaster - user pays gas
            "signature": "0x"  # Will be filled after hash
        }
        
        # Calculate UserOp hash and sign
        user_op_hash = self._hash_user_operation(user_op)
        user_op["signature"] = self.signer.get_packed_signature(user_op_hash)
        
        return user_op
    
    async def send_user_operation(self, user_op: dict) -> str:
        """
        Send UserOperation to bundler and return hash.
        
        Returns the UserOperation hash for tracking.
        """
        if not self.bundler_url:
            raise ValueError("PIMLICO_BUNDLER_URL not configured")
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_sendUserOperation",
                "params": [user_op, self.entrypoint]
            }
            
            async with session.post(self.bundler_url, json=payload) as resp:
                result = await resp.json()
                if "error" in result:
                    raise Exception(f"Bundler error: {result['error']}")
                return result["result"]
    
    def _encode_execute_call(
        self,
        session_key: str,
        target: str,
        value: int,
        data: bytes,
        estimated_value_usd: int
    ) -> bytes:
        """Encode call to executeAsSessionKey."""
        # Function selector for executeAsSessionKey(address,address,uint256,bytes,uint256)
        selector = bytes.fromhex("a7c9d72a")  # TODO: Calculate actual selector
        
        # ABI encode parameters
        from eth_abi import encode
        params = encode(
            ['address', 'address', 'uint256', 'bytes', 'uint256'],
            [session_key, target, value, data, estimated_value_usd]
        )
        
        return selector + params
    
    def _get_nonce(self) -> str:
        """Get the next nonce for the Smart Account."""
        # Query from EntryPoint.getNonce(sender, key)
        # For simplicity, using key=0
        return "0x0"  # TODO: Implement proper nonce tracking
    
    def _get_gas_price(self) -> str:
        """Get current gas price."""
        gas_price = self.w3.eth.gas_price
        return hex(gas_price)
    
    def _hash_user_operation(self, user_op: dict) -> bytes:
        """Calculate the hash of a UserOperation."""
        # Simplified - proper implementation needs full ERC-4337 hashing
        from eth_abi import encode
        
        packed = encode(
            ['address', 'uint256', 'bytes32', 'bytes32', 'uint256', 'uint256', 'uint256', 'uint256', 'uint256', 'bytes32'],
            [
                user_op["sender"],
                int(user_op["nonce"], 16),
                self.w3.keccak(bytes.fromhex(user_op.get("initCode", "")[2:] or "00")),
                self.w3.keccak(bytes.fromhex(user_op["callData"])),
                int(user_op["callGasLimit"], 16),
                int(user_op["verificationGasLimit"], 16),
                int(user_op["preVerificationGas"], 16),
                int(user_op["maxFeePerGas"], 16),
                int(user_op["maxPriorityFeePerGas"], 16),
                self.w3.keccak(bytes.fromhex(user_op.get("paymasterAndData", "")[2:] or "00"))
            ]
        )
        
        inner_hash = self.w3.keccak(packed)
        
        # Pack with entrypoint and chainId
        chain_id = 8453  # Base mainnet
        final = encode(['bytes32', 'address', 'uint256'], [inner_hash, self.entrypoint, chain_id])
        
        return self.w3.keccak(final)


# ============================================
# HELPER FUNCTIONS
# ============================================

def verify_session_key_registered(
    w3: Web3,
    smart_account: str,
    session_key: str
) -> bool:
    """Check if a session key is registered and active for a Smart Account."""
    # ABI for getSessionKeyInfo(address)
    abi = [{
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
    }]
    
    contract = w3.eth.contract(address=smart_account, abi=abi)
    try:
        active, valid_until, _, _ = contract.functions.getSessionKeyInfo(session_key).call()
        import time
        return active and valid_until > time.time()
    except Exception:
        return False
