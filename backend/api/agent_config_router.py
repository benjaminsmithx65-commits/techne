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

router = APIRouter(prefix="/api/agent", tags=["agent"])

# In-memory storage (would use DB in production)
DEPLOYED_AGENTS = {}


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
    message: Optional[str] = None


@router.post("/deploy")
async def deploy_agent(request: AgentDeployRequest):
    """
    Deploy an agent with configuration from Build UI
    """
    try:
        agent_data = {
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
        
        # Store agent
        DEPLOYED_AGENTS[request.user_address] = agent_data
        
        print(f"[AgentConfig] Agent deployed for {request.user_address}")
        print(f"[AgentConfig] Config: {json.dumps(agent_data, indent=2, default=str)}")
        
        return {
            "success": True,
            "agent_address": request.agent_address,
            "message": "Agent deployed successfully",
            "config": agent_data
        }
        
    except Exception as e:
        print(f"[AgentConfig] Deploy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_address}")
async def get_agent_status(user_address: str):
    """
    Get status of deployed agent for a user
    """
    agent = DEPLOYED_AGENTS.get(user_address)
    
    if not agent:
        return AgentStatusResponse(
            success=False,
            message="No agent found for this user"
        )
    
    return AgentStatusResponse(
        success=True,
        agent=agent
    )


@router.post("/stop/{user_address}")
async def stop_agent(user_address: str):
    """
    Stop a deployed agent
    """
    agent = DEPLOYED_AGENTS.get(user_address)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent["is_active"] = False
    agent["stopped_at"] = datetime.utcnow().isoformat()
    
    return {
        "success": True,
        "message": "Agent stopped"
    }


@router.get("/list")
async def list_agents():
    """
    List all deployed agents (admin endpoint)
    """
    return {
        "success": True,
        "count": len(DEPLOYED_AGENTS),
        "agents": list(DEPLOYED_AGENTS.values())
    }
