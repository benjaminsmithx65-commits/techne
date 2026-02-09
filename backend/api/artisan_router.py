"""
Artisan Bot API Router

Backend endpoints for OpenClaw MCP Server integration.
Handles: session key execution, strategy management, trade execution, preferences.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os

logger = logging.getLogger("ArtisanAPI")

router = APIRouter(prefix="/api/artisan", tags=["Artisan Bot"])


# ============================================
# MODELS
# ============================================

class ExecuteTradeRequest(BaseModel):
    user_address: str
    action: str  # enter, exit, swap, rebalance
    pool_id: str
    amount_usd: float
    slippage: float = 0.5


class ExitPositionRequest(BaseModel):
    user_address: str
    position_id: str


class EmergencyExitRequest(BaseModel):
    user_address: str


class StrategyUpdate(BaseModel):
    user_address: str
    risk_level: Optional[str] = None
    target_apy: Optional[float] = None
    max_drawdown: Optional[float] = None
    preferred_protocols: Optional[List[str]] = None
    stablecoin_only: Optional[bool] = None
    auto_compound: Optional[bool] = None
    rebalance_threshold: Optional[float] = None


class PreferenceRequest(BaseModel):
    user_address: str
    key: str
    value: str


# ============================================
# HELPERS
# ============================================

def get_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    return create_client(url, key)


async def get_user_subscription(user_address: str) -> Optional[Dict]:
    """Get premium subscription with session key info"""
    try:
        supabase = get_supabase()
        result = supabase.table("premium_subscriptions").select("*").eq(
            "user_address", user_address.lower()
        ).eq("status", "active").execute()
        
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Get subscription error: {e}")
        return None


async def get_session_key_private(user_address: str) -> Optional[str]:
    """Get session key private key for execution"""
    try:
        from services.agent_service import agent_service
        
        # Get agent for user
        sub = await get_user_subscription(user_address)
        if not sub or not sub.get("agent_address"):
            return None
        
        agent = agent_service.get_agent(sub["agent_address"])
        if agent:
            return agent.get("encrypted_private_key")
        return None
    except Exception as e:
        logger.error(f"Get session key error: {e}")
        return None


# ============================================
# ENDPOINTS
# ============================================

@router.get("/scout")
async def scout_pools(
    chain: str = Query("all"),
    min_apy: float = Query(0),
    max_risk: str = Query("high"),
    stablecoin_only: bool = Query(False)
):
    """Find yield pools matching criteria"""
    try:
        from artisan.scout_agent import get_scout_pools
        
        result = await get_scout_pools(
            chain=chain if chain != "all" else "Base",
            min_apy=min_apy,
            stablecoin_only=stablecoin_only
        )
        
        # Extract pools list from result dict
        pools = result.get("pools", [])
        
        # Apply risk filter
        risk_levels = {"low": 1, "medium": 2, "high": 3}
        max_risk_level = risk_levels.get(max_risk.lower(), 3)
        
        filtered = []
        for pool in pools:
            pool_risk = pool.get("risk_score", "Medium").lower()
            pool_risk_level = risk_levels.get(pool_risk, 2)
            
            if pool_risk_level <= max_risk_level:
                filtered.append(pool)
        
        return {
            "count": len(filtered),
            "pools": filtered[:20]
        }
    except Exception as e:
        logger.error(f"Scout error: {e}")
        return {"count": 0, "pools": [], "error": str(e)}


@router.get("/check-limits")
async def check_execution_limits(
    user: str = Query(...),
    amount: float = Query(...)
):
    """Check if trade amount is within user's limits"""
    try:
        sub = await get_user_subscription(user)
        
        if not sub:
            return {
                "allowed": False,
                "reason": "No active premium subscription",
                "limit": 0,
                "requested": amount
            }
        
        # $99 premium = $10,000 per trade limit
        PREMIUM_LIMIT = 10000
        
        if amount > PREMIUM_LIMIT:
            return {
                "allowed": False,
                "reason": f"Amount exceeds premium limit (${PREMIUM_LIMIT:,})",
                "limit": PREMIUM_LIMIT,
                "requested": amount
            }
        
        # Check session key exists
        if not sub.get("session_key_address"):
            return {
                "allowed": False,
                "reason": "No session key configured. Add session key to enable autonomous trading.",
                "limit": PREMIUM_LIMIT,
                "requested": amount
            }
        
        return {
            "allowed": True,
            "limit": PREMIUM_LIMIT,
            "requested": amount,
            "session_key": sub["session_key_address"][:10] + "..."
        }
        
    except Exception as e:
        logger.error(f"Check limits error: {e}")
        return {"allowed": False, "reason": str(e)}


@router.post("/execute")
async def execute_trade(req: ExecuteTradeRequest):
    """Execute trade via session key"""
    try:
        # Verify subscription and get session key
        session_key_private = await get_session_key_private(req.user_address)
        
        if not session_key_private:
            raise HTTPException(
                status_code=403,
                detail="No session key available. Purchase Artisan Bot subscription."
            )
        
        # Get smart account service
        from services.smart_account_service import SmartAccountService
        smart_account = SmartAccountService()
        
        # Get agent address
        sub = await get_user_subscription(req.user_address)
        agent_address = sub["agent_address"]
        
        # Build transaction based on action
        if req.action == "enter":
            # Build enter position calldata
            from services.aerodrome_lp import AerodromeLPService
            lp = AerodromeLPService()
            
            target, calldata = lp.build_enter_calldata(
                pool_address=req.pool_id,
                amount_usd=req.amount_usd
            )
            
        elif req.action == "exit":
            from services.aerodrome_lp import AerodromeLPService
            lp = AerodromeLPService()
            
            target, calldata = lp.build_exit_calldata(req.pool_id)
            
        elif req.action == "swap":
            # Swap implementation
            target = req.pool_id
            calldata = b""  # Placeholder
            
        elif req.action == "rebalance":
            # Trigger rebalance
            return await trigger_rebalance_internal(req.user_address)
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")
        
        # Execute via session key
        result = smart_account.execute_with_session_key(
            smart_account=agent_address,
            target=target,
            value=0,
            calldata=calldata,
            session_key_private=session_key_private,
            estimated_value_usd=int(req.amount_usd)
        )
        
        # Log action
        await log_artisan_action(
            user_address=req.user_address,
            action_type="trade",
            details={
                "action": req.action,
                "pool": req.pool_id,
                "amount_usd": req.amount_usd,
                "tx_hash": result.get("tx_hash")
            },
            tx_hash=result.get("tx_hash")
        )
        
        return {
            "success": result.get("success", False),
            "tx_hash": result.get("tx_hash"),
            "action": req.action,
            "amount_usd": req.amount_usd,
            "pool": req.pool_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute trade error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exit-position")
async def exit_position(req: ExitPositionRequest):
    """Exit a specific position"""
    try:
        session_key_private = await get_session_key_private(req.user_address)
        
        if not session_key_private:
            raise HTTPException(status_code=403, detail="No session key")
        
        from services.smart_account_service import SmartAccountService
        from services.agent_service import agent_service
        
        # Get position details
        position = agent_service.get_agent_positions(req.position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Build exit calldata
        from services.aerodrome_lp import AerodromeLPService
        lp = AerodromeLPService()
        target, calldata = lp.build_exit_calldata(position["pool_address"])
        
        # Execute
        sub = await get_user_subscription(req.user_address)
        smart_account = SmartAccountService()
        
        result = smart_account.execute_with_session_key(
            smart_account=sub["agent_address"],
            target=target,
            value=0,
            calldata=calldata,
            session_key_private=session_key_private
        )
        
        # Mark position closed
        agent_service.close_position(req.position_id, result.get("exit_value_usd"))
        
        return {
            "success": True,
            "tx_hash": result.get("tx_hash"),
            "position_id": req.position_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exit position error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emergency-exit")
async def emergency_exit_all(req: EmergencyExitRequest):
    """EMERGENCY: Exit all positions to stablecoins"""
    try:
        session_key_private = await get_session_key_private(req.user_address)
        
        if not session_key_private:
            raise HTTPException(status_code=403, detail="No session key")
        
        from services.agent_service import agent_service
        
        sub = await get_user_subscription(req.user_address)
        agent_address = sub["agent_address"]
        
        # Get all active positions
        positions = agent_service.get_agent_positions(agent_address, status="active")
        
        results = []
        for pos in positions:
            try:
                # Exit each position
                result = await exit_position(ExitPositionRequest(
                    user_address=req.user_address,
                    position_id=str(pos["id"])
                ))
                results.append({"position": pos["id"], "success": True})
            except Exception as e:
                results.append({"position": pos["id"], "success": False, "error": str(e)})
        
        # Log emergency action
        await log_artisan_action(
            user_address=req.user_address,
            action_type="emergency_exit",
            details={"positions_exited": len(results), "results": results}
        )
        
        return {
            "success": True,
            "positions_exited": len(results),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Emergency exit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy")
async def get_user_strategy(user: str = Query(...)):
    """Get user's current strategy configuration"""
    try:
        supabase = get_supabase()
        
        result = supabase.table("artisan_strategies").select("*").eq(
            "user_address", user.lower()
        ).execute()
        
        if result.data:
            return result.data[0]
        
        # Return default strategy
        return {
            "user_address": user,
            "risk_level": "moderate",
            "target_apy": 15.0,
            "max_drawdown": 20.0,
            "preferred_protocols": ["Aerodrome", "Aave"],
            "stablecoin_only": False,
            "auto_compound": True,
            "rebalance_threshold": 10.0
        }
        
    except Exception as e:
        logger.error(f"Get strategy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/strategy")
async def update_user_strategy(req: StrategyUpdate):
    """Update user's strategy configuration"""
    try:
        supabase = get_supabase()
        
        update_data = {}
        if req.risk_level: update_data["risk_level"] = req.risk_level
        if req.target_apy is not None: update_data["target_apy"] = req.target_apy
        if req.max_drawdown is not None: update_data["max_drawdown"] = req.max_drawdown
        if req.preferred_protocols: update_data["preferred_protocols"] = req.preferred_protocols
        if req.stablecoin_only is not None: update_data["stablecoin_only"] = req.stablecoin_only
        if req.auto_compound is not None: update_data["auto_compound"] = req.auto_compound
        if req.rebalance_threshold is not None: update_data["rebalance_threshold"] = req.rebalance_threshold
        
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Upsert strategy
        result = supabase.table("artisan_strategies").upsert({
            "user_address": req.user_address.lower(),
            **update_data
        }).execute()
        
        await log_artisan_action(
            user_address=req.user_address,
            action_type="other",
            details={"action": "strategy_update", "changes": update_data}
        )
        
        return {"success": True, "strategy": update_data}
        
    except Exception as e:
        logger.error(f"Update strategy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebalance")
async def trigger_rebalance(req: dict):
    """Trigger portfolio rebalancing"""
    user_address = req.get("user_address")
    return await trigger_rebalance_internal(user_address)


async def trigger_rebalance_internal(user_address: str):
    """Internal rebalance logic"""
    try:
        # Get strategy and current positions
        strategy = await get_user_strategy(user_address)
        
        from services.agent_service import agent_service
        sub = await get_user_subscription(user_address)
        
        if not sub:
            return {"success": False, "error": "No subscription"}
        
        positions = agent_service.get_agent_positions(sub["agent_address"])
        
        # Calculate rebalance actions (simplified)
        # In production, this would use sophisticated logic
        
        await log_artisan_action(
            user_address=user_address,
            action_type="other",
            details={"action": "rebalance_triggered", "positions": len(positions)}
        )
        
        return {
            "success": True,
            "rebalance_triggered": True,
            "positions_analyzed": len(positions),
            "message": "Rebalancing initiated based on strategy parameters"
        }
        
    except Exception as e:
        logger.error(f"Rebalance error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/opportunities")
async def get_yield_opportunities(
    user: str = Query(...),
    limit: int = Query(5)
):
    """Get AI-curated yield opportunities based on strategy"""
    try:
        # Get user strategy
        strategy = await get_user_strategy(user)
        
        # Get pools matching strategy
        from services.pool_discovery import get_pool_discovery
        discovery = get_pool_discovery()
        
        pools = await discovery.find_pools(
            min_apy=strategy.get("target_apy", 10) * 0.8,
            max_risk=strategy.get("risk_level", "moderate"),
            stablecoin_only=strategy.get("stablecoin_only", False)
        )
        
        # Rank and filter
        opportunities = pools[:limit]
        
        return {
            "count": len(opportunities),
            "strategy": strategy.get("risk_level"),
            "opportunities": opportunities
        }
        
    except Exception as e:
        logger.error(f"Opportunities error: {e}")
        return {"count": 0, "opportunities": []}


@router.get("/session-key")
async def check_session_key(user: str = Query(...)):
    """Check if user has active session key"""
    try:
        sub = await get_user_subscription(user)
        
        if not sub:
            return {
                "has_session_key": False,
                "subscription_active": False,
                "message": "No premium subscription"
            }
        
        has_key = bool(sub.get("session_key_address"))
        
        return {
            "has_session_key": has_key,
            "subscription_active": True,
            "session_key_address": sub.get("session_key_address"),
            "agent_address": sub.get("agent_address"),
            "expires_at": sub.get("expires_at")
        }
        
    except Exception as e:
        logger.error(f"Session key check error: {e}")
        return {"has_session_key": False, "error": str(e)}


class LinkAgentRequest(BaseModel):
    chat_id: int
    agent_address: str
    user_address: str


@router.post("/link-agent")
async def link_agent_to_subscription(req: LinkAgentRequest):
    """
    Link existing agent to subscription (for TG /import command).
    
    Finds session key from agents table and links to subscription.
    """
    try:
        supabase = get_supabase()
        
        # Verify agent exists and belongs to user
        from services.agent_service import agent_service
        
        agent = agent_service.get_agent(req.agent_address)
        
        if not agent:
            return {
                "success": False,
                "error": "Agent not found. Create one at techne.finance/build"
            }
        
        # Verify agent belongs to same user
        if agent.get("owner_address", "").lower() != req.user_address.lower():
            return {
                "success": False,
                "error": "Agent doesn't belong to your wallet"
            }
        
        # Get session key from agent
        session_key_address = agent.get("session_key_address")
        
        # Update subscription with agent info
        result = supabase.table("premium_subscriptions").update({
            "agent_address": req.agent_address,
            "session_key_address": session_key_address
        }).eq("telegram_chat_id", req.chat_id).execute()
        
        if not result.data:
            return {
                "success": False,
                "error": "Subscription not found for this chat"
            }
        
        logger.info(f"[Artisan] Linked agent {req.agent_address[:10]} to chat {req.chat_id}")
        
        return {
            "success": True,
            "agent_address": req.agent_address,
            "session_key_address": session_key_address,
            "message": "Agent linked successfully"
        }
        
    except Exception as e:
        logger.error(f"Link agent error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/limits")
async def get_execution_limits(user: str = Query(...)):
    """Get execution limits for user"""
    try:
        sub = await get_user_subscription(user)
        
        if not sub:
            return {
                "tier": "free",
                "per_trade_limit": 0,
                "daily_limit": 0,
                "can_execute": False
            }
        
        # Premium tier limits
        return {
            "tier": "premium",
            "per_trade_limit": 10000,
            "daily_limit": 50000,
            "can_execute": bool(sub.get("session_key_address")),
            "remaining_today": 50000  # Placeholder - track actual usage
        }
        
    except Exception as e:
        logger.error(f"Limits error: {e}")
        return {"tier": "unknown", "error": str(e)}


@router.post("/preferences")
async def save_preference(req: PreferenceRequest):
    """Save user preference"""
    try:
        supabase = get_supabase()
        
        # Upsert preference
        supabase.table("artisan_memory").upsert({
            "user_address": req.user_address.lower(),
            "preferences": {req.key: req.value},
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        
        return {"success": True, "key": req.key, "saved": True}
        
    except Exception as e:
        logger.error(f"Save preference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences")
async def get_preferences(user: str = Query(...)):
    """Get all user preferences"""
    try:
        supabase = get_supabase()
        
        result = supabase.table("artisan_memory").select("preferences").eq(
            "user_address", user.lower()
        ).execute()
        
        if result.data:
            return {"preferences": result.data[0].get("preferences", {})}
        return {"preferences": {}}
        
    except Exception as e:
        logger.error(f"Get preferences error: {e}")
        return {"preferences": {}, "error": str(e)}


async def log_artisan_action(
    user_address: str,
    action_type: str,
    details: Dict[str, Any],
    tx_hash: str = None
):
    """Log action to audit trail"""
    try:
        supabase = get_supabase()
        
        # Get subscription ID
        sub = await get_user_subscription(user_address)
        if not sub:
            return
        
        supabase.table("artisan_actions").insert({
            "subscription_id": sub["id"],
            "action_type": action_type,
            "details": details,
            "tx_hash": tx_hash,
            "executed": True,
            "executed_at": datetime.utcnow().isoformat()
        }).execute()
        
    except Exception as e:
        logger.error(f"Log action error: {e}")


# ============================================
# OPENCLAW INTEGRATION ENDPOINTS
# ============================================

class ActivateCodeRequest(BaseModel):
    activation_code: str
    telegram_id: str


class SetModeRequest(BaseModel):
    agent_address: str
    mode: str  # observer, advisor, copilot, full_auto


class ImportAgentRequest(BaseModel):
    agent_address: str
    user_id: str


@router.post("/activate")
async def activate_premium_code(req: ActivateCodeRequest):
    """
    Activate Premium subscription with activation code.
    Called from OpenClaw /start ARTISAN-XXXX-XXXX command.
    """
    try:
        supabase = get_supabase()
        
        # Validate activation code format
        code = req.activation_code.upper()
        if not code.startswith("ARTISAN-") or len(code) != 16:
            return {
                "success": False,
                "error": "Invalid code format. Expected: ARTISAN-XXXX-XXXX"
            }
        
        # Check if code exists and is unused
        result = supabase.table("activation_codes").select("*").eq(
            "code", code
        ).execute()
        
        if not result.data:
            return {
                "success": False,
                "error": "Activation code not found"
            }
        
        code_data = result.data[0]
        
        if code_data.get("used"):
            return {
                "success": False,
                "error": "Activation code already used"
            }
        
        # Mark code as used
        supabase.table("activation_codes").update({
            "used": True,
            "used_at": datetime.utcnow().isoformat(),
            "telegram_id": req.telegram_id
        }).eq("code", code).execute()
        
        # Create subscription
        subscription = supabase.table("premium_subscriptions").insert({
            "telegram_chat_id": int(req.telegram_id),
            "status": "active",
            "tier": code_data.get("tier", "artisan"),
            "activated_at": datetime.utcnow().isoformat(),
            "expires_at": None  # Never expires for lifetime codes
        }).execute()
        
        logger.info(f"[Artisan] Activated code {code[:8]}*** for TG {req.telegram_id}")
        
        return {
            "success": True,
            "features": ["portfolio", "pools", "trading", "strategies"],
            "tier": code_data.get("tier", "artisan"),
            "message": "Premium activated successfully"
        }
        
    except Exception as e:
        logger.error(f"Activate code error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/status/{telegram_id}")
async def get_user_status(telegram_id: str):
    """
    Check if a Telegram user has active premium subscription.
    Used by OpenClaw bot to identify returning users.
    """
    try:
        # Check for active subscription
        result = supabase.table("premium_subscriptions").select("*").eq(
            "telegram_chat_id", int(telegram_id)
        ).eq("status", "active").execute()
        
        if result.data and len(result.data) > 0:
            sub = result.data[0]
            
            # Get connected agent if any
            agent = None
            if sub.get("agent_address"):
                agent = {
                    "address": sub["agent_address"],
                    "mode": sub.get("mode", "observer")
                }
            
            return {
                "success": True,
                "is_premium": True,
                "tier": sub.get("tier", "artisan"),
                "features": ["portfolio", "pools", "trading", "strategies"],
                "agent": agent,
                "activated_at": sub.get("activated_at")
            }
        else:
            return {
                "success": True,
                "is_premium": False,
                "message": "No active subscription. Use /start ARTISAN-XXXX-XXXX to activate."
            }
            
    except Exception as e:
        logger.error(f"Get user status error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/import-agent")
async def import_agent_for_user(req: ImportAgentRequest):
    """
    Import deployed agent address for OpenClaw user.
    Called from /import command.
    """
    try:
        supabase = get_supabase()
        from services.agent_service import agent_service
        
        # Validate address
        if not req.agent_address.startswith("0x") or len(req.agent_address) != 42:
            return {
                "success": False,
                "error": "Invalid agent address format"
            }
        
        # Check agent exists
        agent = agent_service.get_agent(req.agent_address)
        
        if not agent:
            return {
                "success": False,
                "error": "Agent not found. Create one at techne.finance/build"
            }
        
        # Get user subscription by telegram ID
        sub_result = supabase.table("premium_subscriptions").select("*").eq(
            "telegram_chat_id", int(req.user_id)
        ).execute()
        
        if not sub_result.data:
            return {
                "success": False,
                "error": "No active subscription. Use /start ARTISAN-XXXX-XXXX first."
            }
        
        # Link agent to subscription
        supabase.table("premium_subscriptions").update({
            "agent_address": req.agent_address,
            "session_key_address": agent.get("session_key_address"),
            "user_address": agent.get("owner_address")
        }).eq("telegram_chat_id", int(req.user_id)).execute()
        
        # Get agent balance
        balance = agent.get("balance_usd", 0)
        positions_count = len(agent.get("positions", []))
        
        logger.info(f"[Artisan] Imported agent {req.agent_address[:10]}... for user {req.user_id}")
        
        return {
            "success": True,
            "balance": balance,
            "positions_count": positions_count,
            "autonomy_mode": agent.get("autonomy_mode", "advisor")
        }
        
    except Exception as e:
        logger.error(f"Import agent error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/set-mode")
async def set_autonomy_mode(req: SetModeRequest):
    """
    Set autonomy mode for agent.
    Modes: observer, advisor, copilot, full_auto
    """
    try:
        valid_modes = ["observer", "advisor", "copilot", "full_auto"]
        
        if req.mode not in valid_modes:
            return {
                "success": False,
                "error": f"Invalid mode. Choose from: {', '.join(valid_modes)}"
            }
        
        supabase = get_supabase()
        
        # Update agent mode
        result = supabase.table("agents").update({
            "autonomy_mode": req.mode,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("smart_account_address", req.agent_address).execute()
        
        if not result.data:
            return {"success": False, "error": "Agent not found"}
        
        # Also update subscription
        supabase.table("premium_subscriptions").update({
            "autonomy_mode": req.mode
        }).eq("agent_address", req.agent_address).execute()
        
        mode_limits = {
            "observer": "View-only, no trades",
            "advisor": "Suggests trades, requires confirmation",
            "copilot": "Auto-executes trades under $1,000",
            "full_auto": "Autonomous up to $10,000/day"
        }
        
        logger.info(f"[Artisan] Set mode {req.mode} for agent {req.agent_address[:10]}")
        
        return {
            "success": True,
            "mode": req.mode,
            "description": mode_limits[req.mode]
        }
        
    except Exception as e:
        logger.error(f"Set mode error: {e}")
        return {"success": False, "error": str(e)}

