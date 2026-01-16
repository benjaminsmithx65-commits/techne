"""
On-Chain Executor
Handles real smart contract execution for agent strategies
Integrates with TechneAgentWallet.sol on Base Mainnet
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account
from datetime import datetime
import json

# Contract ABI (simplified for key functions)
WALLET_ABI = [
    {
        "inputs": [{"name": "amount", "type": "uint256"}],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "shares", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenOut", "type": "address"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "stable", "type": "bool"}
        ],
        "name": "swapUSDCFor",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenB", "type": "address"},
            {"name": "usdcAmount", "type": "uint256"},
            {"name": "stable", "type": "bool"}
        ],
        "name": "enterLPPosition", 
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "positionIndex", "type": "uint256"}],
        "name": "exitLPPosition",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalValue",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "address"}],
        "name": "userDeposits",
        "outputs": [
            {"name": "shares", "type": "uint256"},
            {"name": "depositTime", "type": "uint256"}
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
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Token addresses on Base
TOKENS = {
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    "WETH": "0x4200000000000000000000000000000000000006",
    "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
    "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
}


class OnChainExecutor:
    """
    Executes on-chain transactions for agent strategies
    
    Security Features:
    - Gas estimation before execution
    - Transaction receipt verification
    - Error recovery tracking
    - Nonce management
    """
    
    def __init__(self):
        self.rpc_url = os.getenv(
            "ALCHEMY_RPC_URL",
            "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb"
        )
        self.wallet_address = os.getenv(
            "AGENT_WALLET_ADDRESS",
            "0x567D1Fc55459224132aB5148c6140E8900f9a607"
        )
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.wallet_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.wallet_address),
            abi=WALLET_ABI
        )
        
        # Transaction tracking
        self.pending_txs: Dict[str, Dict] = {}
        self.completed_txs: List[Dict] = []
        self.failed_txs: List[Dict] = []
        
        # Max gas price (in gwei)
        self.max_gas_price_gwei = 50
        
    def get_account(self, private_key: str) -> Account:
        """Get account from private key"""
        return Account.from_key(private_key)
    
    async def estimate_gas(self, tx: Dict) -> int:
        """Estimate gas for transaction with safety margin"""
        try:
            estimated = self.w3.eth.estimate_gas(tx)
            # Add 20% safety margin
            return int(estimated * 1.2)
        except Exception as e:
            print(f"[OnChainExecutor] Gas estimation failed: {e}")
            return 300000  # Default fallback
    
    def check_gas_price(self) -> tuple[bool, int]:
        """Check if current gas price is acceptable"""
        gas_price = self.w3.eth.gas_price
        gas_price_gwei = gas_price / 1e9
        
        is_ok = gas_price_gwei <= self.max_gas_price_gwei
        if not is_ok:
            print(f"[OnChainExecutor] Gas too high: {gas_price_gwei:.1f} gwei > {self.max_gas_price_gwei} max")
        
        return is_ok, int(gas_price)
    
    async def approve_token(
        self,
        token_address: str,
        spender: str,
        amount: int,
        private_key: str
    ) -> Optional[str]:
        """Approve token spending"""
        account = self.get_account(private_key)
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        # Check current allowance
        current_allowance = token.functions.allowance(
            account.address,
            spender
        ).call()
        
        if current_allowance >= amount:
            print(f"[OnChainExecutor] Already approved: {current_allowance}")
            return None  # No approval needed
        
        # Build approval tx
        nonce = self.w3.eth.get_transaction_count(account.address)
        gas_ok, gas_price = self.check_gas_price()
        
        if not gas_ok:
            return None
        
        tx = token.functions.approve(spender, amount).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': gas_price
        })
        
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        
        print(f"[OnChainExecutor] Approval tx sent: {tx_hash.hex()}")
        return tx_hash.hex()
    
    async def deposit_to_wallet(
        self,
        amount: int,
        private_key: str
    ) -> Optional[Dict]:
        """
        Deposit USDC to TechneAgentWallet
        
        Args:
            amount: Amount in USDC (6 decimals, e.g., 100000000 = 100 USDC)
            private_key: Agent's private key
            
        Returns:
            Transaction result dict or None if failed
        """
        account = self.get_account(private_key)
        usdc_address = TOKENS["USDC"]
        
        print(f"[OnChainExecutor] Depositing {amount / 1e6:.2f} USDC to wallet")
        
        # 1. Check gas price
        gas_ok, gas_price = self.check_gas_price()
        if not gas_ok:
            return {"success": False, "error": "Gas price too high"}
        
        # 2. Check USDC balance
        usdc = self.w3.eth.contract(
            address=Web3.to_checksum_address(usdc_address),
            abi=ERC20_ABI
        )
        balance = usdc.functions.balanceOf(account.address).call()
        
        if balance < amount:
            return {
                "success": False,
                "error": f"Insufficient USDC: {balance / 1e6:.2f} < {amount / 1e6:.2f}"
            }
        
        # 3. Approve if needed
        await self.approve_token(
            usdc_address,
            self.wallet_address,
            amount,
            private_key
        )
        
        # 4. Build deposit tx
        nonce = self.w3.eth.get_transaction_count(account.address)
        
        tx = self.wallet_contract.functions.deposit(amount).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': gas_price
        })
        
        # Estimate gas
        tx['gas'] = await self.estimate_gas(tx)
        
        # 5. Sign and send
        try:
            signed = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            print(f"[OnChainExecutor] Deposit tx sent: {tx_hash.hex()}")
            
            # Track pending
            self.pending_txs[tx_hash.hex()] = {
                "type": "deposit",
                "amount": amount,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            result = {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt.gasUsed,
                "block": receipt.blockNumber
            }
            
            # Update tracking
            del self.pending_txs[tx_hash.hex()]
            if result["success"]:
                self.completed_txs.append(result)
                print(f"[OnChainExecutor] ✓ Deposit confirmed: block {receipt.blockNumber}")
            else:
                self.failed_txs.append(result)
                print(f"[OnChainExecutor] ✗ Deposit failed")
            
            return result
            
        except ContractLogicError as e:
            return {"success": False, "error": f"Contract error: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def enter_lp_position(
        self,
        token_b: str,
        usdc_amount: int,
        stable: bool,
        private_key: str
    ) -> Optional[Dict]:
        """
        Enter LP position via TechneAgentWallet
        
        Args:
            token_b: Second token address (e.g., WETH)
            usdc_amount: Amount of USDC to use
            stable: True for stable pools, False for volatile
            private_key: Agent's private key
        """
        account = self.get_account(private_key)
        
        # Resolve token symbol to address
        if not token_b.startswith("0x"):
            token_b = TOKENS.get(token_b.upper(), token_b)
        
        print(f"[OnChainExecutor] Entering LP: {usdc_amount / 1e6:.2f} USDC + {token_b[:10]}...")
        
        gas_ok, gas_price = self.check_gas_price()
        if not gas_ok:
            return {"success": False, "error": "Gas price too high"}
        
        nonce = self.w3.eth.get_transaction_count(account.address)
        
        tx = self.wallet_contract.functions.enterLPPosition(
            Web3.to_checksum_address(token_b),
            usdc_amount,
            stable
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': gas_price
        })
        
        tx['gas'] = await self.estimate_gas(tx)
        
        try:
            signed = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            result = {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt.gasUsed,
                "type": "enter_lp"
            }
            
            if result["success"]:
                print(f"[OnChainExecutor] ✓ LP position entered")
                self.completed_txs.append(result)
            else:
                print(f"[OnChainExecutor] ✗ LP entry failed")
                self.failed_txs.append(result)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_wallet_status(self, user_address: str) -> Dict:
        """Get user's position in the wallet"""
        try:
            deposit = self.wallet_contract.functions.userDeposits(
                Web3.to_checksum_address(user_address)
            ).call()
            
            total_value = self.wallet_contract.functions.totalValue().call()
            
            return {
                "shares": deposit[0],
                "deposit_time": deposit[1],
                "total_value": total_value / 1e6,  # USDC decimals
                "pending_txs": len(self.pending_txs),
                "completed_txs": len(self.completed_txs),
                "failed_txs": len(self.failed_txs)
            }
        except Exception as e:
            return {"error": str(e)}


# Global instance
onchain_executor = OnChainExecutor()


async def execute_deposit(amount_usdc: float, private_key: str) -> Dict:
    """
    Convenience function to deposit USDC
    
    Args:
        amount_usdc: Amount in USDC (e.g., 100.0 for 100 USDC)
        private_key: Agent's private key
    """
    amount_wei = int(amount_usdc * 1e6)  # USDC has 6 decimals
    return await onchain_executor.deposit_to_wallet(amount_wei, private_key)


async def execute_lp_entry(
    token_b: str,
    usdc_amount: float,
    stable: bool,
    private_key: str
) -> Dict:
    """
    Convenience function to enter LP position
    """
    amount_wei = int(usdc_amount * 1e6)
    return await onchain_executor.enter_lp_position(token_b, amount_wei, stable, private_key)
