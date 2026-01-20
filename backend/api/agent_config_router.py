"""
Agent Configuration Router
Handles agent deployment and configuration from Build UI
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import os

# Auto-whitelist service for V4.3.2
from services.whitelist_service import get_whitelist_service

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Storage file for persistence across restarts
AGENTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "deployed_agents.json")
MAX_AGENTS_PER_WALLET = 5

def _load_agents() -> dict:
    """Load agents from file"""
    try:
        if os.path.exists(AGENTS_FILE):
            with open(AGENTS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"[AgentConfig] Failed to load agents: {e}")
    return {}

def _save_agents(agents: dict):
    """Save agents to file"""
    try:
        os.makedirs(os.path.dirname(AGENTS_FILE), exist_ok=True)
        with open(AGENTS_FILE, "w") as f:
            json.dump(agents, f, indent=2)
    except Exception as e:
        print(f"[AgentConfig] Failed to save agents: {e}")

# Load agents on startup
DEPLOYED_AGENTS = _load_agents()
print(f"[AgentConfig] Loaded {sum(len(v) for v in DEPLOYED_AGENTS.values())} agents from file")


class ProConfig(BaseModel):
    leverage: Optional[float] = 1.0
    stopLossEnabled: Optional[bool] = False
    stopLossPercent: Optional[float] = 10
    takeProfitEnabled: Optional[bool] = False
    takeProfitAmount: Optional[float] = 0
    volatilityGuard: Optional[bool] = False
    volatilityThreshold: Optional[int] = 10
    mevProtection: Optional[bool] = False
    harvestStrategy: Optional[str] = "compound"
    duration: Optional[dict] = None
    customInstructions: Optional[str] = None


class AgentDeployRequest(BaseModel):
    user_address: str
    agent_address: str
    agent_name: Optional[str] = None  # Optional custom name
    chain: str = "base"
    preset: str = "balanced-growth"
    pool_type: str = "single"
    risk_level: str = "medium"
    min_apy: float = 10
    max_apy: float = 50
    max_drawdown: float = 20
    protocols: List[str] = ["morpho", "aave", "moonwell"]
    preferred_assets: List[str] = ["USDC", "WETH"]
    max_allocation: int = 25
    vault_count: int = 5
    auto_rebalance: bool = True
    only_audited: bool = True
    is_pro_mode: bool = False
    pro_config: Optional[ProConfig] = None


class AgentStatusResponse(BaseModel):
    success: bool
    agent: Optional[dict] = None
    agents: Optional[List[dict]] = None
    message: Optional[str] = None


@router.post("/deploy")
async def deploy_agent(request: AgentDeployRequest):
    """
    Deploy an agent with configuration from Build UI
    Max 5 agents per wallet
    """
    try:
        # Get existing agents for this wallet
        user_agents = DEPLOYED_AGENTS.get(request.user_address, [])
        
        # Check max limit
        active_agents = [a for a in user_agents if a.get("is_active", False)]
        if len(active_agents) >= MAX_AGENTS_PER_WALLET:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {MAX_AGENTS_PER_WALLET} agents per wallet"
            )
        
        # Generate agent ID
        agent_id = f"agent_{len(user_agents) + 1}_{int(datetime.utcnow().timestamp())}"
        
        agent_data = {
            "id": agent_id,
            "name": request.agent_name or f"Agent #{len(user_agents) + 1}",
            "user_address": request.user_address,
            "agent_address": request.agent_address,
            "chain": request.chain,
            "preset": request.preset,
            "pool_type": request.pool_type,
            "risk_level": request.risk_level,
            "min_apy": request.min_apy,
            "max_apy": request.max_apy,
            "max_drawdown": request.max_drawdown,
            "protocols": request.protocols,
            "preferred_assets": request.preferred_assets,
            "max_allocation": request.max_allocation,
            "vault_count": request.vault_count,
            "auto_rebalance": request.auto_rebalance,
            "only_audited": request.only_audited,
            "is_pro_mode": request.is_pro_mode,
            "pro_config": request.pro_config.dict() if request.pro_config else None,
            "deployed_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "positions": [],
            "total_deposited": 0,
            "total_value": 0
        }
        
        # Add to user's agents list
        user_agents.append(agent_data)
        DEPLOYED_AGENTS[request.user_address] = user_agents
        _save_agents(DEPLOYED_AGENTS)  # Persist to file
        
        # AUTO-WHITELIST on V4.3.2 contract
        whitelist_result = {"success": False, "message": "Whitelist not attempted"}
        try:
            whitelist_svc = get_whitelist_service()
            whitelist_result = whitelist_svc.whitelist_user(request.user_address)
            print(f"[AgentConfig] Whitelist result for {request.user_address}: {whitelist_result}")
        except Exception as wl_error:
            print(f"[AgentConfig] Whitelist error (non-fatal): {wl_error}")
            whitelist_result = {"success": False, "message": str(wl_error)}
        
        print(f"[AgentConfig] Agent {agent_id} deployed for {request.user_address}")
        print(f"[AgentConfig] Total agents for user: {len(user_agents)}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "agent_address": request.agent_address,
            "message": "Agent deployed successfully",
            "config": agent_data,
            "total_agents": len(user_agents),
            "whitelist": whitelist_result  # Include whitelist status in response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AgentConfig] Deploy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_address}")
async def get_agent_status(user_address: str, agent_id: Optional[str] = None):
    """
    Get status of deployed agents for a user
    If agent_id provided, returns single agent
    """
    user_agents = DEPLOYED_AGENTS.get(user_address, [])
    
    if not user_agents:
        return AgentStatusResponse(
            success=False,
            message="No agents found for this user"
        )
    
    if agent_id:
        # Return specific agent
        agent = next((a for a in user_agents if a.get("id") == agent_id), None)
        if not agent:
            return AgentStatusResponse(success=False, message="Agent not found")
        return AgentStatusResponse(success=True, agent=agent)
    
    # Return all agents
    return {
        "success": True,
        "agents": user_agents,
        "count": len(user_agents),
        "active_count": len([a for a in user_agents if a.get("is_active")])
    }


@router.post("/stop/{user_address}/{agent_id}")
async def stop_agent(user_address: str, agent_id: str):
    """
    Stop a specific agent
    """
    user_agents = DEPLOYED_AGENTS.get(user_address, [])
    agent = next((a for a in user_agents if a.get("id") == agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent["is_active"] = False
    agent["stopped_at"] = datetime.utcnow().isoformat()
    _save_agents(DEPLOYED_AGENTS)  # Persist to file
    
    return {
        "success": True,
        "message": f"Agent {agent_id} stopped"
    }


@router.delete("/delete/{user_address}/{agent_id}")
async def delete_agent(user_address: str, agent_id: str):
    """
    Delete an agent permanently
    """
    user_agents = DEPLOYED_AGENTS.get(user_address, [])
    agent = next((a for a in user_agents if a.get("id") == agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if agent has active positions (in production, would need to withdraw first)
    if agent.get("total_value", 0) > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete agent with active positions. Withdraw funds first."
        )
    
    # Remove agent
    user_agents.remove(agent)
    DEPLOYED_AGENTS[user_address] = user_agents
    _save_agents(DEPLOYED_AGENTS)  # Persist to file
    
    print(f"[AgentConfig] Agent {agent_id} deleted for {user_address}")
    
    return {
        "success": True,
        "message": f"Agent {agent_id} deleted",
        "remaining_agents": len(user_agents)
    }


@router.get("/list")
async def list_agents():
    """
    List all deployed agents (admin endpoint)
    """
    all_agents = []
    for user_agents in DEPLOYED_AGENTS.values():
        all_agents.extend(user_agents)
    
    return {
        "success": True,
        "total_users": len(DEPLOYED_AGENTS),
        "total_agents": len(all_agents),
        "agents": all_agents
    }


@router.get("/recommendations/{user_address}")
async def get_recommendations(user_address: str, agent_id: Optional[str] = None):
    """
    Get recommended pools for a deployed agent
    Triggers a scan if not done recently
    """
    user_agents = DEPLOYED_AGENTS.get(user_address, [])
    
    if not user_agents:
        return {
            "success": False,
            "message": "No agents found"
        }
    
    # Get specific agent or first active one
    if agent_id:
        agent = next((a for a in user_agents if a.get("id") == agent_id), None)
    else:
        agent = next((a for a in user_agents if a.get("is_active")), None)
    
    if not agent:
        return {
            "success": False,
            "message": "No active agent found"
        }
    
    # Try to run executor scan
    try:
        from agents.strategy_executor import strategy_executor
        await strategy_executor.execute_agent_strategy(agent)
    except Exception as e:
        print(f"[AgentConfig] Scan error: {e}")
    
    return {
        "success": True,
        "agent_id": agent.get("id"),
        "agent_address": agent.get("agent_address"),
        "recommended_pools": agent.get("recommended_pools", []),
        "last_scan": agent.get("last_scan"),
        "config": {
            "preset": agent.get("preset"),
            "risk_level": agent.get("risk_level"),
            "protocols": agent.get("protocols"),
            "apy_range": [agent.get("min_apy"), agent.get("max_apy")]
        }
    }
