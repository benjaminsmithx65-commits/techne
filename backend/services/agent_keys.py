"""
Agent Key Management
Handles generation, encryption, and decryption of agent private keys
"""

import os
import secrets
import hashlib
import base64
from typing import Optional, Tuple

# Fernet encryption for private keys
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("[AgentKeys] WARNING: cryptography not installed, using fallback")

# Web3 account generation
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from web3 import Web3
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    print("[AgentKeys] WARNING: eth_account not installed")


# Master encryption key (in production: use HSM or vault)
# Generate once and store securely
MASTER_KEY = os.getenv("AGENT_ENCRYPTION_KEY")
if not MASTER_KEY:
    # Generate deterministic key from a secret (for MVP)
    secret = os.getenv("SECRET_KEY", "techne-finance-dev-key-change-in-production")
    MASTER_KEY = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


def generate_agent_wallet() -> Tuple[str, str]:
    """
    Generate a new agent wallet keypair
    
    Returns:
        Tuple of (private_key, address)
    """
    if not WEB3_AVAILABLE:
        raise RuntimeError("eth_account not available")
    
    # Generate random private key
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    
    return private_key, account.address


def encrypt_private_key(private_key: str, user_signature: Optional[str] = None) -> str:
    """
    Encrypt a private key for storage
    
    Args:
        private_key: The private key to encrypt
        user_signature: Optional user signature to mix into encryption key
        
    Returns:
        Encrypted private key as base64 string
    """
    if not CRYPTO_AVAILABLE:
        # Fallback: simple XOR (NOT SECURE - dev only!)
        return _fallback_encrypt(private_key)
    
    # Derive encryption key
    if user_signature:
        # Mix user signature into key for additional security
        combined = MASTER_KEY + user_signature.encode()[:32]
        key = base64.urlsafe_b64encode(hashlib.sha256(combined).digest())
    else:
        key = MASTER_KEY
    
    fernet = Fernet(key)
    encrypted = fernet.encrypt(private_key.encode())
    
    return encrypted.decode()


def decrypt_private_key(encrypted_key: str, user_signature: Optional[str] = None) -> str:
    """
    Decrypt a stored private key
    
    Args:
        encrypted_key: The encrypted private key
        user_signature: Optional user signature (must match encryption)
        
    Returns:
        Decrypted private key
    """
    if not CRYPTO_AVAILABLE:
        return _fallback_decrypt(encrypted_key)
    
    # Derive decryption key
    if user_signature:
        combined = MASTER_KEY + user_signature.encode()[:32]
        key = base64.urlsafe_b64encode(hashlib.sha256(combined).digest())
    else:
        key = MASTER_KEY
    
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_key.encode())
    
    return decrypted.decode()


def verify_signature(message: str, signature: str, expected_address: str) -> bool:
    """
    Verify that a signature was created by the expected address
    
    Args:
        message: The original message that was signed
        signature: The signature (hex string with 0x prefix)
        expected_address: The address that should have signed
        
    Returns:
        True if signature is valid and from expected address
    """
    if not WEB3_AVAILABLE:
        print("[AgentKeys] WARNING: Cannot verify signature without web3")
        return True  # Skip verification in dev
    
    try:
        # Encode message for personal_sign
        message_encoded = encode_defunct(text=message)
        
        # Recover signer address
        recovered = Account.recover_message(message_encoded, signature=signature)
        
        # Compare (case-insensitive)
        return recovered.lower() == expected_address.lower()
        
    except Exception as e:
        print(f"[AgentKeys] Signature verification failed: {e}")
        return False


def _fallback_encrypt(data: str) -> str:
    """Simple XOR encryption fallback (NOT SECURE)"""
    key = hashlib.sha256(str(MASTER_KEY).encode()).digest()
    encrypted = bytes([ord(c) ^ key[i % len(key)] for i, c in enumerate(data)])
    return base64.b64encode(encrypted).decode()


def _fallback_decrypt(data: str) -> str:
    """Simple XOR decryption fallback (NOT SECURE)"""
    key = hashlib.sha256(str(MASTER_KEY).encode()).digest()
    encrypted = base64.b64decode(data)
    decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(encrypted)])
    return decrypted.decode()


# Test
if __name__ == "__main__":
    pk, addr = generate_agent_wallet()
    print(f"Generated: {addr}")
    
    encrypted = encrypt_private_key(pk)
    print(f"Encrypted: {encrypted[:50]}...")
    
    decrypted = decrypt_private_key(encrypted)
    print(f"Match: {pk == decrypted}")
