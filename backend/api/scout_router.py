"""
Scout Agent API Router - Advanced Intelligence Endpoints
Provides risk assessment, yield prediction, and conversational AI
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging

from agents.risk_intelligence import risk_engine, get_pool_risk, get_bulk_risk
from artisan.data_sources import get_aggregated_pools

logger = logging.getLogger("ScoutRouter")

router = APIRouter(prefix="/api/scout", tags=["Scout Intelligence"])


@router.get("/pool/{pool_id}")
async def get_pool_by_id(pool_id: str):
    """
    Fetch pool data directly from DefiLlama by pool UUID.
    Used by Verify Pools feature to bypass browser CSP restrictions.
    """
    import httpx
    
    try:
        logger.info(f"Searching for pool: {pool_id}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://yields.llama.fi/pools")
            
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="DefiLlama API unavailable")
            
            data = response.json()
            pools = data.get("data", [])
            
            # Exact match on pool ID
            pool = next((p for p in pools if p.get("pool") == pool_id), None)
            
            if pool:
                logger.info(f"Found pool: {pool.get('symbol')} on {pool.get('chain')}")
                return {"success": True, "pool": pool}
            
            # Partial match fallback
            pool = next((p for p in pools if pool_id in p.get("pool", "")), None)
            
            if pool:
                logger.info(f"Found partial match: {pool.get('symbol')}")
                return {"success": True, "pool": pool}
            
            raise HTTPException(status_code=404, detail="Pool not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pool/address/{address}")
async def get_pool_by_address(address: str):
    """
    Search for a pool by contract address in DefiLlama.
    This endpoint is used when user inputs a contract address or Aerodrome/Uniswap URL.
    """
    import httpx
    
    try:
        address = address.lower()
        logger.info(f"Searching for pool by address: {address}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://yields.llama.fi/pools")
            
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="DefiLlama API unavailable")
            
            data = response.json()
            pools = data.get("data", [])
            
            # Search for pool containing this address in pool ID
            pool = next((p for p in pools if address in p.get("pool", "").lower()), None)
            
            if pool:
                logger.info(f"Found pool by address: {pool.get('symbol')} on {pool.get('chain')}")
                return {"success": True, "pool": pool}
            
            # Also check underlyingTokens if available
            for p in pools:
                underlying = p.get("underlyingTokens", [])
                if isinstance(underlying, list):
                    for token in underlying:
                        if isinstance(token, str) and address in token.lower():
                            logger.info(f"Found pool by underlying token: {p.get('symbol')}")
                            return {"success": True, "pool": p}
            
            raise HTTPException(status_code=404, detail="Pool not found by address")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pool by address: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pool-pair")
async def get_pool_by_pair(
    token0: str = Query(..., description="First token address"),
    token1: str = Query(..., description="Second token address"),
    protocol: str = Query("", description="Optional protocol filter (e.g., aerodrome)"),
    chain: str = Query("Base", description="Chain filter (e.g., Base)")
):
    """
    Search for a pool containing both specified tokens.
    Uses GeckoTerminal for real-time data, falls back to DefiLlama.
    """
    import httpx
    from data_sources.geckoterminal import gecko_client
    
    try:
        token0 = token0.lower()
        token1 = token1.lower()
        logger.info(f"Searching for pair: {token0[:10]}... / {token1[:10]}... on {chain}")
        
        # PRIORITY 1: Try GeckoTerminal first (real-time data)
        gecko_pool = await gecko_client.search_pool_by_tokens(
            chain=chain or "base",
            token0=token0,
            token1=token1,
            dex=protocol if protocol else None
        )
        
        if gecko_pool:
            logger.info(f"Found pool via GeckoTerminal: {gecko_pool.get('name')}")
            gecko_pool["dataSource"] = "geckoterminal"
            return {"success": True, "pool": gecko_pool, "source": "geckoterminal"}
        
        logger.info("GeckoTerminal: not found, trying DefiLlama...")
        
        # PRIORITY 2: Fall back to DefiLlama
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get("https://yields.llama.fi/pools")
            
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="DefiLlama API unavailable")
            
            data = response.json()
            pools = data.get("data", [])
            
            # Filter by protocol if specified (use contains for partial match like aerodrome -> aerodrome-slipstream)
            if protocol:
                protocol_lower = protocol.lower()
                # Filter pools where protocol name contains the search term
                pools = [p for p in pools if protocol_lower in p.get("project", "").lower()]
                logger.info(f"After protocol filter: {len(pools)} pools")
            
            # Filter by chain if specified
            if chain:
                chain_lower = chain.lower()
                pools = [p for p in pools if chain_lower in p.get("chain", "").lower()]
            
            logger.info(f"Searching {len(pools)} pools for tokens: {token0[:10]}... / {token1[:10]}...")
            
            # Search for pool containing both tokens
            for p in pools:
                pool_id = (p.get("pool") or "").lower()
                underlying = p.get("underlyingTokens") or []
                underlying_lower = [str(t).lower() for t in underlying if t]
                
                # Check if both tokens are in underlyingTokens (exact match)
                has_token0 = token0 in underlying_lower
                has_token1 = token1 in underlying_lower
                
                # Also check pool ID (partial match)
                if not has_token0:
                    has_token0 = token0 in pool_id
                if not has_token1:
                    has_token1 = token1 in pool_id
                
                if has_token0 and has_token1:
                    logger.info(f"Found pair pool via DefiLlama: {p.get('symbol')} on {p.get('chain')}")
                    p["dataSource"] = "defillama"
                    return {"success": True, "pool": p, "source": "defillama"}
            
            logger.warning(f"Pool pair not found after checking all pools")
            
            raise HTTPException(status_code=404, detail="Pool pair not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pool by pair: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/{pool_id}")
async def get_risk_score(pool_id: str):
    """
    Get comprehensive risk assessment for a specific pool.
    
    Returns:
        Risk score (0-100), risk level, factor breakdown, warnings
    """
    try:
        # For now, fetch pool data from aggregator
        # In production, would lookup by pool_id from database
        result = await get_aggregated_pools(
            chain="Base",
            min_tvl=0,
            limit=100,
            blur=False
        )
        
        pools = result.get("combined", [])
        pool = next((p for p in pools if p.get("id") == pool_id), None)
        
        if not pool:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        risk_data = await get_pool_risk(pool)
        return risk_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk")
async def get_bulk_risk_scores(
    chain: str = Query("all", description="Chain to filter"),
    limit: int = Query(20, description="Max pools to analyze")
):
    """
    Get risk assessments for multiple pools.
    """
    try:
        chains = [chain.capitalize()] if chain != "all" else ["Base", "Ethereum", "Solana"]
        
        all_pools = []
        for c in chains:
            result = await get_aggregated_pools(
                chain=c,
                min_tvl=100000,
                limit=limit,
                blur=False
            )
            all_pools.extend(result.get("combined", []))
        
        # Get risk scores for all pools
        risk_scores = await get_bulk_risk(all_pools[:limit])
        
        # Sort by risk score (safest first)
        risk_scores.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        
        return {
            "count": len(risk_scores),
            "pools": risk_scores
        }
        
    except Exception as e:
        logger.error(f"Error getting bulk risk scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/protocol/{project}")
async def get_protocol_risk(project: str):
    """
    Get risk assessment for a specific protocol (across all its pools).
    """
    try:
        # Create a mock pool to get protocol-level scoring
        mock_pool = {
            "project": project,
            "tvl": 100_000_000,  # Assume large TVL for protocol-level
            "apy": 5.0,         # Conservative APY estimate
            "chain": "Unknown"
        }
        
        risk_data = await get_pool_risk(mock_pool)
        
        # Remove pool-specific fields
        risk_data["pool_id"] = None
        risk_data["note"] = "Protocol-level assessment (not pool-specific)"
        
        return risk_data
        
    except Exception as e:
        logger.error(f"Error getting protocol risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity: high, medium, low"),
    hours: int = Query(24, description="Alerts from last N hours")
):
    """
    Get active risk alerts.
    """
    try:
        alerts = risk_engine.get_active_alerts(max_age_hours=hours)
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        
        return {
            "count": len(alerts),
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan")
async def trigger_risk_scan(
    chain: str = Query("all", description="Chain to scan")
):
    """
    Trigger a risk scan and generate alerts.
    """
    try:
        chains = [chain.capitalize()] if chain != "all" else ["Base", "Ethereum", "Solana"]
        
        all_pools = []
        for c in chains:
            result = await get_aggregated_pools(
                chain=c,
                min_tvl=100000,
                limit=50,
                blur=False
            )
            all_pools.extend(result.get("combined", []))
        
        # Check for alerts
        new_alerts = await risk_engine.check_for_alerts(all_pools)
        
        return {
            "pools_scanned": len(all_pools),
            "new_alerts": len(new_alerts),
            "alerts": new_alerts
        }
        
    except Exception as e:
        logger.error(f"Error during risk scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# YIELD PREDICTION (Phase 2 - LIVE)
# ==========================================

@router.get("/predict/{pool_id}")
async def get_yield_prediction(
    pool_id: str,
    days: int = Query(7, description="Days ahead to predict (7, 14, or 30)")
):
    """
    Get AI-powered yield prediction for a pool.
    
    Uses historical data from DefiLlama to:
    - Analyze APY trends (7, 14, 30 day windows)
    - Forecast future yields using linear regression + mean reversion
    - Calculate confidence based on data quality and volatility
    - Generate actionable recommendations
    """
    try:
        from agents.yield_predictor import predict_yield
        
        # Fetch pool data
        result = await get_aggregated_pools(
            chain="Base",
            min_tvl=0,
            limit=100,
            blur=False
        )
        
        pools = result.get("combined", [])
        pool = next((p for p in pools if p.get("id") == pool_id), None)
        
        if not pool:
            # Try to create minimal pool object for prediction
            pool = {"id": pool_id, "apy": 5.0, "tvl": 1000000}
        
        prediction = await predict_yield(pool, days)
        return prediction
        
    except Exception as e:
        logger.error(f"Error getting yield prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict")
async def get_bulk_predictions(
    chain: str = Query("all", description="Chain to filter"),
    limit: int = Query(10, description="Max pools to predict"),
    days: int = Query(7, description="Days ahead")
):
    """
    Get AI yield predictions for multiple pools.
    """
    try:
        from agents.yield_predictor import batch_predict
        
        chains = [chain.capitalize()] if chain != "all" else ["Base", "Ethereum", "Solana"]
        
        all_pools = []
        for c in chains:
            result = await get_aggregated_pools(
                chain=c,
                min_tvl=100000,
                limit=limit,
                blur=False
            )
            all_pools.extend(result.get("combined", []))
        
        predictions = await batch_predict(all_pools[:limit], days)
        
        # Sort by predicted trend (rising first)
        predictions.sort(
            key=lambda x: 1 if x.get("trend", {}).get("direction") == "rising" else 0, 
            reverse=True
        )
        
        return {
            "count": len(predictions),
            "days_ahead": days,
            "predictions": predictions
        }
        
    except Exception as e:
        logger.error(f"Error getting bulk predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# CONVERSATIONAL AI (Phase 3 - LIVE)
# ==========================================

@router.post("/chat")
async def scout_chat_endpoint(query: str = Query(..., description="Natural language query")):
    """
    Natural language interface to Scout Agent.
    
    Supports queries like:
    - "Find USDC pools on Solana with >5% APY"
    - "What's the safest stablecoin yield?"
    - "Compare Aave vs Compound"
    - "Is Morpho safe?"
    - "What is impermanent loss?"
    """
    try:
        from agents.scout_chat import chat_query
        
        response = await chat_query(query)
        return response
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return {
            "intent": "error",
            "success": False,
            "text": f"Sorry, I encountered an error: {str(e)}",
            "suggestions": [
                "Find stablecoin pools",
                "What's the safest yield?",
                "Compare Aave vs Compound"
            ]
        }


@router.get("/chat/suggestions")
async def get_chat_suggestions():
    """
    Get suggested queries for the chat interface.
    """
    return {
        "categories": {
            "discovery": [
                "Find USDC pools on Solana",
                "Show me high-yield ETH pools",
                "List stablecoin pools on Base"
            ],
            "comparison": [
                "Compare Aave vs Compound",
                "Morpho vs Aave for USDC",
                "Which is safer: Kamino or Marginfi?"
            ],
            "recommendations": [
                "What's the safest yield right now?",
                "Best stablecoin pool for $10k",
                "Recommend a low-risk pool"
            ],
            "education": [
                "What is APY?",
                "Explain impermanent loss",
                "What is TVL?"
            ],
            "risk": [
                "Is Aave safe?",
                "Check Compound risk",
                "Is this pool audited?"
            ]
        }
    }
