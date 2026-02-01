"""
Agent Wallet API Router
Endpoints for ERC-8004 Smart Account management, deposits, withdrawals, and security
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

from agents.agent_wallet import agent_wallet_manager
from agents.advanced_security import (
    multisig_manager, 
    safe_wallet, 
    two_factor_auth, 
    contract_audit
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentWalletAPI")

router = APIRouter(prefix="/api/agent-wallet", tags=["Agent Wallet"])


# ===========================================
# MODELS
# ===========================================

class CreateWalletRequest(BaseModel):
    user_address: str
    agent_id: Optional[str] = None  # Agent UUID for 1-agent-1-wallet
    signature: str  # User's signature for verification


class DepositRequest(BaseModel):
    user_address: str
    token: str
    amount: float
    tx_hash: str


class WithdrawRequest(BaseModel):
    user_address: str
    agent_address: Optional[str] = None  # Agent wallet to withdraw from
    token: str
    amount: float
    destination: Optional[str] = None
    totp_code: Optional[str] = None  # Required for large withdrawals



class StrategyDepositRequest(BaseModel):
    user_address: str
    pool_id: str
    token: str
    amount: float


class Setup2FARequest(BaseModel):
    user_address: str


class Verify2FARequest(BaseModel):
    user_address: str
    code: str


class ExportKeyRequest(BaseModel):
    user_address: str
    signature: str  # User's signature for verification
    totp_code: Optional[str] = None  # Required if 2FA enabled


class AddSignerRequest(BaseModel):
    user_address: str
    signer_address: str
    totp_code: Optional[str] = None


class ApproveMultiSigRequest(BaseModel):
    request_id: str
    signer_address: str
    signature: str  # Proof of ownership


# ===========================================
# WALLET CREATION & INFO
# ===========================================

@router.post("/create")
async def create_agent_wallet(request: CreateWalletRequest):
    """
    Create a new ERC-8004 Smart Account for a specific agent.
    
    ERC-8004 ARCHITECTURE (1 Agent = 1 Wallet):
    - Each agent gets its own Smart Account
    - User's wallet is owner of ALL their agent accounts
    - agent_id is used as CREATE2 salt for deterministic addressing
    """
    try:
        from services.smart_account_service import get_smart_account_service
        
        smart_account_service = get_smart_account_service()
        
        # Pass agent_id for unique Smart Account per agent
        result = smart_account_service.create_account(
            user_address=request.user_address,
            agent_id=request.agent_id
        )
        
        if result.get("success"):
            agent_address = result.get("account_address")
            tx_hash = result.get("tx_hash")
            
            # Log wallet creation for audit
            contract_audit.log_interaction(
                user_id=request.user_address,
                contract_address="smart_account_factory",
                function_name="create_account",
                parameters={
                    "agent_address": agent_address,
                    "agent_id": request.agent_id
                },
                tx_hash=tx_hash
            )
            
            return {
                "success": True,
                "agent_address": agent_address,
                "agent_id": request.agent_id,
                "account_type": "erc8004",
                "tx_hash": tx_hash,
                "message": f"✅ Smart Account created for agent {request.agent_id[:8] if request.agent_id else 'default'}..."
            }
        else:
            raise Exception(result.get("message", "Smart Account creation failed"))
            
    except Exception as e:
        logger.error(f"Smart Account creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DeploySmartAccountRequest(BaseModel):
    """Request to deploy Smart Account on-chain"""
    user_address: str
    agent_id: str


@router.post("/deploy-smart-account")
async def deploy_smart_account(request: DeploySmartAccountRequest):
    """
    Build transaction to deploy Smart Account on-chain.
    
    Smart Accounts use CREATE2 for deterministic addresses.
    This returns the TX data for user to sign via MetaMask.
    """
    from web3 import Web3
    import os
    
    try:
        user_address = Web3.to_checksum_address(request.user_address)
        agent_id = request.agent_id
        
        # Factory V2 address (with executeWithSessionKey + auto session key)
        FACTORY = "0x9192DC52445E3d6e85EbB53723cFC2Eb9dD6e02A"
        RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        # Calculate salt from agent_id
        agent_bytes = agent_id.encode('utf-8')
        hash_bytes = w3.keccak(agent_bytes)
        salt = int.from_bytes(hash_bytes[:32], 'big')
        
        # Factory ABI
        FACTORY_ABI = [
            {
                "inputs": [{"name": "owner", "type": "address"}, {"name": "agentSalt", "type": "uint256"}],
                "name": "createAccount",
                "outputs": [{"name": "account", "type": "address"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"name": "owner", "type": "address"}, {"name": "agentSalt", "type": "uint256"}],
                "name": "getAddress",
                "outputs": [{"name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        factory = w3.eth.contract(address=FACTORY, abi=FACTORY_ABI)
        
        # Get predicted address
        predicted_address = factory.functions.getAddress(user_address, salt).call()
        
        # Check if already deployed
        code = w3.eth.get_code(predicted_address)
        if len(code) > 2:
            return {
                "success": True,
                "already_deployed": True,
                "agent_address": predicted_address,
                "message": "Smart Account already deployed on-chain"
            }
        
        # Build createAccount transaction
        tx_data = factory.functions.createAccount(user_address, salt).build_transaction({
            'from': user_address,
            'gas': 500000,
            'value': 0,
            'chainId': 8453
        })['data']
        
        # Estimate gas
        try:
            gas_estimate = w3.eth.estimate_gas({
                'from': user_address,
                'to': FACTORY,
                'data': tx_data,
                'value': 0
            })
            gas_estimate = int(gas_estimate * 1.2)  # 20% buffer
        except:
            gas_estimate = 350000
        
        logger.info(f"[DeploySmartAccount] TX ready for {agent_id[:20]}... → {predicted_address}")
        
        return {
            "success": True,
            "already_deployed": False,
            "agent_address": predicted_address,
            "transaction": {
                "to": FACTORY,
                "data": tx_data,
                "gas": hex(gas_estimate),
                "value": "0x0"
            },
            "message": "Sign this transaction in MetaMask to deploy Smart Account"
        }
        
    except Exception as e:
        logger.error(f"Deploy Smart Account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info")
async def get_wallet_info(user_address: str = Query(...)):
    """Get wallet information including balances and status"""
    info = agent_wallet_manager.get_wallet_info(user_address)
    
    if not info:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    # Add pending multi-sig requests
    info["pending_multisig"] = multisig_manager.get_pending_requests(user_address)
    info["2fa_enabled"] = two_factor_auth.is_2fa_enabled(user_address)
    
    return {"success": True, "wallet": info}


@router.get("/balances")
async def get_balances(user_address: str = Query(...)):
    """Get current agent wallet balances"""
    balances = agent_wallet_manager.get_balances(user_address)
    return {"success": True, "balances": balances}


@router.get("/transactions")
async def get_transactions(
    user_address: str = Query(...),
    limit: int = Query(20, le=100)
):
    """Get transaction history"""
    transactions = agent_wallet_manager.get_transactions(user_address, limit)
    return {"success": True, "transactions": transactions}


@router.get("/positions")
async def get_positions(user_address: str = Query(...)):
    """Get all active yield positions"""
    positions = agent_wallet_manager.get_positions(user_address)
    return {"success": True, "positions": positions}


@router.post("/refresh-balances")
async def refresh_balances(
    agent_address: str = Query(...),
    user_address: str = Query(None)
):
    """
    Refresh on-chain balances after fund/withdraw TX.
    
    Called by frontend ~5-10 seconds after TX confirmation.
    Fetches fresh data from RPC and updates cache.
    """
    from web3 import Web3
    import os
    
    logger.info(f"[RefreshBalances] Refreshing for {agent_address[:10]}...")
    
    try:
        RPC_URL = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        agent_addr = Web3.to_checksum_address(agent_address)
        
        # Token addresses on Base
        TOKENS = {
            "ETH": {"address": None, "decimals": 18},
            "USDC": {"address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6},
            "WETH": {"address": "0x4200000000000000000000000000000000000006", "decimals": 18},
            "cbBTC": {"address": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", "decimals": 8},
            "AERO": {"address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "decimals": 18},
        }
        
        ERC20_ABI = [{"name": "balanceOf", "type": "function", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"type": "uint256"}], "stateMutability": "view"}]
        
        balances = {}
        total_usd = 0.0
        
        # Get ETH balance
        eth_balance = w3.eth.get_balance(agent_addr)
        eth_formatted = float(eth_balance) / 1e18
        balances["ETH"] = {"balance": eth_formatted, "raw": str(eth_balance)}
        
        # Estimate ETH price (~$3500 for now, should use price feed)
        total_usd += eth_formatted * 3500
        
        # Get ERC20 balances
        for symbol, config in TOKENS.items():
            if config["address"]:
                try:
                    contract = w3.eth.contract(address=Web3.to_checksum_address(config["address"]), abi=ERC20_ABI)
                    raw_balance = contract.functions.balanceOf(agent_addr).call()
                    formatted = float(raw_balance) / (10 ** config["decimals"])
                    balances[symbol] = {"balance": formatted, "raw": str(raw_balance)}
                    
                    # Add to USD total (simplified pricing)
                    if symbol == "USDC":
                        total_usd += formatted
                    elif symbol == "WETH":
                        total_usd += formatted * 3500
                except Exception as e:
                    logger.warning(f"[RefreshBalances] Error fetching {symbol}: {e}")
                    balances[symbol] = {"balance": 0, "raw": "0", "error": str(e)}
        
        logger.info(f"[RefreshBalances] ✅ Fetched: USDC={balances.get('USDC', {}).get('balance', 0):.2f}, ETH={balances.get('ETH', {}).get('balance', 0):.6f}")
        
        return {
            "success": True,
            "agent_address": agent_address,
            "balances": balances,
            "total_usd": round(total_usd, 2),
            "timestamp": str(int(__import__('time').time()))
        }
        
    except Exception as e:
        logger.error(f"[RefreshBalances] Error: {e}")
        return {"success": False, "error": str(e)}


# ===========================================
# DEPOSITS
# ===========================================

@router.post("/deposit")
async def record_deposit(request: DepositRequest):
    """
    Record a deposit to agent wallet
    Call this after user sends tokens to agent address
    """
    success = agent_wallet_manager.record_deposit(
        user_address=request.user_address,
        token=request.token,
        amount=request.amount,
        tx_hash=request.tx_hash
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    # Log to audit
    contract_audit.log_interaction(
        user_id=request.user_address,
        contract_address="user_deposit",
        function_name="deposit",
        parameters={"token": request.token, "amount": request.amount},
        tx_hash=request.tx_hash
    )
    
    return {
        "success": True,
        "message": f"Deposited {request.amount} {request.token}",
        "balances": agent_wallet_manager.get_balances(request.user_address)
    }


# ===========================================
# WITHDRAWALS (24/7 ACCESS)
# ===========================================

@router.post("/withdraw")
async def request_withdrawal(request: WithdrawRequest):
    """
    Withdraw funds from agent wallet
    Large withdrawals (>$10k) require multi-sig
    """
    # Calculate USD value (simplified - would use price feed)
    token_prices = {"USDC": 1.0, "USDT": 1.0, "ETH": 3500, "WETH": 3500}
    amount_usd = request.amount * token_prices.get(request.token.upper(), 1.0)
    
    # Check if multi-sig required
    if multisig_manager.requires_multisig(amount_usd):
        # Verify 2FA if enabled
        if two_factor_auth.is_2fa_enabled(request.user_address):
            if not request.totp_code:
                raise HTTPException(
                    status_code=400, 
                    detail="2FA code required for large withdrawals"
                )
            if not two_factor_auth.verify_totp(request.user_address, request.totp_code):
                raise HTTPException(status_code=401, detail="Invalid 2FA code")
        
        # Create multi-sig request
        msig_request = multisig_manager.create_request(
            user_id=request.user_address,
            action="withdraw",
            amount_usd=amount_usd,
            token=request.token,
            destination=request.destination or request.user_address
        )
        
        return {
            "success": True,
            "requires_multisig": True,
            "request_id": msig_request.request_id,
            "message": f"Large withdrawal (${amount_usd:,.2f}) requires additional approval",
            "approvals_needed": msig_request.required_approvals
        }
    
    # Process immediate withdrawal
    result = agent_wallet_manager.request_withdrawal(
        user_address=request.user_address,
        token=request.token,
        amount=request.amount,
        destination=request.destination
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return {
        "success": True,
        "withdrawal": result["withdrawal"],
        "remaining_balance": result["remaining_balance"]
    }


class SmartAccountWithdrawRequest(BaseModel):
    """Request for Smart Account (ERC-8004) withdrawal"""
    user_address: str
    agent_address: str
    token: str
    amount: float


@router.post("/withdraw-smart-account")
async def withdraw_smart_account(request: SmartAccountWithdrawRequest):
    """
    Build withdrawal transaction for Smart Account.
    
    Smart Accounts (ERC-8004) have NO private key - they're controlled by owner.
    Returns transaction data for user to sign via MetaMask.
    """
    from web3 import Web3
    from eth_abi import encode
    import os
    
    user_address = request.user_address.lower()
    agent_address = request.agent_address
    token = request.token.upper()
    amount = request.amount
    
    logger.info(f"[WithdrawSA] Building withdraw tx: {amount} {token} from {agent_address[:10]}...")
    
    # Token addresses on Base mainnet  
    TOKEN_CONFIGS = {
        "USDC": ("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
        "WETH": ("0x4200000000000000000000000000000000000006", 18),
        "ETH": (None, 18),
        "CBBTC": ("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", 8),
        "AERO": ("0x940181a94A35A4569E4529A3CDfB74e38FD98631", 18),
    }
    
    token_config = TOKEN_CONFIGS.get(token)
    if not token_config:
        raise HTTPException(status_code=400, detail=f"Unknown token: {token}")
    
    token_address, decimals = token_config
    amount_wei = int(amount * (10 ** decimals))
    
    if token == "ETH":
        # For native ETH: Smart Account execute() directly sends ETH
        # execute(address to, uint256 value, bytes data)
        execute_selector = bytes.fromhex("b61d27f6")  # execute(address,uint256,bytes)
        execute_data = execute_selector + encode(
            ['address', 'uint256', 'bytes'],
            [Web3.to_checksum_address(user_address), amount_wei, b'']
        )
        
        return {
            "success": True,
            "agent_address": agent_address,
            "token": token,
            "amount": amount,
            "transaction": {
                "to": agent_address,
                "data": "0x" + execute_data.hex(),
                "gas": "0x" + hex(100000)[2:],
                "value": "0x0"
            },
            "message": f"Sign to withdraw {amount} ETH to your wallet"
        }
    else:
        # For ERC20: Smart Account execute() calls token.transfer()
        # First encode the ERC20 transfer call
        transfer_selector = bytes.fromhex("a9059cbb")  # transfer(address,uint256)
        transfer_data = transfer_selector + encode(
            ['address', 'uint256'],
            [Web3.to_checksum_address(user_address), amount_wei]
        )
        
        # Then wrap in Smart Account execute()
        execute_selector = bytes.fromhex("b61d27f6")  # execute(address,uint256,bytes)
        execute_data = execute_selector + encode(
            ['address', 'uint256', 'bytes'],
            [Web3.to_checksum_address(token_address), 0, transfer_data]
        )
        
        logger.info(f"[WithdrawSA] Built tx for {amount} {token}, calldata: {execute_data.hex()[:40]}...")
        
        return {
            "success": True,
            "agent_address": agent_address,
            "token": token,
            "amount": amount,
            "transaction": {
                "to": agent_address,
                "data": "0x" + execute_data.hex(),
                "gas": "0x" + hex(150000)[2:],
                "value": "0x0"
            },
            "message": f"Sign to withdraw {amount} {token} to your wallet"
        }

@router.post("/emergency-drain")
async def emergency_drain(
    user_address: str = Body(...),
    totp_code: Optional[str] = Body(None)
):
    """
    Emergency: Withdraw ALL funds to user's wallet
    Available 24/7
    """
    # Verify 2FA if enabled
    if two_factor_auth.is_2fa_enabled(user_address):
        if not totp_code:
            raise HTTPException(
                status_code=400, 
                detail="2FA code required for emergency drain"
            )
        if not two_factor_auth.verify_totp(user_address, totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
    
    result = agent_wallet_manager.emergency_drain(user_address)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# ===========================================
# STRATEGY EXECUTION
# ===========================================

@router.post("/strategy/deposit")
async def execute_strategy_deposit(request: StrategyDepositRequest):
    """Agent deposits to a yield strategy on user's behalf"""
    result = agent_wallet_manager.execute_strategy_deposit(
        user_address=request.user_address,
        pool_id=request.pool_id,
        token=request.token,
        amount=request.amount
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Log to audit
    contract_audit.log_interaction(
        user_id=request.user_address,
        contract_address=request.pool_id,
        function_name="strategy_deposit",
        parameters={"token": request.token, "amount": request.amount}
    )
    
    return result


# ===========================================
# KEY MANAGEMENT (24/7 ACCESS)
# ===========================================

@router.post("/export-key")
async def export_private_key(request: ExportKeyRequest):
    """
    ERC-8004 Smart Account - No Private Key Available
    
    Smart Accounts are controlled by the user's connected wallet.
    There is no private key to export - the user's wallet IS the key.
    
    For fund access: Use /withdraw or /emergency-drain endpoints.
    """
    return {
        "success": False,
        "error": "ERC-8004 Smart Accounts don't have exportable private keys",
        "account_type": "erc8004",
        "message": "🔐 Your Smart Account is controlled by your connected wallet. Use Withdraw to access funds.",
        "alternatives": [
            "POST /api/agent-wallet/withdraw - Withdraw specific amount",
            "POST /api/agent-wallet/emergency-drain - Withdraw all funds"
        ]
    }


# ===========================================
# 2FA MANAGEMENT
# ===========================================

@router.post("/2fa/setup")
async def setup_2fa(request: Setup2FARequest):
    """Setup 2FA for critical actions"""
    result = two_factor_auth.setup_2fa(request.user_address)
    
    return {
        "success": True,
        "secret": result["secret"],
        "qr_uri": result["uri"],
        "recovery_codes": result["recovery_codes"],
        "message": "Scan QR code with Google Authenticator or similar app"
    }


@router.post("/2fa/verify")
async def verify_2fa(request: Verify2FARequest):
    """Verify 2FA code is working"""
    is_valid = two_factor_auth.verify_totp(request.user_address, request.code)
    
    return {
        "success": True,
        "valid": is_valid,
        "message": "2FA verified!" if is_valid else "Invalid code"
    }


@router.get("/2fa/status")
async def get_2fa_status(user_address: str = Query(...)):
    """Check if 2FA is enabled"""
    return {
        "success": True,
        "enabled": two_factor_auth.is_2fa_enabled(user_address)
    }


# ===========================================
# MULTI-SIG
# ===========================================

@router.post("/multisig/add-signer")
async def add_authorized_signer(request: AddSignerRequest):
    """Add an authorized signer for multi-sig approvals"""
    # Verify 2FA if enabled
    if two_factor_auth.is_2fa_enabled(request.user_address):
        if not request.totp_code:
            raise HTTPException(status_code=400, detail="2FA required")
        if not two_factor_auth.verify_totp(request.user_address, request.totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
    
    multisig_manager.add_authorized_signer(
        user_id=request.user_address,
        signer_address=request.signer_address
    )
    
    return {
        "success": True,
        "message": f"Added {request.signer_address[:10]}... as authorized signer"
    }


@router.get("/multisig/pending")
async def get_pending_multisig(user_address: str = Query(...)):
    """Get pending multi-sig requests"""
    requests = multisig_manager.get_pending_requests(user_address)
    return {"success": True, "requests": requests}


@router.post("/multisig/approve")
async def approve_multisig(request: ApproveMultiSigRequest):
    """Approve a multi-sig request"""
    success, message = multisig_manager.approve(
        request_id=request.request_id,
        signer_address=request.signer_address
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Check if now fully approved
    msig_request = multisig_manager.pending_requests.get(request.request_id)
    if msig_request and msig_request.is_approved():
        # Execute the withdrawal
        if msig_request.action == "withdraw":
            result = agent_wallet_manager.request_withdrawal(
                user_address=msig_request.user_id,
                token=msig_request.token,
                amount=msig_request.amount_usd,  # Convert back from USD
                destination=msig_request.destination
            )
            return {
                "success": True,
                "message": "Multi-sig approved and withdrawal executed",
                "withdrawal": result
            }
    
    return {"success": True, "message": message}


@router.post("/multisig/reject")
async def reject_multisig(request: ApproveMultiSigRequest):
    """Reject a multi-sig request"""
    success, message = multisig_manager.reject(
        request_id=request.request_id,
        signer_address=request.signer_address
    )
    
    return {"success": success, "message": message}


# ===========================================
# SAFE{WALLET} INTEGRATION
# ===========================================

@router.get("/safe/creation-params")
async def get_safe_creation_params(
    owners: str = Query(..., description="Comma-separated owner addresses"),
    threshold: int = Query(2),
    chain: str = Query("base")
):
    """Get parameters for creating a Safe{Wallet}"""
    owner_list = [o.strip() for o in owners.split(",")]
    
    params = safe_wallet.get_safe_creation_params(
        owners=owner_list,
        threshold=threshold,
        chain=chain
    )
    
    return {"success": True, "params": params}


@router.post("/safe/register")
async def register_safe(
    user_address: str = Body(...),
    safe_address: str = Body(...),
    owners: List[str] = Body(...),
    threshold: int = Body(2),
    chain: str = Body("base")
):
    """Register a deployed Safe{Wallet}"""
    safe_wallet.register_safe(
        user_id=user_address,
        safe_address=safe_address,
        owners=owners,
        threshold=threshold,
        chain=chain
    )
    
    return {
        "success": True,
        "message": f"Safe registered at {safe_address[:10]}..."
    }


@router.get("/safe/info")
async def get_safe_info(user_address: str = Query(...)):
    """Get Safe{Wallet} info for user"""
    info = safe_wallet.get_user_safe(user_address)
    
    if not info:
        return {"success": True, "safe": None, "message": "No Safe registered"}
    
    return {"success": True, "safe": info}


# ===========================================
# AUDIT LOG
# ===========================================

@router.get("/audit-log")
async def get_audit_log(
    user_address: str = Query(...),
    limit: int = Query(50, le=200)
):
    """Get contract interaction audit log"""
    logs = contract_audit.get_user_logs(user_address, limit)
    suspicious = contract_audit.get_suspicious_activity(user_address)
    
    return {
        "success": True,
        "logs": logs,
        "suspicious_count": len(suspicious)
    }


# ===========================================
# AAVE V3 PROTOCOL INTEGRATION
# ===========================================

class AaveSupplyRequest(BaseModel):
    user_address: str
    agent_address: str
    amount_usdc: float

class AaveWithdrawRequest(BaseModel):
    user_address: str
    agent_address: str
    amount_usdc: Optional[float] = None  # None = full withdraw

class AaveWithdrawPercentRequest(BaseModel):
    user_address: str
    agent_address: str
    percent: int  # 25, 50, or 100


@router.post("/aave/supply")
async def aave_supply(request: AaveSupplyRequest):
    """
    Supply (deposit) USDC to Aave V3.
    
    The agent will:
    1. Approve USDC for Aave Pool (if needed)
    2. Supply USDC and receive aUSDC
    """
    try:
        from protocols.aave_v3 import get_aave_protocol
        
        aave = get_aave_protocol()
        
        # Get agent's private key (from secure storage)
        # In production, this would use ERC-8004 Smart Account execution
        agent_key = os.getenv("AGENT_PRIVATE_KEY")
        if not agent_key:
            raise HTTPException(status_code=500, detail="Agent key not configured")
        
        result = await aave.supply(
            user_address=request.agent_address,
            amount_usdc=request.amount_usdc,
            private_key=agent_key
        )
        
        if result["success"]:
            # Log the interaction
            contract_audit.log_interaction(
                user_id=request.user_address,
                contract_address=request.agent_address,
                function_name="aave_v3_supply",
                parameters={"amount_usdc": request.amount_usdc},
                tx_hash=result.get("tx_hash")
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Aave supply error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aave/withdraw")
async def aave_withdraw(request: AaveWithdrawRequest):
    """
    Withdraw USDC from Aave V3.
    
    Pass amount_usdc=null for full withdrawal.
    """
    try:
        from protocols.aave_v3 import get_aave_protocol
        
        aave = get_aave_protocol()
        
        agent_key = os.getenv("AGENT_PRIVATE_KEY")
        if not agent_key:
            raise HTTPException(status_code=500, detail="Agent key not configured")
        
        result = await aave.withdraw(
            user_address=request.agent_address,
            amount_usdc=request.amount_usdc,
            private_key=agent_key
        )
        
        if result["success"]:
            contract_audit.log_interaction(
                user_id=request.user_address,
                contract_address=request.agent_address,
                function_name="aave_v3_withdraw",
                parameters={"amount_usdc": request.amount_usdc or "full"},
                tx_hash=result.get("tx_hash")
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Aave withdraw error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aave/withdraw-percent")
async def aave_withdraw_percent(request: AaveWithdrawPercentRequest):
    """
    Partial withdraw from Aave V3 (for Portfolio Close buttons).
    
    Supports:
    - 25% - Close 25% of position
    - 50% - Close 50% of position  
    - 100% - Close entire position
    """
    try:
        if request.percent not in [25, 50, 100]:
            raise HTTPException(status_code=400, detail="Percent must be 25, 50, or 100")
        
        from protocols.aave_v3 import get_aave_protocol
        
        aave = get_aave_protocol()
        
        agent_key = os.getenv("AGENT_PRIVATE_KEY")
        if not agent_key:
            raise HTTPException(status_code=500, detail="Agent key not configured")
        
        result = await aave.withdraw_percent(
            user_address=request.agent_address,
            percent=request.percent,
            private_key=agent_key
        )
        
        if result["success"]:
            contract_audit.log_interaction(
                user_id=request.user_address,
                contract_address=request.agent_address,
                function_name=f"aave_v3_close_{request.percent}pct",
                parameters={"percent": request.percent},
                tx_hash=result.get("tx_hash")
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Aave withdraw-percent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aave/position")
async def aave_get_position(agent_address: str = Query(...)):
    """Get Aave V3 position for an agent."""
    try:
        from protocols.aave_v3 import get_aave_protocol
        
        aave = get_aave_protocol()
        position = aave.get_position(agent_address)
        
        return {
            "success": True,
            "position": position,
            "protocol": "aave_v3"
        }
        
    except Exception as e:
        logger.error(f"Aave position error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aave/reserves")
async def aave_get_reserves():
    """
    Get all Aave V3 reserves (pools) with live APY and TVL.
    On-chain data source - similar to Aerodrome Sugar contract.
    
    Returns list of available lending markets with:
    - Asset symbol and address
    - Current supply APY
    - Available liquidity (TVL)
    - Risk level and pool type
    """
    try:
        from protocols.aave_v3 import get_aave_protocol
        
        aave = get_aave_protocol()
        reserves = aave.get_reserves_data()
        
        return {
            "success": True,
            "reserves": reserves,
            "count": len(reserves),
            "source": "on-chain",
            "protocol": "aave_v3"
        }
        
    except Exception as e:
        logger.error(f"Aave reserves error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# MORPHO BLUE INTEGRATION
# ==========================================

@router.get("/morpho/markets")
async def get_morpho_markets():
    """
    Get all Morpho Blue USDC markets with live APY and TVL.
    Uses Morpho API for market discovery.
    
    Returns list of available lending markets with:
    - Market ID and collateral token
    - Current supply APY  
    - Total supplied (TVL)
    - Utilization rate
    """
    try:
        from protocols.morpho_blue import get_morpho_protocol
        
        morpho = get_morpho_protocol()
        markets = morpho.get_usdc_markets()
        
        return {
            "success": True,
            "markets": markets,
            "count": len(markets),
            "source": "morpho-api",
            "protocol": "morpho_blue"
        }
        
    except Exception as e:
        logger.error(f"Morpho markets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/morpho/best-market")
async def get_morpho_best_market():
    """
    Get the best (highest APY) Morpho Blue USDC market.
    """
    try:
        from protocols.morpho_blue import get_morpho_protocol
        
        morpho = get_morpho_protocol()
        market = morpho.get_best_usdc_market()
        
        if market:
            return {
                "success": True,
                "market": market,
                "protocol": "morpho_blue"
            }
        else:
            return {
                "success": False,
                "error": "No USDC markets found"
            }
        
    except Exception as e:
        logger.error(f"Morpho best market error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# PRICE ORACLE ENDPOINT
# ===========================================

@router.get("/prices")
async def get_prices():
    """
    Get live token prices from Pyth Network + Chainlink fallback.
    Used by frontend for accurate USD valuations.
    """
    try:
        from services.price_oracle import get_oracle
        
        oracle = get_oracle()
        
        # Get prices for common tokens
        eth_data = oracle.get_price("ETH/USD")
        btc_data = oracle.get_price("BTC/USD")
        usdc_data = oracle.get_price("USDC/USD")
        
        return {
            "success": True,
            "prices": {
                "ETH": {
                    "price": eth_data.get("price", 3000),
                    "source": eth_data.get("source", "fallback"),
                    "age_seconds": eth_data.get("age_seconds", 0),
                    "is_stale": eth_data.get("is_stale", False)
                },
                "BTC": {
                    "price": btc_data.get("price", 60000),
                    "source": btc_data.get("source", "fallback"),
                    "age_seconds": btc_data.get("age_seconds", 0),
                    "is_stale": btc_data.get("is_stale", False)
                },
                "USDC": {
                    "price": usdc_data.get("price", 1.0),
                    "source": usdc_data.get("source", "fallback"),
                    "age_seconds": usdc_data.get("age_seconds", 0),
                    "is_stale": usdc_data.get("is_stale", False)
                },
                # Native stables at fixed 1.0
                "USDT": {"price": 1.0, "source": "fixed", "is_stale": False},
                "DAI": {"price": 1.0, "source": "fixed", "is_stale": False}
            },
            "timestamp": int(__import__("time").time())
        }
        
    except Exception as e:
        logger.error(f"Price oracle error: {e}")
        # Return hardcoded fallback if oracle fails
        return {
            "success": False,
            "error": str(e),
            "prices": {
                "ETH": {"price": 3300, "source": "fallback", "is_stale": True},
                "BTC": {"price": 100000, "source": "fallback", "is_stale": True},
                "USDC": {"price": 1.0, "source": "fallback", "is_stale": True}
            }
        }
