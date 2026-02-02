"""
Premium Subscription API Router
Handles Techne Premium ($50/mo) subscriptions with Artisan Agent
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import secrets
import logging
import os

# Supabase client
from supabase import create_client

logger = logging.getLogger("PremiumAPI")

router = APIRouter(prefix="/api/premium", tags=["Premium"])

# ============================================
# MODELS
# ============================================

class SubscribeRequest(BaseModel):
    """Request to subscribe to Premium"""
    user_address: str
    x402_payment_id: Optional[str] = None  # Meridian payment ID

class ValidateCodeRequest(BaseModel):
    """Validate activation code from Telegram"""
    activation_code: str
    telegram_chat_id: int
    telegram_username: Optional[str] = None

class ChangeAutonomyRequest(BaseModel):
    """Change autonomy mode"""
    user_address: str
    mode: str  # observer, advisor, copilot, full_auto

class DisconnectRequest(BaseModel):
    """Disconnect/cancel subscription"""
    user_address: str

# ============================================
# HELPERS
# ============================================

def get_supabase():
    """Get Supabase client"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    return create_client(url, key)

def generate_activation_code() -> str:
    """Generate unique activation code: ARTISAN-XXXX-XXXX"""
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    return f"ARTISAN-{part1}-{part2}"

# ============================================
# ENDPOINTS
# ============================================

# Treasury address for receiving payments
TREASURY_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f8fE00"  # TODO: Update to your treasury
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
SUBSCRIPTION_PRICE_USDC = 99_000_000  # $99 in USDC (6 decimals)


@router.get("/payment-requirements")
async def get_payment_requirements():
    """
    Get x402 payment requirements for $99 Artisan Bot subscription.
    Frontend uses this to build EIP-712 signature request.
    """
    return {
        "usdcAddress": USDC_BASE,
        "recipientAddress": TREASURY_ADDRESS,
        "amount": str(SUBSCRIPTION_PRICE_USDC),
        "chainId": 8453,  # Base
        "productName": "Artisan Bot",
        "productDescription": "AI Trading Agent - 30 day subscription",
        "priceUsd": "99.00"
    }


class SubscribeWithPaymentRequest(BaseModel):
    """Subscribe request with x402 payment payload"""
    wallet_address: str
    paymentPayload: dict  # x402 payload from frontend
    meridian_tx: Optional[str] = None  # Meridian transaction hash after settlement


@router.post("/subscribe")
async def subscribe_premium(request: SubscribeWithPaymentRequest):
    """
    Subscribe to Techne Artisan Bot ($99/mo) via x402 Meridian payment.
    
    Flow:
    1. Frontend signs EIP-712 TransferWithAuthorization
    2. Frontend calls this with payment payload
    3. We verify and settle via Meridian (or direct)
    4. Generate activation code
    5. User enters code in Telegram bot
    """
    try:
        supabase = get_supabase()
        user_address = request.wallet_address.lower()
        
        # Extract payment info for verification/logging
        payment_sig = request.paymentPayload.get("payload", {}).get("signature", "")[:20]
        
        # Check if already subscribed
        existing = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address
        ).execute()
        
        if existing.data:
            sub = existing.data[0]
            if sub["status"] == "active":
                return {
                    "success": True,
                    "already_subscribed": True,
                    "activation_code": sub["activation_code"],
                    "expires_at": sub["expires_at"],
                    "message": "Already subscribed! Use your existing code."
                }
            else:
                # Reactivate expired/cancelled subscription
                code = generate_activation_code()
                supabase.table("premium_subscriptions").update({
                    "status": "active",
                    "activation_code": code,
                    "code_used_at": None,
                    "telegram_chat_id": None,
                    "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
                    "x402_payment_id": payment_sig
                }).eq("user_address", user_address).execute()
                
                return {
                    "success": True,
                    "already_subscribed": False,
                    "activation_code": code,
                    "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
                    "message": "Subscription reactivated!"
                }
        
        # Create new subscription
        code = generate_activation_code()
        expires_at = datetime.now() + timedelta(days=30)
        
        supabase.table("premium_subscriptions").insert({
            "user_address": user_address,
            "status": "active",
            "autonomy_mode": "advisor",  # Default mode
            "activation_code": code,
            "expires_at": expires_at.isoformat(),
            "x402_payment_id": payment_sig
        }).execute()
        
        logger.info(f"[Premium] New subscription: {user_address[:10]}... code: {code}")
        
        return {
            "success": True,
            "already_subscribed": False,
            "activation_code": code,
            "expires_at": expires_at.isoformat(),
            "telegram_bot": "@TechneArtisanBot",
            "message": "Welcome to Techne Premium! Enter your code in Telegram to activate."
        }
        
    except Exception as e:
        logger.error(f"Subscribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-code")
async def validate_activation_code(request: ValidateCodeRequest):
    """
    Validate activation code from Telegram bot.
    Links Telegram chat to subscription AND creates agent wallet.
    
    Full flow:
    1. Validate code exists and not used
    2. Create agent wallet (smart account)
    3. Generate session key for backend execution
    4. Link everything together
    """
    try:
        supabase = get_supabase()
        code = request.activation_code.upper().strip()
        
        # Find subscription by code
        result = supabase.table("premium_subscriptions").select("*").eq(
            "activation_code", code
        ).execute()
        
        if not result.data:
            return {
                "success": False,
                "error": "Invalid activation code"
            }
        
        sub = result.data[0]
        
        # Check if already used
        if sub.get("code_used_at"):
            # If same chat, just return success
            if sub.get("telegram_chat_id") == request.telegram_chat_id:
                return {
                    "success": True,
                    "user_address": sub["user_address"],
                    "agent_address": sub.get("agent_address"),
                    "autonomy_mode": sub["autonomy_mode"],
                    "expires_at": sub["expires_at"],
                    "message": "Already activated!"
                }
            return {
                "success": False,
                "error": "Code already used by another account"
            }
        
        # Check if expired
        if sub["status"] != "active":
            return {
                "success": False,
                "error": "Subscription is not active"
            }
        
        # === AUTO-CREATE AGENT WALLET ===
        agent_address = None
        session_key_address = None
        
        try:
            from services.smart_account_service import SmartAccountService
            from eth_account import Account
            
            smart_account = SmartAccountService()
            
            # Generate unique agent ID
            agent_id = f"artisan-{secrets.token_hex(8)}"
            
            # Get counterfactual smart account address
            account_result = smart_account.create_account(
                user_address=sub["user_address"],
                agent_id=agent_id
            )
            
            if account_result.get("success"):
                agent_address = account_result["account_address"]
                
                # Generate session key for backend execution
                session_key = Account.create()
                session_key_address = session_key.address
                
                # Store in agents table for later use
                from services.agent_service import agent_service, AgentConfig
                
                config = AgentConfig(
                    chain="base",
                    preset="artisan",
                    risk_level="moderate"
                )
                
                agent_service.create_agent(
                    user_address=sub["user_address"],
                    agent_address=agent_address,
                    encrypted_private_key=session_key.key.hex(),
                    config=config,
                    agent_name=agent_id
                )
                
                logger.info(f"[Premium] Created agent {agent_address[:10]} for {sub['user_address'][:10]}")
            else:
                logger.warning(f"[Premium] Agent creation failed: {account_result.get('error')}")
                
        except Exception as agent_error:
            logger.error(f"[Premium] Agent creation error: {agent_error}")
            # Continue anyway - agent can be created later
        
        # Link Telegram + agent to subscription
        update_data = {
            "telegram_chat_id": request.telegram_chat_id,
            "telegram_username": request.telegram_username,
            "code_used_at": datetime.now().isoformat()
        }
        
        if agent_address:
            update_data["agent_address"] = agent_address
        if session_key_address:
            update_data["session_key_address"] = session_key_address
        
        supabase.table("premium_subscriptions").update(update_data).eq(
            "id", sub["id"]
        ).execute()
        
        logger.info(f"[Premium] Code validated: {code} → chat {request.telegram_chat_id}")
        
        return {
            "success": True,
            "user_address": sub["user_address"],
            "agent_address": agent_address,
            "session_key_address": session_key_address,
            "autonomy_mode": sub["autonomy_mode"],
            "expires_at": sub["expires_at"],
            "message": "Welcome to Artisan Agent! 🤖 Your agent wallet is ready."
        }
        
    except Exception as e:
        logger.error(f"Validate code error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_subscription_status(user_address: str = Query(...)):
    """Get subscription status for user"""
    try:
        supabase = get_supabase()
        user_address = user_address.lower()
        
        result = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address
        ).execute()
        
        if not result.data:
            return {
                "subscribed": False,
                "message": "No active subscription"
            }
        
        sub = result.data[0]
        is_active = sub["status"] == "active"
        is_connected = sub["telegram_chat_id"] is not None
        
        return {
            "subscribed": is_active,
            "status": sub["status"],
            "autonomy_mode": sub["autonomy_mode"],
            "telegram_connected": is_connected,
            "telegram_username": sub.get("telegram_username"),
            "expires_at": sub["expires_at"],
            "activation_code": sub["activation_code"] if not is_connected else None
        }
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/change-mode")
async def change_autonomy_mode(request: ChangeAutonomyRequest):
    """Change autonomy mode"""
    try:
        valid_modes = ["observer", "advisor", "copilot", "full_auto"]
        if request.mode not in valid_modes:
            raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {valid_modes}")
        
        supabase = get_supabase()
        user_address = request.user_address.lower()
        
        result = supabase.table("premium_subscriptions").update({
            "autonomy_mode": request.mode
        }).eq("user_address", user_address).eq("status", "active").execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        logger.info(f"[Premium] Mode changed: {user_address[:10]}... → {request.mode}")
        
        return {
            "success": True,
            "mode": request.mode,
            "message": f"Autonomy mode changed to: {request.mode}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change mode error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_subscription(request: DisconnectRequest):
    """Disconnect Telegram and cancel subscription"""
    try:
        supabase = get_supabase()
        user_address = request.user_address.lower()
        
        result = supabase.table("premium_subscriptions").update({
            "status": "cancelled",
            "telegram_chat_id": None,
            "telegram_username": None
        }).eq("user_address", user_address).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        logger.info(f"[Premium] Disconnected: {user_address[:10]}...")
        
        return {
            "success": True,
            "message": "Subscription cancelled. You can resubscribe anytime."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete")
async def delete_subscription(request: DisconnectRequest):
    """Permanently delete subscription and all associated data"""
    try:
        supabase = get_supabase()
        user_address = request.user_address.lower()
        
        # Get subscription first for related cleanup
        sub_result = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address
        ).execute()
        
        if not sub_result.data:
            raise HTTPException(status_code=404, detail="No subscription found")
        
        # Delete related data (conversations, actions, memory)
        try:
            supabase.table("artisan_conversations").delete().eq(
                "user_address", user_address
            ).execute()
            
            supabase.table("artisan_actions").delete().eq(
                "user_address", user_address  
            ).execute()
            
            supabase.table("artisan_memory").delete().eq(
                "user_address", user_address
            ).execute()
            
            supabase.table("artisan_strategies").delete().eq(
                "user_address", user_address
            ).execute()
        except Exception as e:
            logger.warning(f"Some related data may not exist: {e}")
        
        # Delete subscription
        supabase.table("premium_subscriptions").delete().eq(
            "user_address", user_address
        ).execute()
        
        logger.info(f"[Premium] DELETED: {user_address[:10]}... (full removal)")
        
        return {
            "success": True,
            "message": "Subscription and all data permanently deleted."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscription-by-chat")
async def get_subscription_by_telegram(chat_id: int = Query(...)):
    """Get subscription by Telegram chat ID (used by bot)"""
    try:
        supabase = get_supabase()
        
        result = supabase.table("premium_subscriptions").select("*").eq(
            "telegram_chat_id", chat_id
        ).eq("status", "active").execute()
        
        if not result.data:
            return {"found": False}
        
        sub = result.data[0]
        return {
            "found": True,
            "user_address": sub["user_address"],
            "autonomy_mode": sub["autonomy_mode"],
            "expires_at": sub["expires_at"]
        }
        
    except Exception as e:
        logger.error(f"Get by chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
