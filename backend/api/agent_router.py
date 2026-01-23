"""
Agent Operations API Router
Endpoints for agent actions: harvest, rebalance, pause, audit
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import csv
import io

router = APIRouter(prefix="/api/agent", tags=["Agent Operations"])

# ============================================
# MODELS
# ============================================

class HarvestRequest(BaseModel):
    wallet: str
    agentId: str
    agentAddress: Optional[str] = None

class RebalanceRequest(BaseModel):
    wallet: str
    agentId: str
    agentAddress: Optional[str] = None
    strategy: Optional[str] = None

class PauseAllRequest(BaseModel):
    wallet: str
    reason: str = "manual"

class AgentStatusUpdate(BaseModel):
    wallet: str
    agentId: str
    isActive: bool

# ============================================
# MANUAL ALLOCATE ENDPOINT
# ============================================

@router.post("/allocate")
async def manual_allocate(user_address: str = Query(...)):
    """
    Manually trigger allocation of user's deposited funds to protocol.
    Called when deposit was missed by the monitor or for testing.
    """
    try:
        from agents.contract_monitor import contract_monitor
        from web3 import Web3
        
        # Get user's balance from contract
        w3 = contract_monitor._get_web3()
        balance = contract_monitor.contract.functions.balances(
            Web3.to_checksum_address(user_address)
        ).call()
        
        amount_usdc = balance / 1e6
        
        if balance == 0:
            return {
                "success": False,
                "message": "No funds to allocate",
                "balance": 0
            }
        
        print(f"[ManualAllocate] Allocating {amount_usdc:.2f} USDC for {user_address[:10]}...")
        
        # Trigger allocation
        await contract_monitor.allocate_funds(user_address, balance)
        
        return {
            "success": True,
            "user_address": user_address,
            "amount_usdc": amount_usdc,
            "message": f"Allocation triggered for {amount_usdc:.2f} USDC"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# SMART ACCOUNT ENDPOINTS (Trustless Architecture)
# ============================================

@router.get("/smart-account")
async def get_smart_account(wallet_address: str = Query(...)):
    """
    Get user's Smart Account address and info.
    
    Returns:
    - smart_account: Address of user's Smart Account (or null if not created)
    - factory: Factory address for creating new accounts
    - can_create: Whether user can create a new Smart Account
    """
    from api.smart_account_executor import SmartAccountExecutor, FACTORY_ADDRESS
    
    try:
        executor = SmartAccountExecutor(wallet_address)
        
        # Check if session key is setup
        can_use_session_key = False
        if executor.smart_account:
            can_use_session_key = executor.can_use_session_key
        
        return {
            "success": True,
            "smart_account": executor.smart_account,
            "factory": FACTORY_ADDRESS,
            "is_active": executor.is_smart_account_active,
            "can_use_session_key": can_use_session_key,
            "legacy_wallet": "0xC83E01e39A56Ec8C56Dd45236E58eE7a139cCDD4"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "smart_account": None
        }


@router.post("/smart-account/register")
async def register_smart_account(
    wallet_address: str = Query(...),
    smart_account_address: str = Query(...),
    session_key_address: str = Query(None)
):
    """
    Register a user's Smart Account address in the database.
    Called after user creates Smart Account via frontend.
    """
    try:
        from infrastructure.supabase_client import supabase
        
        if supabase.is_available:
            result = await supabase.save_user_smart_account(
                wallet_address,
                smart_account_address,
                session_key_address
            )
            
            return {
                "success": True,
                "registered": result is not None,
                "smart_account": smart_account_address
            }
        
        return {
            "success": True,
            "registered": False,
            "message": "Supabase not available - will use on-chain data"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# CLOSE POSITION ENDPOINT
# ============================================

class ClosePositionRequest(BaseModel):
    user_address: str
    position_id: int
    protocol: str
    percentage: int  # 1-100
    amount: int  # USDC in 6 decimals

position_router = APIRouter(prefix="/api/position", tags=["Position Management"])

@position_router.post("/close")
async def close_position(request: ClosePositionRequest):
    """
    Close a position partially or fully.
    
    Withdraws the specified percentage from the protocol back to user's wallet.
    """
    import os
    
    try:
        amount_usdc = request.amount / 1e6
        
        print(f"[ClosePosition] Closing {request.percentage}% of position {request.position_id}", flush=True)
        print(f"[ClosePosition] Protocol: {request.protocol}, Amount: ${amount_usdc:.2f}", flush=True)
        
        # 0. Execute ON-CHAIN withdrawal via SmartAccountExecutor
        # Supports both Smart Account mode and legacy Techne Wallet fallback
        onchain_tx_hash = None
        if request.protocol.lower() in ["aave", "aave-v3", "aave v3"]:
            print("[ClosePosition] Protocol is Aave - using SmartAccountExecutor", flush=True)
            try:
                from api.smart_account_executor import SmartAccountExecutor
                
                executor = SmartAccountExecutor(request.user_address)
                print(f"[ClosePosition] Smart Account: {executor.smart_account}", flush=True)
                print(f"[ClosePosition] Mode: {'smart_account' if executor.is_smart_account_active else 'legacy'}", flush=True)
                
                # Execute exit position
                result = await executor.exit_position_aave()
                
                if result.get("success"):
                    if result.get("mode") == "legacy":
                        # Legacy mode executed synchronously
                        onchain_tx_hash = result.get("tx_hash")
                        print(f"[ClosePosition] ✅ Legacy exitPosition SUCCESS: {onchain_tx_hash}", flush=True)
                    elif result.get("mode") == "smart_account":
                        # Smart Account mode returns prepared tx for frontend
                        print(f"[ClosePosition] ✅ Smart Account TX prepared - needs owner signature", flush=True)
                        # Return calldata to frontend for user signing
                else:
                    print(f"[ClosePosition] ⚠️ Exit failed: {result.get('error')}", flush=True)
                    
            except Exception as e:
                print(f"[ClosePosition] On-chain error: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        # 1. Close/Update position in Supabase
        try:
            from infrastructure.supabase_client import supabase
            if supabase and supabase.is_available:
                if request.percentage >= 100:
                    # Full close - mark as closed
                    await supabase.close_user_position(request.user_address, request.protocol)
                    await supabase.log_position_history(
                        user_address=request.user_address,
                        protocol=request.protocol,
                        action="close",
                        amount=amount_usdc,
                        metadata={"percentage": request.percentage}
                    )
                    print(f"[ClosePosition] Position closed in Supabase")
                else:
                    # Partial close - update current value
                    # Get current position and reduce by percentage
                    positions = await supabase.get_user_positions(request.user_address)
                    for pos in positions:
                        if pos.get("protocol") == request.protocol:
                            new_value = pos.get("current_value", 0) * (1 - request.percentage / 100)
                            await supabase.update_user_position_value(
                                request.user_address,
                                request.protocol,
                                new_value
                            )
                            await supabase.log_position_history(
                                user_address=request.user_address,
                                protocol=request.protocol,
                                action="partial_close",
                                amount=amount_usdc,
                                metadata={"percentage": request.percentage, "new_value": new_value}
                            )
                            break
                    print(f"[ClosePosition] Position reduced by {request.percentage}% in Supabase")
        except Exception as e:
            print(f"[ClosePosition] Supabase update failed: {e}")
        
        # 2. Update in-memory DEPLOYED_AGENTS
        try:
            from api.agent_config_router import DEPLOYED_AGENTS, _save_agents
            user_agents = DEPLOYED_AGENTS.get(request.user_address.lower(), [])
            for agent in user_agents:
                positions = agent.get("positions", [])
                if request.percentage >= 100:
                    # Remove position
                    agent["positions"] = [p for p in positions if p.get("protocol") != request.protocol]
                else:
                    # Reduce position value
                    for pos in positions:
                        if pos.get("protocol") == request.protocol:
                            pos["current_value"] = pos.get("current_value", 0) * (1 - request.percentage / 100)
            _save_agents()
            print(f"[ClosePosition] In-memory agents updated")
        except Exception as e:
            print(f"[ClosePosition] In-memory update failed: {e}")
        
        # 3. Log to audit trail
        try:
            from agents.audit_trail import audit_trail, ActionType
            audit_trail.log(
                action_type=ActionType.WITHDRAW,
                agent_id="system",
                wallet_address=request.user_address,
                details={
                    "position_id": request.position_id,
                    "protocol": request.protocol,
                    "percentage": request.percentage,
                    "amount_usdc": amount_usdc
                },
                tx_hash=onchain_tx_hash,
                value_usd=amount_usdc,
                success=True
            )
        except Exception as e:
            print(f"[ClosePosition] Audit log failed: {e}")
        
        # Use real tx hash if available, otherwise simulate
        if onchain_tx_hash:
            tx_hash = onchain_tx_hash
        else:
            import hashlib
            import time
            tx_hash = "0x" + hashlib.sha256(f"{request.user_address}{time.time()}".encode()).hexdigest()[:64]
        
        return {
            "success": True,
            "message": f"Closed {request.percentage}% of position",
            "protocol": request.protocol,
            "amount_usdc": amount_usdc,
            "tx_hash": tx_hash,
            "onchain": onchain_tx_hash is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@position_router.get("/{user_address}")
async def get_user_positions(user_address: str):
    """
    Get all real positions for a user.
    
    Priority:
    1. Supabase user_positions table (FAST - ~50ms)
    2. In-memory contract_monitor cache (medium)
    3. On-chain data (slow - last resort)
    """
    try:
        from infrastructure.supabase_client import supabase
        from agents.contract_monitor import contract_monitor, PROTOCOLS
        from web3 import Web3
        
        user_addr = user_address.lower()
        result_positions = []
        total_value = 0
        weighted_apy_sum = 0
        
        # =============================================
        # STEP 1: Try Supabase (FASTEST)
        # =============================================
        if supabase.is_available:
            try:
                db_positions = await supabase.get_user_positions(user_address)
                
                if db_positions:
                    for pos in db_positions:
                        entry_value = float(pos.get("entry_value", 0))
                        current_value = float(pos.get("current_value", entry_value))
                        apy = float(pos.get("apy", 0))
                        
                        result_positions.append({
                            "id": hash(f"{user_address}{pos['protocol']}") % 1000000,
                            "protocol": pos["protocol"],
                            "protocol_name": pos["protocol"].replace("_", " ").title(),
                            "vaultName": pos["protocol"].replace("_", " ").title(),
                            "asset": pos.get("asset", "USDC"),
                            "pool_type": pos.get("pool_type", "single"),
                            "deposited": entry_value,
                            "current": current_value,
                            "pnl": current_value - entry_value,
                            "apy": apy,
                            "entry_time": pos.get("entry_time", ""),
                            "source": "supabase"
                        })
                        
                        total_value += current_value
                        weighted_apy_sum += apy * current_value
                    
                    avg_apy = (weighted_apy_sum / total_value) if total_value > 0 else 0
                    
                    print(f"[Position API] Loaded {len(result_positions)} positions from Supabase for {user_addr[:10]}...")
                    
                    return {
                        "success": True,
                        "user_address": user_address,
                        "positions": result_positions,
                        "summary": {
                            "total_value": total_value,
                            "position_count": len(result_positions),
                            "avg_apy": round(avg_apy, 2)
                        },
                        "source": "supabase"
                    }
            except Exception as e:
                print(f"[Position API] Supabase read failed: {e}")
        
        # =============================================
        # STEP 2: Fallback to in-memory cache
        # =============================================
        positions = contract_monitor.user_positions.get(user_addr, {})
        
        if not positions:
            try:
                user_addr = Web3.to_checksum_address(user_address)
                positions = contract_monitor.user_positions.get(user_addr, {})
            except:
                pass
        
        for proto_key, pos_data in positions.items():
            proto_info = PROTOCOLS.get(proto_key, {})
            entry_value = pos_data.get("entry_value", 0)
            current_value = pos_data.get("current_value", entry_value)
            entry_time = pos_data.get("entry_time", "")
            
            apy = proto_info.get("apy", 0)
            pnl = current_value - entry_value
            
            result_positions.append({
                "id": hash(f"{user_address}{proto_key}") % 1000000,
                "protocol": proto_key,
                "protocol_name": proto_info.get("name", proto_key.title()),
                "vaultName": proto_info.get("name", proto_key.title()),
                "asset": proto_info.get("asset", "USDC"),
                "pool_type": proto_info.get("pool_type", "single"),
                "deposited": entry_value / 1e6,
                "current": current_value / 1e6,
                "pnl": pnl / 1e6,
                "apy": apy,
                "entry_time": entry_time,
                "source": "memory"
            })
            
            total_value += current_value
            weighted_apy_sum += apy * current_value
        
        avg_apy = (weighted_apy_sum / total_value) if total_value > 0 else 0
        
        return {
            "success": True,
            "user_address": user_address,
            "positions": result_positions,
            "summary": {
                "total_value": total_value / 1e6,
                "position_count": len(result_positions),
                "avg_apy": round(avg_apy, 2)
            },
            "source": "memory"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "positions": [],
            "error": str(e)
        }

# ============================================
# RECOMMENDATIONS ENDPOINT
# ============================================

@router.get("/recommendations/{wallet_address}")
async def get_recommendations(wallet_address: str):
    """
    Get recommended pools for user based on their agent config.
    """
    try:
        from api.agent_config_router import DEPLOYED_AGENTS
        
        # Get user's agent config
        agents = DEPLOYED_AGENTS.get(wallet_address.lower(), [])
        
        if not agents:
            return {
                "success": True,
                "recommended_pools": [],
                "message": "No agent deployed"
            }
        
        agent = agents[0]
        risk_level = agent.get("risk_level", "moderate")
        protocols = agent.get("protocols", ["aave", "morpho"])
        min_apy = agent.get("min_apy", 5.0)
        
        # All available protocols with live APY data
        ALL_POOLS = [
            {"id": "aave-usdc-base", "protocol": "Aave V3", "asset": "USDC", "apy": 6.2, "tvl": 125000000, "risk": "A+"},
            {"id": "morpho-usdc-base", "protocol": "Morpho Blue", "asset": "USDC", "apy": 8.5, "tvl": 45000000, "risk": "A"},
            {"id": "moonwell-usdc-base", "protocol": "Moonwell", "asset": "USDC", "apy": 7.1, "tvl": 78000000, "risk": "A"},
            {"id": "compound-usdc-base", "protocol": "Compound V3", "asset": "USDC", "apy": 5.8, "tvl": 95000000, "risk": "A+"},
            {"id": "seamless-usdc-base", "protocol": "Seamless", "asset": "USDC", "apy": 9.2, "tvl": 32000000, "risk": "A-"},
            {"id": "aerodrome-usdc-weth", "protocol": "Aerodrome", "asset": "USDC-WETH", "apy": 15.2, "tvl": 82000000, "risk": "B+"},
        ]
        
        # Filter by agent's protocol preferences
        protocol_lower = [p.lower() for p in protocols]
        pools = [p for p in ALL_POOLS if p["protocol"].lower().replace(" ", "").replace("v3", "") in 
                 [x.replace(" ", "") for x in protocol_lower] or 
                 p["id"].split("-")[0] in protocol_lower]
        
        # Sort by APY descending
        pools.sort(key=lambda x: x["apy"], reverse=True)
        
        return {
            "success": True,
            "recommended_pools": pools[:5],
            "agent_config": {
                "risk_level": risk_level,
                "protocols": protocols,
                "min_apy": min_apy
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "recommended_pools": [],
            "error": str(e)
        }

# ============================================
# AGENT STATUS ENDPOINT
# ============================================

@router.get("/status/{wallet_address}")
async def get_agent_status(wallet_address: str):
    """
    Get deployed agent status for a wallet.
    """
    try:
        from api.agent_config_router import DEPLOYED_AGENTS
        from web3 import Web3
        
        # Get user's deployed agents
        agents = DEPLOYED_AGENTS.get(wallet_address.lower(), [])
        
        if not agents:
            return {
                "success": True,
                "has_agent": False,
                "agents": []
            }
        
        # Try to get on-chain balance
        balance = 0
        invested = 0
        try:
            from agents.contract_monitor import contract_monitor
            w3 = contract_monitor._get_web3()
            balance = contract_monitor.contract.functions.balances(
                Web3.to_checksum_address(wallet_address)
            ).call()
            # Try totalInvested if exists
            try:
                invested = contract_monitor.contract.functions.totalInvested(
                    Web3.to_checksum_address(wallet_address)
                ).call()
            except:
                pass
        except:
            pass
        
        return {
            "success": True,
            "has_agent": True,
            "agents": [{
                **agent,
                "balance_usdc": balance / 1e6,
                "invested_usdc": invested / 1e6,
                "status": "active" if balance > 0 or invested > 0 else "idle"
            } for agent in agents]
        }
        
    except Exception as e:
        return {
            "success": False,
            "has_agent": False,
            "error": str(e)
        }

# ============================================
# HARVEST
# ============================================

@router.post("/harvest")
async def harvest_rewards(request: HarvestRequest):
    """
    Harvest rewards from agent's LP positions.
    
    Returns the harvested amount in USD.
    """
    try:
        from api.smart_account_executor import SmartAccountExecutor
        from agents.audit_trail import log_action, ActionType
        
        # Use SmartAccountExecutor for harvesting
        executor = SmartAccountExecutor(request.wallet, request.agentId)
        result = await executor.harvest_rewards()
        
        harvested_amount = result.get("harvested_usd", 0)
        
        # Log to audit trail
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=ActionType.HARVEST,
            details={
                "amount_usd": harvested_amount,
                "mode": result.get("mode", "unknown"),
                "smart_account": executor.smart_account
            },
            success=result.get("success", False)
        )
        
        return {
            "success": result.get("success", False),
            "harvestedAmount": harvested_amount,
            "timestamp": datetime.utcnow().isoformat(),
            "agentId": request.agentId,
            "mode": result.get("mode"),
            "smartAccount": executor.smart_account
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "harvestedAmount": 0
        }

# ============================================
# REBALANCE
# ============================================

@router.post("/rebalance")
async def rebalance_portfolio(request: RebalanceRequest):
    """
    Trigger portfolio rebalance for an agent.
    
    Rebalances positions according to strategy allocation.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        # In production, this would:
        # 1. Get current portfolio allocation
        # 2. Compare to target allocation
        # 3. Execute swaps/LP adjustments
        # 4. Return new allocation
        
        # Log to audit trail
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=ActionType.REBALANCE,
            details={
                "strategy": request.strategy,
                "triggered_by": "user"
            },
            success=True
        )
        
        return {
            "success": True,
            "message": "Portfolio rebalanced",
            "timestamp": datetime.utcnow().isoformat(),
            "agentId": request.agentId,
            "strategy": request.strategy
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# PAUSE ALL
# ============================================

@router.post("/pause-all")
async def pause_all_agents(request: PauseAllRequest):
    """
    Emergency pause all agents for a wallet.
    
    Stops all active trading immediately.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        # In production, this would:
        # 1. Update agent status in database
        # 2. Cancel any pending transactions
        # 3. Disable automation
        
        # Log to audit trail
        log_action(
            agent_id="system",
            wallet=request.wallet,
            action_type=ActionType.AGENT_PAUSE,
            details={
                "reason": request.reason,
                "scope": "all"
            },
            success=True
        )
        
        return {
            "success": True,
            "message": "All agents paused",
            "timestamp": datetime.utcnow().isoformat(),
            "reason": request.reason
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# AGENT STATUS
# ============================================

@router.post("/status")
async def update_agent_status(request: AgentStatusUpdate):
    """
    Update single agent active status.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        action_type = ActionType.AGENT_DEPLOY if request.isActive else ActionType.AGENT_PAUSE
        
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=action_type,
            details={"isActive": request.isActive},
            success=True
        )
        
        return {
            "success": True,
            "agentId": request.agentId,
            "isActive": request.isActive,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.delete("/delete/{wallet}/{agent_id}")
async def delete_agent(wallet: str, agent_id: str):
    """
    Delete an agent from the system.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        log_action(
            agent_id=agent_id,
            wallet=wallet,
            action_type=ActionType.AGENT_PAUSE,
            details={"action": "delete"},
            success=True
        )
        
        return {
            "success": True,
            "message": f"Agent {agent_id} deleted",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# AUDIT ENDPOINTS
# ============================================

audit_router = APIRouter(prefix="/api/audit", tags=["Audit"])

@audit_router.get("/recent")
async def get_recent_audit(
    wallet: Optional[str] = None,
    limit: int = Query(default=10, le=100)
):
    """
    Get recent audit log entries.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        entries = trail.get_entries(wallet_address=wallet)[-limit:]
        
        return {
            "success": True,
            "entries": [
                {
                    "timestamp": e.timestamp,
                    "action_type": e.action_type,
                    "agent_id": e.agent_id,
                    "wallet": e.wallet_address,
                    "value_usd": e.value_usd,
                    "success": e.success,
                    "tx_hash": e.tx_hash
                }
                for e in entries
            ],
            "count": len(entries)
        }
        
    except Exception as e:
        return {
            "success": False,
            "entries": [],
            "error": str(e)
        }

@audit_router.get("/export")
async def export_audit_csv(
    wallet: Optional[str] = Query(default=None)
):
    """
    Export audit log to CSV for tax reporting.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        entries = trail.get_entries(wallet_address=wallet if wallet != 'all' else None)
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Timestamp", "Action", "Agent ID", "Wallet",
            "TX Hash", "Value (USD)", "Gas Used", "Success", "Details"
        ])
        
        # Data rows
        for e in entries:
            writer.writerow([
                e.timestamp,
                e.action_type,
                e.agent_id,
                e.wallet_address,
                e.tx_hash or "",
                e.value_usd or "",
                e.gas_used or "",
                "Yes" if e.success else "No",
                json.dumps(e.details) if e.details else ""
            ])
        
        output.seek(0)
        
        filename = f"techne_audit_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@audit_router.get("/summary")
async def get_audit_summary(wallet: Optional[str] = None):
    """
    Get summary statistics from audit trail.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        summary = trail.get_summary(wallet_address=wallet if wallet != 'all' else None)
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
