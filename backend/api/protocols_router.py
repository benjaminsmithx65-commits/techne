"""
Protocols API Router
Returns available protocols for frontend with pool_type filtering
"""

from fastapi import APIRouter, Query
from typing import Optional, List

router = APIRouter(prefix="/api/protocols", tags=["Protocols"])


@router.get("")
async def get_protocols(
    pool_type: Optional[str] = Query(None, description="Filter: 'single', 'dual', or 'all'"),
    chain: str = Query("base", description="Chain to get protocols for")
):
    """
    Get all available protocols for the builder.
    
    Filters:
    - pool_type: 'single' (lending), 'dual' (LP), or 'all'
    - chain: currently only 'base' supported
    """
    from agents.contract_monitor import PROTOCOLS
    
    result = []
    
    for key, proto in PROTOCOLS.items():
        # Filter by pool_type if specified
        if pool_type and pool_type != 'all':
            if proto.get("pool_type") != pool_type:
                continue
        
        result.append({
            "id": key,
            "name": proto.get("name", key.title()),
            "address": proto.get("address"),
            "asset": proto.get("asset", "USDC"),
            "pool_type": proto.get("pool_type", "single"),
            "risk_level": proto.get("risk_level", "medium"),
            "apy": proto.get("apy", 0),
            "tvl": proto.get("tvl", 0),
            "volatility": proto.get("volatility", 5.0),
            "audited": proto.get("audited", False),
            "implemented": proto.get("implemented", True),  # Default True for backwards compat
            "is_lending": proto.get("is_lending", False),
            "is_stableswap": proto.get("is_stableswap", False),
            "is_leveraged_farm": proto.get("is_leveraged_farm", False),
            "is_reward_aggregator": proto.get("is_reward_aggregator", False),
            "is_weighted_pool": proto.get("is_weighted_pool", False),
            "max_leverage": proto.get("max_leverage", None),
            "chain": chain
        })
    
    # Sort by APY desc
    result.sort(key=lambda x: x["apy"], reverse=True)
    
    return {
        "success": True,
        "chain": chain,
        "pool_type_filter": pool_type or "all",
        "count": len(result),
        "protocols": result
    }


@router.get("/single")
async def get_single_sided():
    """Get single-sided (lending) protocols only"""
    return await get_protocols(pool_type="single")


@router.get("/dual")
async def get_dual_sided():
    """Get dual-sided (LP) protocols only"""
    return await get_protocols(pool_type="dual")


@router.get("/stats")
async def get_protocol_stats():
    """Get aggregated stats for all protocols"""
    from agents.contract_monitor import PROTOCOLS
    
    single_count = sum(1 for p in PROTOCOLS.values() if p.get("pool_type") == "single")
    dual_count = sum(1 for p in PROTOCOLS.values() if p.get("pool_type") == "dual")
    
    total_tvl = sum(p.get("tvl", 0) for p in PROTOCOLS.values())
    avg_apy_single = sum(p.get("apy", 0) for p in PROTOCOLS.values() if p.get("pool_type") == "single") / max(single_count, 1)
    avg_apy_dual = sum(p.get("apy", 0) for p in PROTOCOLS.values() if p.get("pool_type") == "dual") / max(dual_count, 1)
    
    return {
        "success": True,
        "stats": {
            "total_protocols": len(PROTOCOLS),
            "single_sided": single_count,
            "dual_sided": dual_count,
            "total_tvl": total_tvl,
            "avg_apy_single": round(avg_apy_single, 2),
            "avg_apy_dual": round(avg_apy_dual, 2)
        }
    }
