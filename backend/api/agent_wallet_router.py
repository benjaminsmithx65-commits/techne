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
    signature: str  # User's signature for verification


class DepositRequest(BaseModel):
    user_address: str
    token: str
    amount: float
    tx_hash: str


class WithdrawRequest(BaseModel):
    user_address: str
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
    Create a new ERC-8004 Smart Account for user.
    
    ERC-8004 ARCHITECTURE:
    - Smart Account is deployed on-chain via factory contract
    - User's connected wallet is the owner - NO private key needed
    - User can withdraw funds directly using their wallet signature
    """
    try:
        # For ERC-8004, we use SmartAccountService instead of EOA generation
        from services.smart_account_service import get_smart_account_service
        
        smart_account_service = get_smart_account_service()
        result = smart_account_service.create_account(request.user_address)
        
        if result.get("success"):
            agent_address = result.get("account_address")
            tx_hash = result.get("tx_hash")
            
            # Log wallet creation for audit
            contract_audit.log_interaction(
                user_id=request.user_address,
                contract_address="smart_account_factory",
                function_name="create_account",
                parameters={"agent_address": agent_address},
                tx_hash=tx_hash
            )
            
            return {
                "success": True,
                "agent_address": agent_address,
                "account_type": "erc8004",
                "tx_hash": tx_hash,
                "message": "✅ ERC-8004 Smart Account created! Your wallet controls this account - no private key needed."
            }
        else:
            # Account may already exist
            existing = smart_account_service.get_account(request.user_address)
            if existing:
                return {
                    "success": True,
                    "agent_address": existing,
                    "account_type": "erc8004",
                    "message": "Smart Account already exists for this wallet"
                }
            raise Exception(result.get("message", "Smart Account creation failed"))
            
    except Exception as e:
        logger.error(f"Smart Account creation error: {e}")
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
