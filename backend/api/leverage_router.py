"""
Smart Loop API Router
Exposes leverage loop functionality via REST API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/leverage", tags=["Leverage"])


class LeverageRequest(BaseModel):
    """Request to create leveraged position"""
    user_address: str
    amount_usdc: float  # In USDC (e.g., 1000.0)
    target_leverage: float  # 1.0 to 3.0
    on_behalf_of: Optional[str] = None


class LeverageResponse(BaseModel):
    """Response from leverage operation"""
    success: bool
    message: str
    position: Optional[dict] = None
    tx_hashes: list = []


class LoopCalculation(BaseModel):
    """Calculation preview for leverage loop"""
    initial_amount: float
    target_leverage: float
    actual_leverage: float
    total_loops: int
    final_collateral: float
    final_debt: float
    health_factor: float


@router.post("/create", response_model=LeverageResponse)
async def create_leverage_position(request: LeverageRequest):
    """
    Create a leveraged position using Smart Loop Engine
    
    - Deposits USDC as collateral
    - Borrows against it
    - Re-deposits borrowed USDC
    - Repeats until target leverage reached
    
    Safety: Maintains minimum 1.5 health factor
    """
    from agents.smart_loop_engine import smart_loop_engine
    
    # Validate leverage
    if request.target_leverage < 1.0 or request.target_leverage > 3.0:
        raise HTTPException(
            status_code=400, 
            detail="Leverage must be between 1.0x and 3.0x"
        )
    
    # Convert to USDC decimals (6)
    amount = int(request.amount_usdc * 1e6)
    
    if amount < 100_000000:  # Min $100
        raise HTTPException(
            status_code=400,
            detail="Minimum amount is $100 USDC"
        )
    
    # Execute loop
    result = await smart_loop_engine.execute_leverage_loop(
        user=request.user_address,
        amount=amount,
        target_leverage=request.target_leverage,
        on_behalf_of=request.on_behalf_of
    )
    
    if result["success"]:
        position = result["position"]
        return LeverageResponse(
            success=True,
            message=f"Leverage position created: {position.actual_leverage:.2f}x",
            position={
                "user": position.user,
                "initial_deposit": position.initial_deposit / 1e6,
                "current_collateral": position.current_collateral / 1e6,
                "current_debt": position.current_debt / 1e6,
                "leverage": position.actual_leverage,
                "health_factor": position.health_factor,
                "loop_count": position.loop_count,
                "created_at": position.created_at
            },
            tx_hashes=result.get("tx_hashes", [])
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Unknown error")
        )


@router.post("/deleverage")
async def deleverage_position(user_address: str, target_leverage: float = 1.0):
    """
    Reduce leverage on existing position
    
    - target_leverage=1.0: Fully unwind to no leverage
    - target_leverage=1.5: Reduce to 1.5x
    """
    from agents.smart_loop_engine import smart_loop_engine
    
    result = await smart_loop_engine.deleverage(user_address, target_leverage)
    
    if result["success"]:
        return {
            "success": True,
            "message": f"Deleveraged to {result['position'].actual_leverage:.2f}x",
            "health_factor": result['position'].health_factor,
            "tx_hashes": result.get("tx_hashes", [])
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@router.get("/calculate")
async def calculate_leverage(amount_usdc: float, target_leverage: float):
    """
    Preview leverage loop calculation without executing
    
    Returns:
    - Number of loops needed
    - Final collateral/debt
    - Expected health factor
    """
    from agents.smart_loop_engine import smart_loop_engine
    
    if target_leverage < 1.0 or target_leverage > 3.0:
        raise HTTPException(status_code=400, detail="Leverage must be 1.0x to 3.0x")
    
    amount = int(amount_usdc * 1e6)
    params = smart_loop_engine.calculate_loop_parameters(amount, target_leverage)
    
    return LoopCalculation(
        initial_amount=amount_usdc,
        target_leverage=target_leverage,
        actual_leverage=params["actual_leverage"],
        total_loops=params["total_loops"],
        final_collateral=params["final_collateral"] / 1e6,
        final_debt=params["final_debt"] / 1e6,
        health_factor=params["health_factor"]
    )


@router.get("/position/{user_address}")
async def get_leverage_position(user_address: str):
    """Get user's current leverage position"""
    from agents.smart_loop_engine import smart_loop_engine
    
    if user_address not in smart_loop_engine.positions:
        raise HTTPException(status_code=404, detail="No leverage position found")
    
    position = smart_loop_engine.positions[user_address]
    
    # Get fresh health factor
    hf = await smart_loop_engine._get_health_factor(user_address)
    
    return {
        "user": position.user,
        "initial_deposit": position.initial_deposit / 1e6,
        "current_collateral": position.current_collateral / 1e6,
        "current_debt": position.current_debt / 1e6,
        "leverage": position.actual_leverage,
        "health_factor": hf,
        "loop_count": position.loop_count,
        "created_at": position.created_at,
        "last_updated": position.last_updated
    }


@router.get("/positions")
async def get_all_positions():
    """Get all tracked leverage positions"""
    from agents.smart_loop_engine import smart_loop_engine
    
    positions = []
    for user, pos in smart_loop_engine.positions.items():
        positions.append({
            "user": pos.user,
            "leverage": pos.actual_leverage,
            "health_factor": pos.health_factor,
            "collateral": pos.current_collateral / 1e6,
            "debt": pos.current_debt / 1e6
        })
    
    return {"positions": positions, "count": len(positions)}


# ==========================================
# MORPHO BLUE ENDPOINTS
# Higher leverage possible (up to 5x with 86% LLTV)
# ==========================================

class MorphoLeverageRequest(BaseModel):
    """Request for Morpho Blue leverage"""
    user_address: str
    market_key: str  # e.g., "usdc_weth"
    collateral_amount: float
    target_leverage: float  # 1.0 to 5.0


@router.post("/morpho/create")
async def create_morpho_leverage(request: MorphoLeverageRequest):
    """
    Create leveraged position on Morpho Blue
    
    Higher leverage than Aave (up to 5x with 86% LLTV markets)
    """
    from agents.morpho_loop_engine import morpho_loop_engine
    
    if request.target_leverage < 1.0 or request.target_leverage > 5.0:
        raise HTTPException(
            status_code=400,
            detail="Leverage must be between 1.0x and 5.0x"
        )
    
    # Execute on Morpho
    result = await morpho_loop_engine.execute_leverage_loop(
        user=request.user_address,
        market_key=request.market_key,
        collateral_amount=int(request.collateral_amount * 1e6),
        target_leverage=request.target_leverage
    )
    
    if result["success"]:
        pos = result["position"]
        return {
            "success": True,
            "protocol": "morpho_blue",
            "message": f"Morpho leverage: {pos.actual_leverage:.2f}x",
            "position": {
                "user": pos.user,
                "market": pos.market_key,
                "collateral": pos.current_collateral,
                "debt": pos.current_debt,
                "leverage": pos.actual_leverage,
                "lltv": pos.lltv,
                "loop_count": pos.loop_count
            },
            "tx_hashes": result.get("tx_hashes", [])
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))


@router.get("/morpho/markets")
async def get_morpho_markets():
    """Get available Morpho Blue markets for leverage"""
    from agents.morpho_loop_engine import morpho_loop_engine
    
    markets = morpho_loop_engine.get_available_markets()
    return {
        "protocol": "morpho_blue",
        "chain": "base",
        "markets": markets
    }


@router.get("/morpho/calculate")
async def calculate_morpho_leverage(market_key: str, collateral: float, target_leverage: float):
    """Preview Morpho Blue leverage calculation"""
    from agents.morpho_loop_engine import morpho_loop_engine
    
    if target_leverage < 1.0 or target_leverage > 5.0:
        raise HTTPException(status_code=400, detail="Leverage must be 1.0x to 5.0x")
    
    params = morpho_loop_engine.calculate_loop_parameters(
        market_key,
        int(collateral * 1e6),
        target_leverage
    )
    
    return {
        "market": market_key,
        "initial_collateral": collateral,
        "target_leverage": target_leverage,
        "actual_leverage": params["actual_leverage"],
        "total_loops": params["total_loops"],
        "final_collateral": params["final_collateral"] / 1e6,
        "final_debt": params["final_debt"] / 1e6,
        "ltv_usage": f"{params['ltv_usage']*100:.1f}%",
        "lltv": f"{params['lltv']*100:.1f}%",
        "safety_margin": f"{params['safety_margin']*100:.1f}%"
    }


@router.get("/protocols")
async def get_available_protocols():
    """Get all available leverage protocols"""
    return {
        "protocols": [
            {
                "name": "Aave V3",
                "key": "aave",
                "chain": "base",
                "max_leverage": 3.0,
                "description": "Industry standard, lower leverage but safer"
            },
            {
                "name": "Morpho Blue",
                "key": "morpho",
                "chain": "base",
                "max_leverage": 5.0,
                "description": "Higher leverage possible with isolated markets"
            }
        ]
    }

