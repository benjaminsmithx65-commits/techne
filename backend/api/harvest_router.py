"""
Public Harvest API Router
Allows anyone to trigger harvesting and earn executor rewards.
Based on Revert Finance Compoundor pattern.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/harvest", tags=["Harvest"])


class PublicHarvestRequest(BaseModel):
    """Request to execute harvest for a user's positions"""
    user_address: str
    protocol: Optional[str] = None  # If None, harvest all protocols


class HarvestResponse(BaseModel):
    """Response from harvest execution"""
    success: bool
    user: str
    harvested_amount: float
    executor_reward: float
    message: str


@router.post("/execute", response_model=HarvestResponse)
async def execute_public_harvest(request: PublicHarvestRequest):
    """
    Execute harvest for a user's positions.
    
    Anyone can call this endpoint to trigger harvesting.
    The caller (executor) earns 1% of the harvested yield as reward.
    
    This incentivizes decentralized harvesting without relying on
    a centralized backend to trigger compounding.
    """
    from agents.contract_monitor import contract_monitor
    from agents.executor_rewards import executor_rewards
    from api.agent_config_router import DEPLOYED_AGENTS
    
    user = request.user_address.lower()
    
    # Get user's agent config
    agent_config = None
    for u, agents in DEPLOYED_AGENTS.items():
        if u.lower() == user and agents:
            agent_config = agents[0]
            break
    
    if not agent_config:
        raise HTTPException(status_code=404, detail="No deployed agent found for user")
    
    # Check if user has positions
    positions = contract_monitor.user_positions.get(user, {})
    if not positions:
        raise HTTPException(status_code=404, detail="No positions to harvest")
    
    # Filter by protocol if specified
    if request.protocol:
        if request.protocol not in positions:
            raise HTTPException(status_code=404, detail=f"No position in {request.protocol}")
    
    # Execute harvest
    try:
        await contract_monitor.execute_auto_harvest(user, agent_config)
        
        # Calculate total yield harvested (simplified)
        total_yield = 0
        for proto_key, pos_data in positions.items():
            if request.protocol and proto_key != request.protocol:
                continue
            entry = pos_data.get("entry_value", 0)
            current = pos_data.get("current_value", entry)
            total_yield += max(0, current - entry)
        
        total_yield_usdc = total_yield / 1e6
        
        # Get executor reward stats
        executor_reward = total_yield_usdc * 0.01  # 1%
        
        return HarvestResponse(
            success=True,
            user=user,
            harvested_amount=total_yield_usdc,
            executor_reward=executor_reward,
            message=f"Harvest executed. Executor earned ${executor_reward:.4f}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Harvest failed: {str(e)}")


@router.get("/stats")
async def get_harvest_stats():
    """Get executor reward system stats"""
    from agents.executor_rewards import executor_rewards
    
    stats = executor_rewards.get_stats()
    return {
        "success": True,
        "stats": stats
    }


@router.get("/pending/{executor_address}")
async def get_pending_rewards(executor_address: str):
    """Get pending rewards for an executor"""
    from agents.executor_rewards import executor_rewards
    
    pending = executor_rewards.get_pending_rewards(executor_address)
    return {
        "success": True,
        "executor": executor_address,
        "pending_rewards_usdc": pending
    }
