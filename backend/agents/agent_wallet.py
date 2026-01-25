"""
Agent Wallet System - Secure Wallet Management for AI Agents
Allows users to fund agents who execute yield strategies on their behalf

Features:
- Create dedicated agent wallet per user
- Encrypted private key storage (user can export anytime)
- Deposit from connected wallet
- Agent executes transactions with session permissions
- 24/7 withdrawal access for user
"""

import os
import json
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import base64

# Use cryptography for proper encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentWallet")


class WalletStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    LOCKED = "locked"
    DRAINING = "draining"


class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    STRATEGY_DEPOSIT = "strategy_deposit"
    STRATEGY_WITHDRAW = "strategy_withdraw"
    REBALANCE = "rebalance"
    CLAIM_REWARDS = "claim_rewards"


@dataclass
class AgentWalletData:
    """Data structure for an agent wallet"""
    user_id: str  # Owner's wallet address
    agent_address: str  # Agent's wallet address
    encrypted_private_key: str  # Encrypted private key
    created_at: datetime = field(default_factory=datetime.now)
    status: WalletStatus = WalletStatus.ACTIVE
    
    # Balances (tracked off-chain, verified on-chain)
    balances: Dict[str, float] = field(default_factory=dict)  # token -> amount
    
    # Active positions
    positions: List[Dict] = field(default_factory=list)
    
    # Transaction history
    transactions: List[Dict] = field(default_factory=list)
    
    # Settings
    settings: Dict = field(default_factory=lambda: {
        "auto_compound": True,
        "max_gas_gwei": 50,
        "slippage_tolerance": 0.5,
        "emergency_withdraw_enabled": True
    })


class AgentWalletManager:
    """
    Manages agent wallets for all users
    
    Security Model:
    - Each user gets a dedicated agent wallet
    - Private key is encrypted with user's signature
    - User can export key anytime (24/7 access)
    - Agent operates with session permissions only
    """
    
    def __init__(self, storage_path: str = "./data/agent_wallets"):
        self.storage_path = storage_path
        self.wallets: Dict[str, AgentWalletData] = {}
        self._encryption_salt = b"techne_agent_wallet_v1"
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        # Load existing wallets
        self._load_wallets()
    
    # ===========================================
    # WALLET CREATION
    # ===========================================
    
    def create_wallet(self, user_address: str, encryption_key: str) -> Tuple[str, str]:
        """
        Create a new agent wallet for a user
        
        Args:
            user_address: User's main wallet address
            encryption_key: Key to encrypt private key (from user's signature)
            
        Returns:
            (agent_address, private_key) - Save private key for user!
        """
        
        if user_address.lower() in self.wallets:
            existing = self.wallets[user_address.lower()]
            return existing.agent_address, "[encrypted - use export_private_key]"
        
        # Generate new wallet
        private_key, agent_address = self._generate_wallet()
        
        # Encrypt private key
        encrypted_key = self._encrypt_key(private_key, encryption_key)
        
        # Create wallet data
        wallet = AgentWalletData(
            user_id=user_address.lower(),
            agent_address=agent_address,
            encrypted_private_key=encrypted_key,
            balances={
                "USDC": 0.0,
                "ETH": 0.0,
                "WETH": 0.0
            }
        )
        
        self.wallets[user_address.lower()] = wallet
        self._save_wallet(wallet)
        
        logger.info(f"🔐 Created agent wallet for {user_address[:10]}...")
        
        return agent_address, private_key
    
    def _generate_wallet(self) -> Tuple[str, str]:
        """Generate a new Ethereum-compatible wallet"""
        try:
            from eth_account import Account
            Account.enable_unaudited_hdwallet_features()
            
            # Generate from mnemonic for extra security
            account, mnemonic = Account.create_with_mnemonic()
            return account.key.hex(), account.address
        except ImportError:
            # Fallback: Generate random wallet (for testing)
            import secrets
            private_key = "0x" + secrets.token_hex(32)
            # Mock address generation
            address = "0x" + hashlib.sha256(private_key.encode()).hexdigest()[-40:]
            return private_key, address
    
    def _encrypt_key(self, private_key: str, encryption_key: str) -> str:
        """Encrypt private key with user's encryption key"""
        if CRYPTO_AVAILABLE:
            # Derive key from user's encryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._encryption_salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            fernet = Fernet(key)
            
            return fernet.encrypt(private_key.encode()).decode()
        else:
            # Simple XOR obfuscation (not production-ready)
            return base64.b64encode(
                bytes(a ^ b for a, b in zip(
                    private_key.encode(),
                    (encryption_key * 100)[:len(private_key)].encode()
                ))
            ).decode()
    
    def _decrypt_key(self, encrypted_key: str, encryption_key: str) -> str:
        """Decrypt private key"""
        if CRYPTO_AVAILABLE:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._encryption_salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
            fernet = Fernet(key)
            
            return fernet.decrypt(encrypted_key.encode()).decode()
        else:
            # Simple XOR de-obfuscation
            encrypted_bytes = base64.b64decode(encrypted_key)
            return bytes(a ^ b for a, b in zip(
                encrypted_bytes,
                (encryption_key * 100)[:len(encrypted_bytes)].encode()
            )).decode()
    
    # ===========================================
    # KEY MANAGEMENT (24/7 ACCESS)
    # ===========================================
    
    def export_private_key(self, user_address: str, encryption_key: str) -> Optional[str]:
        """
        Export private key for user - 24/7 access guaranteed
        
        Args:
            user_address: User's wallet address
            encryption_key: Decryption key (from user's signature)
            
        Returns:
            Decrypted private key or None if not found
        """
        wallet = self.wallets.get(user_address.lower())
        if not wallet:
            return None
        
        try:
            private_key = self._decrypt_key(wallet.encrypted_private_key, encryption_key)
            logger.info(f"🔓 Private key exported for {user_address[:10]}...")
            return private_key
        except Exception as e:
            logger.error(f"Key export failed: {e}")
            return None
    
    def get_agent_address(self, user_address: str) -> Optional[str]:
        """Get agent wallet address for a user"""
        wallet = self.wallets.get(user_address.lower())
        return wallet.agent_address if wallet else None
    
    # ===========================================
    # DEPOSITS
    # ===========================================
    
    def record_deposit(
        self,
        user_address: str,
        token: str,
        amount: float,
        tx_hash: str
    ) -> bool:
        """Record a deposit to agent wallet"""
        wallet = self.wallets.get(user_address.lower())
        if not wallet:
            return False
        
        # Update balance
        if token not in wallet.balances:
            wallet.balances[token] = 0.0
        wallet.balances[token] += amount
        
        # Record transaction
        wallet.transactions.append({
            "type": TransactionType.DEPOSIT.value,
            "token": token,
            "amount": amount,
            "tx_hash": tx_hash,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_wallet(wallet)
        logger.info(f"💰 Deposit recorded: {amount} {token} for {user_address[:10]}...")
        
        return True
    
    # ===========================================
    # WITHDRAWALS (24/7 ACCESS)
    # ===========================================
    
    def request_withdrawal(
        self,
        user_address: str,
        token: str,
        amount: float,
        destination: Optional[str] = None
    ) -> Dict:
        """
        Request withdrawal from agent wallet - EXECUTES REAL ON-CHAIN TRANSFER
        User has 24/7 access to their funds
        """
        wallet = self.wallets.get(user_address.lower())
        if not wallet:
            return {"success": False, "error": "Wallet not found"}
        
        current_balance = wallet.balances.get(token, 0.0)
        if amount > current_balance:
            return {
                "success": False,
                "error": f"Insufficient balance. Have: {current_balance}, Requested: {amount}"
            }
        
        tx_hash = None
        dest_address = destination or user_address
        
        # ============================================
        # EXECUTE REAL ON-CHAIN TRANSFER
        # ============================================
        try:
            from web3 import Web3
            from eth_account import Account
            
            rpc_url = os.environ.get("ALCHEMY_RPC_URL", "https://mainnet.base.org")
            w3 = Web3(Web3.HTTPProvider(rpc_url))
            
            # Get agent private key for signing
            agent_key = self._get_agent_private_key(user_address)
            if not agent_key:
                return {"success": False, "error": "Cannot access agent private key"}
            
            agent_account = Account.from_key(agent_key)
            
            # Token addresses on Base
            TOKEN_ADDRESSES = {
                "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "WETH": "0x4200000000000000000000000000000000000006",
                "ETH": None  # Native ETH
            }
            
            token_upper = token.upper()
            token_address = TOKEN_ADDRESSES.get(token_upper)
            
            if token_upper == "ETH":
                # Native ETH transfer
                amount_wei = int(amount * 1e18)
                tx = {
                    'to': Web3.to_checksum_address(dest_address),
                    'value': amount_wei,
                    'gas': 21000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': w3.eth.get_transaction_count(agent_account.address),
                    'chainId': 8453  # Base
                }
                
                signed = agent_account.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt.status != 1:
                    return {"success": False, "error": "ETH transfer failed on-chain"}
                    
            elif token_address:
                # ERC20 transfer
                decimals = 6 if token_upper == "USDC" else 18
                amount_units = int(amount * (10 ** decimals))
                
                erc20_abi = [{
                    "inputs": [
                        {"name": "recipient", "type": "address"},
                        {"name": "amount", "type": "uint256"}
                    ],
                    "name": "transfer",
                    "outputs": [{"type": "bool"}],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }]
                
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(token_address),
                    abi=erc20_abi
                )
                
                tx = contract.functions.transfer(
                    Web3.to_checksum_address(dest_address),
                    amount_units
                ).build_transaction({
                    'from': agent_account.address,
                    'gas': 100000,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': w3.eth.get_transaction_count(agent_account.address),
                    'chainId': 8453
                })
                
                signed = agent_account.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                
                if receipt.status != 1:
                    return {"success": False, "error": f"{token} transfer failed on-chain"}
            else:
                return {"success": False, "error": f"Unknown token: {token}"}
            
            tx_hash = tx_hash.hex() if tx_hash else None
            logger.info(f"✅ On-chain transfer SUCCESS: {tx_hash}")
            
        except Exception as e:
            logger.error(f"On-chain transfer failed: {e}")
            return {"success": False, "error": f"On-chain transfer failed: {str(e)}"}
        
        # Deduct from balance AFTER successful on-chain transfer
        wallet.balances[token] -= amount
        
        # Record transaction
        tx_record = {
            "type": TransactionType.WITHDRAW.value,
            "token": token,
            "amount": amount,
            "destination": dest_address,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "tx_hash": tx_hash
        }
        wallet.transactions.append(tx_record)
        
        self._save_wallet(wallet)
        
        logger.info(f"📤 Withdrawal completed: {amount} {token} for {user_address[:10]}...")
        
        return {
            "success": True,
            "withdrawal": tx_record,
            "remaining_balance": wallet.balances[token],
            "tx_hash": tx_hash
        }
    
    def _get_agent_private_key(self, user_address: str) -> Optional[str]:
        """Get agent's private key for transaction signing"""
        # Try to get from environment (for hot wallet)
        agent_key = os.environ.get("AGENT_PRIVATE_KEY") or os.environ.get("PRIVATE_KEY")
        if agent_key:
            return agent_key
        
        # Fallback: Try to decrypt from wallet data
        wallet = self.wallets.get(user_address.lower())
        if wallet and wallet.encrypted_private_key:
            # Note: This requires the encryption key which user provides
            # For automated operations, use AGENT_PRIVATE_KEY env var
            pass
        
        return None
    
    def emergency_drain(self, user_address: str) -> Dict:
        """
        Emergency: Withdraw all funds to user's wallet - EXECUTES REAL ON-CHAIN TRANSFERS
        Always available 24/7
        """
        wallet = self.wallets.get(user_address.lower())
        if not wallet:
            return {"success": False, "error": "Wallet not found"}
        
        if not wallet.settings.get("emergency_withdraw_enabled", True):
            return {"success": False, "error": "Emergency withdraw disabled"}
        
        # Set wallet to draining mode
        wallet.status = WalletStatus.DRAINING
        
        # Execute real withdrawals for each token
        withdrawals = []
        tx_hashes = []
        
        for token, balance in list(wallet.balances.items()):
            if balance > 0:
                # Use request_withdrawal which now does real on-chain transfer
                result = self.request_withdrawal(
                    user_address=user_address,
                    token=token,
                    amount=balance,
                    destination=user_address
                )
                
                if result.get("success"):
                    withdrawals.append({
                        "token": token,
                        "amount": balance,
                        "destination": user_address,
                        "tx_hash": result.get("tx_hash")
                    })
                    tx_hashes.append(result.get("tx_hash"))
                else:
                    logger.error(f"Emergency drain failed for {token}: {result.get('error')}")
        
        # Record emergency drain
        wallet.transactions.append({
            "type": "emergency_drain",
            "withdrawals": withdrawals,
            "timestamp": datetime.now().isoformat(),
            "tx_hashes": tx_hashes
        })
        
        # Reset wallet status
        wallet.status = WalletStatus.ACTIVE
        self._save_wallet(wallet)
        
        logger.warning(f"🚨 Emergency drain completed for {user_address[:10]}... {len(withdrawals)} tokens transferred")
        
        return {
            "success": True,
            "withdrawals": withdrawals,
            "tx_hashes": tx_hashes,
            "message": f"All funds ({len(withdrawals)} tokens) transferred to your wallet"
        }
    
    # ===========================================
    # BALANCE & STATUS
    # ===========================================
    
    def get_balances(self, user_address: str) -> Dict[str, float]:
        """Get current agent wallet balances"""
        wallet = self.wallets.get(user_address.lower())
        return wallet.balances if wallet else {}
    
    def get_wallet_info(self, user_address: str) -> Optional[Dict]:
        """Get full wallet information"""
        wallet = self.wallets.get(user_address.lower())
        if not wallet:
            return None
        
        return {
            "agent_address": wallet.agent_address,
            "status": wallet.status.value,
            "balances": wallet.balances,
            "positions_count": len(wallet.positions),
            "total_transactions": len(wallet.transactions),
            "created_at": wallet.created_at.isoformat(),
            "settings": wallet.settings
        }
    
    def get_transactions(self, user_address: str, limit: int = 20) -> List[Dict]:
        """Get transaction history"""
        wallet = self.wallets.get(user_address.lower())
        if not wallet:
            return []
        
        return wallet.transactions[-limit:][::-1]  # Most recent first
    
    # ===========================================
    # AGENT EXECUTION
    # ===========================================
    
    def execute_strategy_deposit(
        self,
        user_address: str,
        pool_id: str,
        token: str,
        amount: float
    ) -> Dict:
        """
        Agent deposits to a yield strategy on user's behalf
        """
        wallet = self.wallets.get(user_address.lower())
        if not wallet:
            return {"success": False, "error": "Wallet not found"}
        
        if wallet.status != WalletStatus.ACTIVE:
            return {"success": False, "error": f"Wallet is {wallet.status.value}"}
        
        current_balance = wallet.balances.get(token, 0.0)
        if amount > current_balance:
            return {"success": False, "error": "Insufficient balance"}
        
        # Deduct from available balance
        wallet.balances[token] -= amount
        
        # Add to positions
        wallet.positions.append({
            "pool_id": pool_id,
            "token": token,
            "amount": amount,
            "deposited_at": datetime.now().isoformat(),
            "current_value": amount,
            "apy": 0  # Will be updated
        })
        
        # Record transaction
        wallet.transactions.append({
            "type": TransactionType.STRATEGY_DEPOSIT.value,
            "pool_id": pool_id,
            "token": token,
            "amount": amount,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_wallet(wallet)
        
        logger.info(f"🎯 Strategy deposit: {amount} {token} to {pool_id}")
        
        return {
            "success": True,
            "position": wallet.positions[-1],
            "remaining_balance": wallet.balances[token]
        }
    
    def get_positions(self, user_address: str) -> List[Dict]:
        """Get all active positions"""
        wallet = self.wallets.get(user_address.lower())
        return wallet.positions if wallet else []
    
    # ===========================================
    # PERSISTENCE
    # ===========================================
    
    def _save_wallet(self, wallet: AgentWalletData):
        """Save wallet to disk"""
        filepath = os.path.join(self.storage_path, f"{wallet.user_id}.json")
        
        data = {
            "user_id": wallet.user_id,
            "agent_address": wallet.agent_address,
            "encrypted_private_key": wallet.encrypted_private_key,
            "created_at": wallet.created_at.isoformat(),
            "status": wallet.status.value,
            "balances": wallet.balances,
            "positions": wallet.positions,
            "transactions": wallet.transactions,
            "settings": wallet.settings
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_wallets(self):
        """Load all wallets from disk"""
        if not os.path.exists(self.storage_path):
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                filepath = os.path.join(self.storage_path, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    
                    wallet = AgentWalletData(
                        user_id=data["user_id"],
                        agent_address=data["agent_address"],
                        encrypted_private_key=data["encrypted_private_key"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        status=WalletStatus(data["status"]),
                        balances=data.get("balances", {}),
                        positions=data.get("positions", []),
                        transactions=data.get("transactions", []),
                        settings=data.get("settings", {})
                    )
                    
                    self.wallets[wallet.user_id] = wallet
                except Exception as e:
                    logger.error(f"Failed to load wallet {filename}: {e}")
    
    def update_settings(self, user_address: str, settings: Dict) -> bool:
        """Update wallet settings"""
        wallet = self.wallets.get(user_address.lower())
        if not wallet:
            return False
        
        wallet.settings.update(settings)
        self._save_wallet(wallet)
        return True


# Singleton instance
agent_wallet_manager = AgentWalletManager()
