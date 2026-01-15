"""
Scout Agent API Router - Advanced Intelligence Endpoints
Provides risk assessment, yield prediction, and conversational AI
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging

from agents.risk_intelligence import risk_engine, get_pool_risk, get_bulk_risk
from artisan.data_sources import get_aggregated_pools
from data_sources.onchain import onchain_client

logger = logging.getLogger("ScoutRouter")

router = APIRouter(prefix="/api/scout", tags=["Scout Intelligence"])

# Token price cache (simple in-memory, expires on restart)
_price_cache = {}


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


@router.get("/resolve")
async def resolve_input(
    input: str = Query(..., description="Any input: pool address, Aerodrome URL, Uniswap URL, DexScreener URL, etc."),
    chain: str = Query("base", description="Chain name")
):
    """
    Universal input resolver using "Vacuum Cleaner" approach.
    Extracts pool address from ANY input format.
    
    Examples:
    - Raw address: 0x1234...
    - Aerodrome: https://aerodrome.finance/deposit?token0=0x...&token1=0x...
    - Uniswap: https://app.uniswap.org/pools/0x1234...
    - DexScreener: https://dexscreener.com/base/0x1234...
    """
    from api.input_resolver import input_resolver, InvalidInputError
    
    try:
        result = await input_resolver.resolve(input, chain)
        
        logger.info(f"[Resolve] Input resolved to pool {result['pool_address'][:10]}... ({result['type']})")
        
        return {
            "success": True,
            "pool_address": result["pool_address"],
            "resolution_type": result["type"],
            "protocol": result.get("protocol", "Unknown"),
            "factory": result.get("factory"),
            "tokens": result.get("tokens"),
            "stable": result.get("stable", False)
        }
        
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[Resolve] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pool-pair")
async def get_pool_by_pair(
    token0: str = Query(..., description="First token address"),
    token1: str = Query(..., description="Second token address"),
    protocol: str = Query("", description="Optional protocol filter (e.g., aerodrome)"),
    chain: str = Query("Base", description="Chain filter (e.g., Base)"),
    stable: bool = Query(False, description="True for stable pool, False for volatile")
):
    """
    Search for a pool containing both specified tokens.
    AERODROME-FIRST APPROACH: Aerodrome on-chain → GeckoTerminal → DefiLlama → Merge
    """
    import httpx
    from data_sources.geckoterminal import gecko_client
    from data_sources.aerodrome import aerodrome_client
    
    try:
        token0 = token0.lower()
        token1 = token1.lower()
        chain_lower = chain.lower() if chain else "base"
        logger.info(f"[Pool-Pair] Searching: {token0[:10]}.../{token1[:10]}... on {chain}")
        
        merged_data = {
            "token0": token0,
            "token1": token1,
            "chain": chain.capitalize() if chain else "Base",
            "sources": [],
        }
        
        # =========================================
        # STEP 0: AERODROME DIRECT (for Base chain - most accurate TVL)
        # =========================================
        if chain_lower == "base":
            try:
                aero_pool = await aerodrome_client.get_pool_by_tokens(token0, token1, stable=stable)
                if aero_pool:
                    logger.info(f"[Pool-Pair] Aerodrome direct: {aero_pool.get('symbol')}")
                    merged_data["sources"].append("aerodrome")
                    merged_data["address"] = aero_pool.get("address")
                    merged_data["symbol"] = aero_pool.get("symbol")
                    merged_data["project"] = "Aerodrome"
                    merged_data["token0_symbol"] = aero_pool.get("symbol0")
                    merged_data["token1_symbol"] = aero_pool.get("symbol1")
                    merged_data["reserve0"] = aero_pool.get("reserve0", 0)
                    merged_data["reserve1"] = aero_pool.get("reserve1", 0)
                    merged_data["stable"] = aero_pool.get("stable", False)
                    merged_data["pool_type"] = aero_pool.get("pool_type", "volatile")
                    
                    # Calculate TVL from reserves (need prices)
                    price0 = await get_token_price(aero_pool.get("symbol0", ""), token0)
                    price1 = await get_token_price(aero_pool.get("symbol1", ""), token1)
                    tvl = (aero_pool.get("reserve0", 0) * price0) + (aero_pool.get("reserve1", 0) * price1)
                    merged_data["tvl"] = tvl
                    merged_data["tvlUsd"] = tvl
                    merged_data["tvl_formatted"] = f"${tvl/1e6:.2f}M" if tvl >= 1e6 else f"${tvl/1e3:.1f}K" if tvl >= 1e3 else f"${tvl:.0f}"
                    logger.info(f"[Pool-Pair] Aerodrome TVL: ${tvl:,.0f}")
            except Exception as e:
                logger.debug(f"Aerodrome lookup failed: {e}")
        
        # =========================================
        # STEP 1: GeckoTerminal (has pool addresses, TVL, volume)
        # =========================================
        gecko_pool = None
        try:
            gecko_pool = await gecko_client.search_pool_by_tokens(
                chain=chain_lower,
                token0=token0,
                token1=token1,
                dex=protocol if protocol else None
            )
            if gecko_pool:
                logger.info(f"[Pool-Pair] GeckoTerminal found: {gecko_pool.get('name')}")
                merged_data["sources"].append("geckoterminal")
                merged_data["address"] = gecko_pool.get("address")
                merged_data["name"] = gecko_pool.get("name")
                merged_data["symbol"] = gecko_pool.get("symbol")
                merged_data["project"] = gecko_pool.get("project", "Unknown")
                merged_data["tvl"] = gecko_pool.get("tvl", 0)
                merged_data["tvlUsd"] = gecko_pool.get("tvlUsd", 0)
                merged_data["volume_24h"] = gecko_pool.get("volume_24h", 0)
                merged_data["volume_24h_formatted"] = gecko_pool.get("volume_24h_formatted", "N/A")
                merged_data["trading_fee"] = gecko_pool.get("trading_fee")
                merged_data["fee_24h_usd"] = gecko_pool.get("fee_24h_usd")
                merged_data["apy"] = gecko_pool.get("apy", 0)
                merged_data["apy_base"] = gecko_pool.get("apy_base", 0)
                merged_data["il_risk"] = gecko_pool.get("il_risk", "yes")
                merged_data["pool_type"] = gecko_pool.get("pool_type", "volatile")
        except Exception as e:
            logger.debug(f"GeckoTerminal lookup failed: {e}")
        
        # =========================================
        # STEP 2: On-chain RPC (accurate TVL from reserves)
        # =========================================
        if merged_data.get("address") and onchain_client.is_chain_available(chain_lower):
            try:
                pool_address = merged_data["address"]
                onchain_data = await onchain_client.get_any_pool_data(chain_lower, pool_address)
                
                if onchain_data:
                    logger.info(f"[Pool-Pair] On-chain data found: {onchain_data.get('pool_type')}")
                    merged_data["sources"].append("onchain")
                    merged_data["pool_type_detail"] = onchain_data.get("pool_type")
                    
                    # Calculate on-chain TVL
                    if onchain_data.get("pool_type") == "v2":
                        price0 = await get_token_price(onchain_data.get("symbol0", ""), token0)
                        price1 = await get_token_price(onchain_data.get("symbol1", ""), token1)
                        onchain_tvl = (onchain_data.get("reserve0", 0) * price0) + (onchain_data.get("reserve1", 0) * price1)
                        merged_data["tvl_onchain"] = onchain_tvl
                        # Use on-chain TVL if significantly different (>20%)
                        if onchain_tvl > 0:
                            current_tvl = merged_data.get("tvl", 0)
                            if current_tvl == 0 or abs(onchain_tvl - current_tvl) / max(onchain_tvl, current_tvl) > 0.2:
                                merged_data["tvl"] = onchain_tvl
                                merged_data["tvlUsd"] = onchain_tvl
                                logger.info(f"[Pool-Pair] Using on-chain TVL: ${onchain_tvl:,.0f}")
                    elif onchain_data.get("pool_type") == "cl":
                        price0 = await get_token_price(onchain_data.get("symbol0", ""), onchain_data.get("token0"))
                        price1 = await get_token_price(onchain_data.get("symbol1", ""), onchain_data.get("token1"))
                        onchain_tvl = (onchain_data.get("balance0", 0) * price0) + (onchain_data.get("balance1", 0) * price1)
                        merged_data["tvl_onchain"] = onchain_tvl
                        if onchain_tvl > 0:
                            current_tvl = merged_data.get("tvl", 0)
                            if current_tvl == 0 or abs(onchain_tvl - current_tvl) / max(onchain_tvl, current_tvl) > 0.2:
                                merged_data["tvl"] = onchain_tvl
                                merged_data["tvlUsd"] = onchain_tvl
                                logger.info(f"[Pool-Pair] Using CL on-chain TVL: ${onchain_tvl:,.0f}")
                    
                    # Set symbols if not already set
                    if not merged_data.get("symbol"):
                        merged_data["symbol"] = f"{onchain_data.get('symbol0', '???')}-{onchain_data.get('symbol1', '???')}"
            except Exception as e:
                logger.debug(f"On-chain lookup failed: {e}")
        
        # =========================================
        # STEP 2.5: ON-CHAIN APR FROM GAUGE (Aerodrome only)
        # =========================================
        is_aerodrome = not protocol or "aerodrome" in protocol.lower()
        if chain_lower == "base" and merged_data.get("address") and is_aerodrome:
            try:
                pool_address = merged_data["address"]
                apy_data = await aerodrome_client.get_real_time_apy(pool_address)
                
                if apy_data.get("has_gauge") and apy_data.get("yearly_rewards_usd", 0) > 0:
                    # Use accurate TVL for APR calculation
                    accurate_tvl = merged_data.get("tvl", 0)
                    yearly_rewards = apy_data.get("yearly_rewards_usd", 0)
                    
                    if accurate_tvl > 0:
                        # Recalculate APR with accurate TVL
                        onchain_apr = (yearly_rewards / accurate_tvl) * 100
                        
                        # Override GeckoTerminal/DefiLlama APY with on-chain APR
                        merged_data["apy"] = onchain_apr
                        merged_data["apy_reward"] = onchain_apr
                        merged_data["apy_onchain"] = onchain_apr
                        merged_data["gauge_address"] = apy_data.get("gauge_address")
                        merged_data["yearly_emissions_usd"] = yearly_rewards
                        merged_data["aero_price"] = apy_data.get("aero_price")
                        merged_data["epoch_end"] = apy_data.get("epoch_end")
                        merged_data["sources"].append("gauge_apy")
                        
                        logger.info(f"[Pool-Pair] On-chain APR: {onchain_apr:.2f}% (emissions ${yearly_rewards:,.0f} / TVL ${accurate_tvl:,.0f})")
            except Exception as e:
                logger.debug(f"On-chain APR calculation failed: {e}")
        
        # =========================================
        # STEP 3: DefiLlama (historical APY, more metadata)
        # =========================================
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get("https://yields.llama.fi/pools")
                if response.status_code == 200:
                    data = response.json()
                    pools = data.get("data", [])
                    
                    # Filter by chain
                    pools = [p for p in pools if chain_lower in p.get("chain", "").lower()]
                    
                    # Search for matching pool
                    for p in pools:
                        pool_id = (p.get("pool") or "").lower()
                        underlying = [str(t).lower() for t in (p.get("underlyingTokens") or []) if t]
                        
                        has_token0 = token0 in underlying or token0 in pool_id
                        has_token1 = token1 in underlying or token1 in pool_id
                        
                        if has_token0 and has_token1:
                            logger.info(f"[Pool-Pair] DefiLlama found: {p.get('symbol')}")
                            merged_data["sources"].append("defillama")
                            
                            # Add APY from DefiLlama if not already set or if DefiLlama has higher value
                            defillama_apy = p.get("apy", 0)
                            if defillama_apy and (not merged_data.get("apy") or defillama_apy > merged_data.get("apy", 0)):
                                merged_data["apy"] = defillama_apy
                                merged_data["apy_base"] = p.get("apyBase", 0)
                                merged_data["apy_reward"] = p.get("apyReward", 0)
                            
                            # Add TVL change
                            merged_data["tvl_change_1d"] = p.get("apyPct1D", 0)
                            merged_data["tvl_change_7d"] = p.get("apyPct7D", 0)
                            
                            # Set project if not already set
                            if not merged_data.get("project") or merged_data.get("project") == "Unknown":
                                merged_data["project"] = p.get("project", "Unknown")
                            
                            break
        except Exception as e:
            logger.debug(f"DefiLlama lookup failed: {e}")
        
        # =========================================
        # STEP 4: Finalize merged data
        # =========================================
        if not merged_data.get("sources"):
            raise HTTPException(status_code=404, detail="Pool not found on any data source")
        
        # Format TVL
        tvl = merged_data.get("tvl", 0)
        merged_data["tvl_formatted"] = f"${tvl/1e6:.2f}M" if tvl >= 1e6 else f"${tvl/1e3:.1f}K" if tvl >= 1e3 else f"${tvl:.0f}"
        
        # Calculate estimated APR from trading fee if no APY
        if not merged_data.get("apy") and merged_data.get("trading_fee"):
            # Simple estimation: trading_fee * 365 (daily trading volume basis)
            merged_data["apy_estimated"] = merged_data["trading_fee"] * 365
        
        merged_data["dataSource"] = "+".join(merged_data["sources"])
        
        logger.info(f"[Pool-Pair] Final: TVL=${tvl:,.0f}, APY={merged_data.get('apy', 0):.2f}%, sources={merged_data['dataSource']}")
        
        return {"success": True, "pool": merged_data, "source": merged_data["dataSource"]}
        
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


# ============================================
# ON-CHAIN DATA ENDPOINTS
# ============================================

async def get_token_price(symbol: str, address: str = None) -> float:
    """
    Get token price in USD using CoinGecko API.
    Falls back to known prices for common tokens.
    """
    import httpx
    
    symbol = symbol.upper()
    
    # Known token prices (fallback)
    KNOWN_PRICES = {
        "WETH": 3400.0,
        "ETH": 3400.0,
        "USDC": 1.0,
        "USDT": 1.0,
        "DAI": 1.0,
        "WBTC": 98000.0,
        "BTC": 98000.0,
        "AERO": 1.2,  # Aerodrome token
        "VIRTUAL": 1.5,  # Approx price
    }
    
    # Check cache first
    cache_key = f"{symbol}_{address or ''}"
    if cache_key in _price_cache:
        return _price_cache[cache_key]
    
    # Try CoinGecko API
    try:
        # Map common symbols to CoinGecko IDs
        id_map = {
            "WETH": "ethereum",
            "ETH": "ethereum",
            "USDC": "usd-coin",
            "USDT": "tether",
            "DAI": "dai",
            "WBTC": "wrapped-bitcoin",
            "CBETH": "coinbase-wrapped-staked-eth",
            "WSTETH": "wrapped-steth",
            "RETH": "rocket-pool-eth",
            "AERO": "aerodrome-finance",
        }
        
        coin_id = id_map.get(symbol)
        if coin_id:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if coin_id in data:
                        price = data[coin_id]["usd"]
                        _price_cache[cache_key] = price
                        return price
    except Exception as e:
        logger.warning(f"CoinGecko price fetch failed for {symbol}: {e}")
    
    # Fallback to known prices
    if symbol in KNOWN_PRICES:
        return KNOWN_PRICES[symbol]
    
    # Unknown token - estimate based on address if available
    return 0.0


@router.get("/onchain-tvl")
async def get_onchain_tvl(
    pool_address: str = Query(..., description="Pool contract address"),
    chain: str = Query("base", description="Chain name (base, ethereum, etc.)")
):
    """
    Get real-time TVL for a pool.
    Priority: GeckoTerminal API (works for CL pools) -> On-chain reserves (V2 pools)
    """
    from data_sources.geckoterminal import gecko_client
    
    try:
        chain = chain.lower()
        pool_address = pool_address.lower()
        
        logger.info(f"Fetching TVL for {pool_address} on {chain}")
        
        # PRIORITY 1: Try GeckoTerminal (works for all pool types including CL)
        gecko_data = await gecko_client.get_pool_by_address(chain, pool_address)
        
        if gecko_data and gecko_data.get("tvl", 0) > 0:
            tvl = gecko_data["tvl"]
            logger.info(f"GeckoTerminal TVL for {pool_address}: ${tvl:,.2f}")
            return {
                "success": True,
                "tvl": tvl,
                "tvl_formatted": f"${tvl/1e6:.2f}M" if tvl >= 1e6 else f"${tvl/1e3:.1f}K" if tvl >= 1e3 else f"${tvl:.0f}",
                "volume_24h": gecko_data.get("volume_24h", 0),
                "volume_24h_formatted": gecko_data.get("volume_24h_formatted", "N/A"),
                "apy_estimated": gecko_data.get("apy", 0),
                "name": gecko_data.get("name", ""),
                "source": "geckoterminal",
                "chain": chain
            }
        
        logger.info("GeckoTerminal: no data, trying on-chain...")
        
        # PRIORITY 2: Try on-chain reserves (V2 style pools)
        if not onchain_client.is_chain_available(chain):
            return {
                "success": False,
                "error": f"Chain {chain} RPC not available",
                "fallback": True
            }
        
        reserves = await onchain_client.get_lp_reserves(chain, pool_address)
        
        if not reserves:
            return {
                "success": False,
                "error": "Could not fetch pool data from any source",
                "fallback": True
            }
        
        # Get token prices
        price0 = await get_token_price(reserves["symbol0"], reserves["token0"])
        price1 = await get_token_price(reserves["symbol1"], reserves["token1"])
        
        # Calculate TVL
        tvl_token0 = reserves["reserve0"] * price0
        tvl_token1 = reserves["reserve1"] * price1
        total_tvl = tvl_token0 + tvl_token1
        
        logger.info(f"On-chain TVL for {pool_address}: ${total_tvl:,.2f}")
        
        return {
            "success": True,
            "tvl": total_tvl,
            "tvl_formatted": f"${total_tvl/1e6:.2f}M" if total_tvl >= 1e6 else f"${total_tvl/1e3:.1f}K" if total_tvl >= 1e3 else f"${total_tvl:.0f}",
            "reserves": {
                "token0": {
                    "symbol": reserves["symbol0"],
                    "amount": reserves["reserve0"],
                    "price_usd": price0,
                    "value_usd": tvl_token0
                },
                "token1": {
                    "symbol": reserves["symbol1"],
                    "amount": reserves["reserve1"],
                    "price_usd": price1,
                    "value_usd": tvl_token1
                }
            },
            "source": "onchain",
            "chain": chain
        }
        
    except Exception as e:
        logger.error(f"TVL fetch error: {e}")
        return {
            "success": False,
            "error": str(e),
            "fallback": True
        }


@router.get("/chains-status")
async def get_chains_status():
    """
    Get status of all RPC connections.
    """
    return {
        "available_chains": onchain_client.get_available_chains(),
        "all_chains": ["base", "ethereum", "arbitrum", "optimism", "polygon"]
    }


# ============================================
# VERIFY-RPC (RPC-First Pool Verification)
# ============================================

@router.get("/verify-rpc")
async def verify_pool_rpc_first(
    pool_address: str = Query(..., description="Pool contract address"),
    chain: str = Query("base", description="Chain name")
):
    """
    🔗 RPC-First Pool Verification.
    
    Unlike verify-any which uses SmartRouter (GeckoTerminal→DefiLlama→RPC),
    this endpoint goes DIRECTLY to on-chain RPC for pool data.
    
    Priority order:
    1. On-chain RPC (get pool reserves, tokens, factory)
    2. Enrich with GeckoTerminal for volume/APY (optional)
    3. Security checks (GoPlus, audit, whale analysis)
    
    Use this for:
    - Direct pool address verification
    - When GeckoTerminal/DefiLlama don't have the pool
    - Real-time on-chain data
    """
    from data_sources.geckoterminal import gecko_client
    import httpx
    
    chain = chain.lower()
    pool_address = pool_address.lower() if chain != "solana" else pool_address
    
    logger.info(f"🔗 RPC-First verify for {pool_address} on {chain}")
    
    pool_data = None
    source = "unknown"
    
    # PRIORITY 1: On-chain RPC (FIRST - this is the key difference)
    try:
        if onchain_client.is_chain_available(chain):
            rpc_data = await onchain_client.get_any_pool_data(chain, pool_address)
            
            if rpc_data:
                symbol0 = rpc_data.get("symbol0", "???")
                symbol1 = rpc_data.get("symbol1", "???")
                pool_type = rpc_data.get("pool_type", "unknown")
                
                # Get token prices for TVL calculation
                price0 = await get_token_price(symbol0, rpc_data.get("token0"))
                price1 = await get_token_price(symbol1, rpc_data.get("token1"))
                
                reserve0 = rpc_data.get("reserve0", 0)
                reserve1 = rpc_data.get("reserve1", 0)
                tvl = (reserve0 * price0) + (reserve1 * price1)
                
                pool_data = {
                    "symbol": f"{symbol0}/{symbol1}",
                    "name": f"{symbol0}-{symbol1} Pool",
                    "project": rpc_data.get("protocol", "Unknown"),
                    "chain": chain.capitalize(),
                    "pool_address": pool_address,
                    "tvl": tvl,
                    "tvlUsd": tvl,
                    "apy": 0,  # Will be enriched
                    "apy_base": 0,
                    "apy_reward": 0,
                    "pool_type": pool_type,
                    "token0": rpc_data.get("token0", ""),
                    "token1": rpc_data.get("token1", ""),
                    "symbol0": symbol0,
                    "symbol1": symbol1,
                    "reserve0": reserve0,
                    "reserve1": reserve1,
                    "factory": rpc_data.get("factory", ""),
                }
                source = "rpc"
                logger.info(f"RPC found: {symbol0}/{symbol1}, TVL: ${tvl:,.0f}")
        else:
            logger.warning(f"Chain {chain} RPC not available")
    except Exception as e:
        logger.warning(f"RPC lookup failed: {e}")
    
    # PRIORITY 2: Enrich with GeckoTerminal (for APY and volume)
    if pool_data:
        try:
            gecko_data = await gecko_client.get_pool_by_address(chain, pool_address)
            if gecko_data:
                # FIX: Update symbols if RPC returned ??? or empty
                if pool_data.get("symbol0") in ["???", "", None] and gecko_data.get("symbol0"):
                    pool_data["symbol0"] = gecko_data.get("symbol0")
                if pool_data.get("symbol1") in ["???", "", None] and gecko_data.get("symbol1"):
                    pool_data["symbol1"] = gecko_data.get("symbol1")
                # Update main symbol/name if they contain ???
                if "???" in pool_data.get("symbol", ""):
                    gecko_symbol = gecko_data.get("symbol", "")
                    if gecko_symbol and "???" not in gecko_symbol:
                        pool_data["symbol"] = gecko_symbol
                        pool_data["name"] = gecko_data.get("name", "") or f"{pool_data['symbol0']}-{pool_data['symbol1']} Pool"
                
                # Merge APY and volume data
                if gecko_data.get("apy", 0) > 0:
                    pool_data["apy"] = gecko_data.get("apy", 0)
                    pool_data["apy_base"] = gecko_data.get("apy_base", 0)
                    pool_data["apy_reward"] = gecko_data.get("apy_reward", 0)
                if gecko_data.get("volume_24h", 0) > 0:
                    pool_data["volume_24h"] = gecko_data.get("volume_24h", 0)
                    pool_data["volume_24h_formatted"] = gecko_data.get("volume_24h_formatted", "N/A")
                if gecko_data.get("project"):
                    pool_data["project"] = gecko_data.get("project")
                # TVL fallback from GeckoTerminal (critical for CL pools where RPC gives 0)
                gecko_tvl = gecko_data.get("tvl", 0) or gecko_data.get("tvlUsd", 0)
                if gecko_tvl > 0 and (pool_data.get("tvl", 0) == 0 or pool_data.get("tvlUsd", 0) == 0):
                    pool_data["tvl"] = gecko_tvl
                    pool_data["tvlUsd"] = gecko_tvl
                    logger.info(f"TVL enriched from GeckoTerminal: ${gecko_tvl:,.0f}")
                # Pool age from GeckoTerminal
                if gecko_data.get("pool_created_at"):
                    pool_data["pool_created_at"] = gecko_data.get("pool_created_at")
                source = f"{source}+geckoterminal"
                logger.info(f"Enriched with GeckoTerminal: {pool_data['symbol']}, APY={pool_data['apy']:.2f}%")
        except Exception as e:
            logger.debug(f"GeckoTerminal enrichment failed: {e}")
    
    # PRIORITY 2.5: AERODROME ON-CHAIN APY (Base only - REAL-TIME from gauge)
    # This calculates APY from actual on-chain gauge emissions
    if chain == "base" and pool_data:
        try:
            from data_sources.aerodrome import aerodrome_client
            onchain_apy_data = await aerodrome_client.get_real_time_apy(pool_address)
            
            if onchain_apy_data and onchain_apy_data.get("apy", 0) > 0:
                onchain_apy = onchain_apy_data.get("apy", 0)
                current_apy = pool_data.get("apy", 0) or 0
                
                # Calculate discrepancy
                if current_apy > 0:
                    discrepancy = abs(onchain_apy - current_apy) / current_apy
                else:
                    discrepancy = 1.0  # If no API APY, always use on-chain
                
                # Override if >5% discrepancy or no APY - on-chain is more accurate
                if discrepancy > 0.05 or current_apy == 0:
                    logger.info(f"[verify-rpc] APY Override: {current_apy:.2f}% → {onchain_apy:.2f}% (on-chain, diff: {discrepancy*100:.1f}%)")
                    pool_data["apy"] = onchain_apy
                    pool_data["apy_reward"] = onchain_apy_data.get("apy_reward", 0)
                    pool_data["apy_base"] = onchain_apy_data.get("apy_base", 0)
                    pool_data["apy_source"] = "aerodrome_onchain"
                    pool_data["gauge_address"] = onchain_apy_data.get("gauge_address")
                    pool_data["aero_price"] = onchain_apy_data.get("aero_price")
                    pool_data["epoch_remaining"] = onchain_apy_data.get("epoch_remaining") or aerodrome_client.get_epoch_time_remaining()
                    source = f"{source}+aero_onchain"
        except Exception as e:
            logger.debug(f"Aerodrome on-chain APY failed: {e}")
    
    # PRIORITY 3: If RPC failed, try GeckoTerminal as primary
    if not pool_data:
        try:
            gecko_data = await gecko_client.get_pool_by_address(chain, pool_address)
            if gecko_data and gecko_data.get("tvl", 0) > 0:
                pool_data = {
                    "symbol": gecko_data.get("symbol", ""),
                    "name": gecko_data.get("name", ""),
                    "project": gecko_data.get("project", "Unknown"),
                    "chain": chain.capitalize(),
                    "pool_address": pool_address,
                    "tvl": gecko_data.get("tvl", 0),
                    "tvlUsd": gecko_data.get("tvlUsd", 0),
                    "apy": gecko_data.get("apy", 0),
                    "apy_base": gecko_data.get("apy_base", 0),
                    "apy_reward": gecko_data.get("apy_reward", 0),
                    "volume_24h": gecko_data.get("volume_24h", 0),
                    "volume_24h_formatted": gecko_data.get("volume_24h_formatted", "N/A"),
                    "pool_type": gecko_data.get("pool_type", "volatile"),
                    "token0": gecko_data.get("token0", ""),
                    "token1": gecko_data.get("token1", ""),
                    "symbol0": gecko_data.get("symbol0", ""),
                    "symbol1": gecko_data.get("symbol1", ""),
                }
                source = "geckoterminal"
                logger.info(f"GeckoTerminal found: {pool_data['symbol']}")
        except Exception as e:
            logger.debug(f"GeckoTerminal fallback failed: {e}")
    
    # PRIORITY 4: DefiLlama enrichment (ALWAYS run for historical data like tvl_change, exposure)
    if pool_data:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get("https://yields.llama.fi/pools")
                if response.status_code == 200:
                    data = response.json()
                    pools = data.get("data", [])
                    
                    # Filter to chain first
                    chain_pools = [p for p in pools if chain in p.get("chain", "").lower()]
                    
                    # Strategy 1: Search by pool address
                    for p in chain_pools:
                        if pool_address in p.get("pool", "").lower():
                            # APY only if not already set by on-chain
                            if not pool_data.get("apy") or pool_data.get("apy", 0) == 0:
                                pool_data["apy"] = p.get("apy", 0)
                                pool_data["apy_base"] = p.get("apyBase", 0)
                                pool_data["apy_reward"] = p.get("apyReward", 0)
                            pool_data["project"] = p.get("project", pool_data.get("project", "Unknown"))
                            pool_data["il_risk"] = p.get("ilRisk", "unknown")
                            # Historical metrics from DefiLlama (ALWAYS add)
                            pool_data["tvl_change_1d"] = p.get("apyPct1D", 0)
                            pool_data["tvl_change_7d"] = p.get("apyPct7D", 0)
                            pool_data["tvl_change_30d"] = p.get("apyPct30D", 0)
                            pool_data["tvl_stability"] = "stable" if abs(p.get("apyPct7D", 0) or 0) < 10 else "volatile"
                            pool_data["stablecoin"] = p.get("stablecoin", False)
                            pool_data["exposure"] = p.get("exposure", "single")
                            pool_data["pool_meta"] = p.get("poolMeta")
                            pool_data["underlying_tokens"] = p.get("underlyingTokens", [])
                            pool_data["reward_tokens"] = p.get("rewardTokens", [])
                            source = f"{source}+defillama"
                            logger.info(f"DefiLlama enrichment: APY={pool_data['apy']:.2f}%, stablecoin={pool_data.get('stablecoin')}")
                            break
                    
                    # Strategy 2: Search by symbol if not found by address (check for missing historical data)
                    if pool_data.get("tvl_change_1d") is None and pool_data.get("symbol"):
                        symbol = pool_data["symbol"].upper().replace("/", "-")
                        for p in chain_pools:
                            p_symbol = (p.get("symbol", "") or "").upper().replace("/", "-")
                            if symbol == p_symbol or set(symbol.split("-")) == set(p_symbol.split("-")):
                                # APY only if not already set by on-chain
                                if not pool_data.get("apy") or pool_data.get("apy", 0) == 0:
                                    pool_data["apy"] = p.get("apy", 0)
                                    pool_data["apy_base"] = p.get("apyBase", 0)
                                    pool_data["apy_reward"] = p.get("apyReward", 0)
                                pool_data["project"] = p.get("project", pool_data.get("project", "Unknown"))
                                pool_data["il_risk"] = p.get("ilRisk", "unknown")
                                # Historical metrics from DefiLlama
                                pool_data["tvl_change_1d"] = p.get("apyPct1D", 0)
                                pool_data["tvl_change_7d"] = p.get("apyPct7D", 0)
                                pool_data["tvl_change_30d"] = p.get("apyPct30D", 0)
                                pool_data["tvl_stability"] = "stable" if abs(p.get("apyPct7D", 0) or 0) < 10 else "volatile"
                                pool_data["stablecoin"] = p.get("stablecoin", False)
                                pool_data["exposure"] = p.get("exposure", "single")
                                pool_data["pool_meta"] = p.get("poolMeta")
                                pool_data["underlying_tokens"] = p.get("underlyingTokens", [])
                                pool_data["reward_tokens"] = p.get("rewardTokens", [])
                                source = f"{source}+defillama"
                                logger.info(f"DefiLlama APY found by symbol: {pool_data['apy']:.2f}%")
                                break
        except Exception as e:
            logger.debug(f"DefiLlama APY enrichment failed: {e}")
    
    # If still no data, return error
    if not pool_data:
        logger.warning(f"Pool not found via RPC or GeckoTerminal: {pool_address}")
        raise HTTPException(status_code=404, detail="Pool not found on chain RPC or GeckoTerminal")
    
    # SECURITY & RISK ANALYSIS
    risk_analysis = {"risk_score": 50, "risk_level": "Medium", "risk_reasons": []}
    
    try:
        from api.security_module import security_checker
        
        tokens = [t for t in [pool_data.get("token0"), pool_data.get("token1")] if t]
        
        # Phase 1: GoPlus security checks
        security_result = await security_checker.check_security(tokens, chain)
        pool_data = await security_checker.clean_pool_symbols(pool_data, chain)
        peg_status = await security_checker.check_stablecoin_peg(pool_data, chain)
        
        # =========================================================
        # PHASE 4: CHECK AUDIT STATUS (same as verify-any)
        # =========================================================
        audit_result = {"audited": False, "source": "unknown"}
        try:
            from data_sources.audit_checker import audit_checker
            project_name = pool_data.get("project", "") or pool_data.get("protocol", "")
            audit_result = await audit_checker.check_audit_status(
                protocol_name=project_name,
                contract_address=pool_address,
                chain=chain
            )
            pool_data["audit_status"] = audit_result
        except Exception as e:
            logger.debug(f"Audit check failed: {e}")
            pool_data["audit_status"] = {"audited": False, "source": "error"}
        
        # =========================================================
        # PHASE 5: CHECK LIQUIDITY LOCK (same as verify-any)
        # =========================================================
        lock_result = {"has_lock": False, "source": "unknown"}
        try:
            from data_sources.liquidity_lock import liquidity_lock_checker
            lock_result = await liquidity_lock_checker.check_lp_lock(
                pool_address=pool_address,
                chain=chain
            )
            pool_data["liquidity_lock"] = lock_result
        except Exception as e:
            logger.debug(f"Liquidity lock check failed: {e}")
            pool_data["liquidity_lock"] = {"has_lock": False, "source": "error"}
        
        # =========================================================
        # PHASE 6: WHALE CONCENTRATION ANALYSIS (same as verify-any)
        # =========================================================
        # Skip for stablecoins and major tokens (highly distributed)
        SKIP_WHALE_TOKENS = {
            "usdc", "usdt", "dai", "busd", "frax", "tusd", "usdp", "usdd", "gusd", "lusd",
            "weth", "eth", "wbtc", "btc", "sol", "wsol", "matic", "wmatic", "avax", "wavax",
            "bnb", "wbnb", "ftm", "wftm", "op", "arb", "aero"
        }
        
        whale_analysis = {"token0": None, "token1": None, "lp_token": None}
        try:
            from data_sources.holder_analysis import holder_analyzer
            token0_addr = pool_data.get("token0") or ""
            token1_addr = pool_data.get("token1") or ""
            symbol0 = (pool_data.get("symbol0") or "").lower()
            symbol1 = (pool_data.get("symbol1") or "").lower()
            
            # Only analyze exotic tokens (not stablecoins/majors)
            if token0_addr and symbol0 not in SKIP_WHALE_TOKENS:
                whale_analysis["token0"] = await holder_analyzer.get_holder_analysis(
                    token_address=token0_addr,
                    chain=chain
                )
            else:
                whale_analysis["token0"] = {"skipped": True, "reason": "major/stable token", "concentration_risk": "low"}
            
            if token1_addr and symbol1 not in SKIP_WHALE_TOKENS:
                whale_analysis["token1"] = await holder_analyzer.get_holder_analysis(
                    token_address=token1_addr,
                    chain=chain
                )
            else:
                whale_analysis["token1"] = {"skipped": True, "reason": "major/stable token", "concentration_risk": "low"}
            
            # LP token analysis - shows who holds positions in this pool
            if pool_address:
                whale_analysis["lp_token"] = await holder_analyzer.get_holder_analysis(
                    token_address=pool_address,
                    chain=chain
                )
            
            pool_data["whale_analysis"] = whale_analysis
        except Exception as e:
            logger.debug(f"Whale concentration check failed: {e}")
            pool_data["whale_analysis"] = {"token0": None, "token1": None, "lp_token": None, "source": "error"}
        
        # =========================================================
        # PHASE 7: CALCULATE COMPREHENSIVE RISK SCORE (WITH ALL DATA)
        # =========================================================
        risk_analysis = security_checker.calculate_risk_score(
            pool_data=pool_data,
            security_result=security_result,
            peg_status=peg_status,
            symbol_warnings=pool_data.get("symbol_warnings"),
            # Pass additional risk factors (same as verify-any)
            audit_status=pool_data.get("audit_status"),
            liquidity_lock=pool_data.get("liquidity_lock"),
            whale_analysis=pool_data.get("whale_analysis")
        )
        
        pool_data["security"] = {
            "checked": security_result.get("status") == "success",
            "source": security_result.get("source", "goplus"),
            "is_honeypot": risk_analysis.get("is_honeypot", False),
            "peg_status": peg_status,
            "tokens": security_result.get("tokens", {})
        }
        
        # Add full risk analysis to pool_data (same as verify-any)
        pool_data["risk_score"] = risk_analysis.get("risk_score")
        pool_data["risk_level"] = risk_analysis.get("risk_level")
        pool_data["risk_reasons"] = risk_analysis.get("risk_reasons", [])
        pool_data["risk_breakdown"] = risk_analysis.get("risk_breakdown", {})
        pool_data["il_analysis"] = risk_analysis.get("il_analysis", {})
        pool_data["volatility_analysis"] = risk_analysis.get("volatility_analysis", {})
        pool_data["pool_age_analysis"] = risk_analysis.get("pool_age_analysis", {})
        
    except Exception as e:
        logger.warning(f"Security check failed: {e}")
        # Basic risk based on TVL
        tvl = pool_data.get("tvl", 0)
        if tvl < 100000:
            risk_analysis["risk_score"] = 35
            risk_analysis["risk_level"] = "High"
            risk_analysis["risk_reasons"].append("Low TVL (<$100K)")
    
    return {
        "success": True,
        "pool": pool_data,
        "risk_analysis": risk_analysis,
        "source": source,
        "data_quality": "rpc" if "rpc" in source else "api",
        "chain": chain
    }


# ============================================
# SMART VERIFY (Intelligent Factory-Based Routing)
# ============================================

@router.get("/smart-verify")
async def smart_verify_pool(
    input: str = Query(..., description="Pool address or URL"),
    chain: str = Query("base", description="Chain hint (auto-detected from URL if possible)")
):
    """
    🧠 Smart Pool Verification with Factory-Based Protocol Detection.
    
    The "Brain" of the system that:
    1. Parses input (address or URL)
    2. Detects protocol via pool.factory() call
    3. Routes to optimal adapter:
       - Tier 1 (Premium): Aerodrome - Full APY, Gauge, Epoch
       - Tier 2 (High): Uniswap V3 - Fee APY
       - Tier 3 (Basic): Universal - TVL only
    4. Patches with DefiLlama APY if needed
    
    Returns data quality tier indicator.
    """
    from api.smart_router import smart_router
    
    result = await smart_router.smart_route_pool_check(input, chain)
    
    # Add risk analysis if we have pool data
    if result.get("success") and result.get("pool"):
        pool = result["pool"]
        
        # Generate risk analysis
        risk_score = 50  # Base score
        risk_reasons = []
        
        tvl = pool.get("tvl", 0) or pool.get("tvlUsd", 0)
        apy = pool.get("apy", 0)
        
        # TVL risk
        if tvl < 100000:
            risk_score += 25
            risk_reasons.append(f"Low TVL (<$100K) - liquidity risk")
        elif tvl > 10000000:
            risk_score -= 15
            risk_reasons.append(f"High TVL (>${tvl/1e6:.1f}M) - strong liquidity")
        
        # APY risk
        if apy > 1000:
            risk_score += 20
            risk_reasons.append(f"Very high APY ({apy:.0f}%) - sustainability concern")
        elif apy > 100:
            risk_score += 10
            risk_reasons.append(f"High APY ({apy:.0f}%) - verify sources")
        
        # Data quality warning
        if result.get("data_quality") == "basic":
            risk_score += 10
            risk_reasons.append("Unverified protocol - limited analysis")
        
        risk_score = max(0, min(100, risk_score))
        risk_level = "Low" if risk_score < 40 else "Medium" if risk_score < 70 else "High"
        
        result["risk_analysis"] = {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_reasons": risk_reasons
        }
    
    return result


@router.get("/verify-any")
async def verify_any_pool(
    pool_address: str = Query(..., description="Pool contract address"),
    chain: str = Query("base", description="Chain name")
):
    """
    Universal pool verification endpoint.
    NOW USES SmartRouter with factory-based protocol detection.
    Fallback: GeckoTerminal -> DefiLlama -> On-chain RPC.
    Always returns risk analysis.
    """
    from api.smart_router import smart_router
    
    chain = chain.lower()
    # Solana addresses are case-sensitive (base58), EVM addresses are not
    pool_address = pool_address if chain == "solana" else pool_address.lower()
    
    logger.info(f"🧠 SmartRouter verify for {pool_address} on {chain}")
    
    # PRIMARY: Use SmartRouter (factory-based detection)
    try:
        smart_result = await smart_router.smart_route_pool_check(pool_address, chain)
        
        if smart_result.get("success") and smart_result.get("pool"):
            pool = smart_result["pool"]
            
            # =========================================================
            # SECURITY & DATA HYGIENE LAYER
            # =========================================================
            from api.security_module import security_checker
            
            # Get token addresses for security check
            token0 = pool.get("token0", "")
            token1 = pool.get("token1", "")
            
            # If no token addresses, fetch from RPC (pool.token0(), pool.token1())
            if not token0 or not token1:
                try:
                    from data_sources.onchain import onchain_client
                    logger.info(f"Fetching token addresses from RPC for security check...")
                    
                    rpc_data = await onchain_client.get_lp_reserves(chain, pool_address)
                    if rpc_data:
                        token0 = rpc_data.get("token0", "")
                        token1 = rpc_data.get("token1", "")
                        pool["token0"] = token0
                        pool["token1"] = token1
                        pool["symbol0"] = rpc_data.get("symbol0", pool.get("symbol0", ""))
                        pool["symbol1"] = rpc_data.get("symbol1", pool.get("symbol1", ""))
                        logger.info(f"Got tokens via RPC: {pool.get('symbol0')}/{pool.get('symbol1')}")
                except Exception as e:
                    logger.debug(f"RPC token fetch failed: {e}")
            
            tokens = [t for t in [token0, token1] if t]
            
            # Run security checks in parallel
            try:
                # Phase 1: GoPlus RugCheck
                security_result = await security_checker.check_security(tokens, chain)
                
                # Phase 2: Clean symbols (fix 0x addresses)
                pool = await security_checker.clean_pool_symbols(pool, chain)
                
                # Phase 3: Stablecoin peg check
                peg_status = await security_checker.check_stablecoin_peg(pool, chain)
                
                # =========================================================
                # COLLECT ALL DATA BEFORE SCORING
                # =========================================================
                
                # Phase 4: Check audit status
                audit_result = {"audited": False, "source": "unknown"}
                try:
                    from data_sources.audit_checker import audit_checker
                    project_name = pool.get("project", "") or pool.get("protocol", "")
                    audit_result = await audit_checker.check_audit_status(
                        protocol_name=project_name,
                        contract_address=pool_address,
                        chain=chain
                    )
                    pool["audit_status"] = audit_result
                except Exception as e:
                    logger.debug(f"Audit check failed: {e}")
                    pool["audit_status"] = {"audited": False, "source": "error"}
                
                # Phase 5: Check liquidity lock
                lock_result = {"has_lock": False, "source": "unknown"}
                try:
                    from data_sources.liquidity_lock import liquidity_lock_checker
                    lock_result = await liquidity_lock_checker.check_lp_lock(
                        pool_address=pool_address,
                        chain=chain
                    )
                    pool["liquidity_lock"] = lock_result
                except Exception as e:
                    logger.debug(f"Liquidity lock check failed: {e}")
                    pool["liquidity_lock"] = {"has_lock": False, "source": "error"}
                
                # Phase 6: Analyze whale concentration
                # SKIP for stablecoins and major tokens (highly distributed, waste of API calls)
                SKIP_WHALE_TOKENS = {
                    # Stablecoins
                    "usdc", "usdt", "dai", "busd", "frax", "tusd", "usdp", "usdd", "gusd", "lusd",
                    # Major tokens (highly distributed)
                    "weth", "eth", "wbtc", "btc", "sol", "wsol", "matic", "wmatic", "avax", "wavax",
                    "bnb", "wbnb", "ftm", "wftm", "op", "arb"
                }
                
                whale_analysis = {"token0": None, "token1": None, "lp_token": None}
                try:
                    from data_sources.holder_analysis import holder_analyzer
                    token0_addr = pool.get("token0") or ""
                    token1_addr = pool.get("token1") or ""
                    symbol0 = (pool.get("symbol0") or "").lower()
                    symbol1 = (pool.get("symbol1") or "").lower()
                    
                    # Only analyze exotic tokens (not stablecoins/majors)
                    if token0_addr and symbol0 not in SKIP_WHALE_TOKENS:
                        whale_analysis["token0"] = await holder_analyzer.get_holder_analysis(
                            token_address=token0_addr,
                            chain=chain
                        )
                    else:
                        whale_analysis["token0"] = {"skipped": True, "reason": "major/stable token", "concentration_risk": "low"}
                    
                    if token1_addr and symbol1 not in SKIP_WHALE_TOKENS:
                        whale_analysis["token1"] = await holder_analyzer.get_holder_analysis(
                            token_address=token1_addr,
                            chain=chain
                        )
                    else:
                        whale_analysis["token1"] = {"skipped": True, "reason": "major/stable token", "concentration_risk": "low"}
                    
                    # LP token analysis is useful - shows who holds positions in this pool
                    if pool_address:
                        whale_analysis["lp_token"] = await holder_analyzer.get_holder_analysis(
                            token_address=pool_address,
                            chain=chain
                        )
                    
                    pool["whale_analysis"] = whale_analysis
                except Exception as e:
                    logger.debug(f"Whale concentration check failed: {e}")
                    pool["whale_analysis"] = {"token0": None, "token1": None, "lp_token": None, "source": "error"}
                
                # =========================================================
                # PHASE 7: CALCULATE COMPREHENSIVE RISK SCORE (WITH ALL DATA)
                # =========================================================
                risk_analysis = security_checker.calculate_risk_score(
                    pool_data=pool,
                    security_result=security_result,
                    peg_status=peg_status,
                    symbol_warnings=pool.get("symbol_warnings"),
                    # NEW: Pass additional risk factors
                    audit_status=pool.get("audit_status"),
                    liquidity_lock=pool.get("liquidity_lock"),
                    whale_analysis=pool.get("whale_analysis")
                )
                
                # Add security details to response (includes tokens for frontend display)
                pool["security"] = {
                    "checked": security_result.get("status") == "success",
                    "source": security_result.get("source", "goplus"),
                    "is_honeypot": risk_analysis.get("is_honeypot", False),
                    "peg_status": peg_status,
                    "tokens": security_result.get("tokens", {}),  # Token analysis for frontend
                    "summary": security_result.get("summary", {})
                }
                
                # Add full risk analysis to pool object (for frontend display)
                pool["risk_score"] = risk_analysis.get("risk_score")
                pool["risk_level"] = risk_analysis.get("risk_level")
                pool["risk_reasons"] = risk_analysis.get("risk_reasons", [])
                pool["risk_breakdown"] = risk_analysis.get("risk_breakdown", {})
                pool["il_analysis"] = risk_analysis.get("il_analysis", {})
                pool["volatility_analysis"] = risk_analysis.get("volatility_analysis", {})
                pool["pool_age_analysis"] = risk_analysis.get("pool_age_analysis", {})
                
            except Exception as e:
                logger.warning(f"Security check failed, using basic analysis: {e}")
                # Fallback to basic risk analysis
                tvl = pool.get("tvl", 0) or pool.get("tvlUsd", 0)
                risk_score = 50
                risk_reasons = []
                
                if tvl < 100000:
                    risk_score += 25
                    risk_reasons.append("Low TVL (<$100K) - liquidity risk")
                
                risk_analysis = {
                    "risk_score": max(0, min(100, 100 - risk_score)),
                    "risk_level": "Medium",
                    "risk_reasons": risk_reasons,
                    "is_honeypot": False
                }
            
            return {
                "success": True,
                "pool": pool,
                "risk_analysis": risk_analysis,
                "source": smart_result.get("source", "smart_router"),
                "data_quality": smart_result.get("data_quality", "unknown"),
                "chain": chain
            }
    except Exception as e:
        logger.warning(f"SmartRouter failed, using legacy: {e}")
    
    # FALLBACK: Legacy logic (GeckoTerminal -> DefiLlama -> On-chain)
    from data_sources.geckoterminal import gecko_client
    import httpx
    
    pool_data = None
    source = "unknown"
    symbol_for_search = ""
    
    # PRIORITY 1: GeckoTerminal (real-time, works for CL - most complete data)
    try:
        gecko_data = await gecko_client.get_pool_by_address(chain, pool_address)
        if gecko_data and gecko_data.get("tvl", 0) > 0:
            symbol_for_search = gecko_data.get("symbol", "")
            pool_data = {
                "symbol": gecko_data.get("symbol", ""),
                "name": gecko_data.get("name", ""),
                "project": gecko_data.get("project", "Unknown"),  # Now included from _normalize_pool_data
                "chain": chain.capitalize(),
                "tvl": gecko_data.get("tvl", 0),
                "tvlUsd": gecko_data.get("tvlUsd", 0),
                "apy": gecko_data.get("apy", 0),
                "apy_base": gecko_data.get("apy_base", 0),
                "apy_reward": gecko_data.get("apy_reward", 0),
                "volume_24h": gecko_data.get("volume_24h", 0),
                "volume_24h_formatted": gecko_data.get("volume_24h_formatted", "N/A"),
                "trading_fee": gecko_data.get("trading_fee"),
                "fee_24h_usd": gecko_data.get("fee_24h_usd"),
                "il_risk": gecko_data.get("il_risk", "yes"),
                "pool_type": gecko_data.get("pool_type", "volatile"),
                "pool_address": pool_address,
                # Token addresses for security checks (Solana RugCheck / EVM GoPlus)
                "token0": gecko_data.get("token0", ""),
                "token1": gecko_data.get("token1", ""),
                "symbol0": gecko_data.get("symbol0", ""),
                "symbol1": gecko_data.get("symbol1", ""),
                "pool_created_at": gecko_data.get("pool_created_at"),
                "priceChange24h": gecko_data.get("priceChange24h", 0),
            }
            source = "geckoterminal"
            logger.info(f"Found in GeckoTerminal: {pool_data['symbol']}, project: {pool_data['project']}")
    except Exception as e:
        logger.debug(f"GeckoTerminal lookup failed: {e}")
    
    # PRIORITY 2: DefiLlama (ALWAYS check for APY, even if GeckoTerminal found pool)
    defillama_apy = 0
    defillama_found = False
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get("https://yields.llama.fi/pools")
            if response.status_code == 200:
                data = response.json()
                pools = data.get("data", [])
                
                # Filter to chain first
                chain_pools = [p for p in pools if chain in p.get("chain", "").lower()]
                
                # Strategy 1: Search for pool by address in pool ID
                for p in chain_pools:
                    if pool_address in p.get("pool", "").lower():
                        defillama_apy = p.get("apy", 0)
                        defillama_found = True
                        
                        if pool_data:
                            # Merge APY from DefiLlama with existing data
                            if defillama_apy and (not pool_data.get("apy") or defillama_apy > pool_data.get("apy", 0)):
                                pool_data["apy"] = defillama_apy
                                pool_data["apy_base"] = p.get("apyBase", 0)
                                pool_data["apy_reward"] = p.get("apyReward", 0)
                            pool_data["project"] = p.get("project", pool_data.get("project", "Unknown"))
                            pool_data["il_risk"] = p.get("ilRisk", "no")
                            source = f"{source}+defillama" if source != "unknown" else "defillama"
                        else:
                            pool_data = {
                                "symbol": p.get("symbol", ""),
                                "project": p.get("project", "Unknown"),
                                "chain": p.get("chain", chain.capitalize()),
                                "tvl": p.get("tvlUsd", 0),
                                "apy": defillama_apy,
                                "apy_base": p.get("apyBase", 0),
                                "apy_reward": p.get("apyReward", 0),
                                "pool_address": pool_address,
                                "il_risk": p.get("ilRisk", "no"),
                            }
                            source = "defillama"
                        
                        logger.info(f"DefiLlama found by address, APY: {defillama_apy}%")
                        break
                
                # Strategy 2: If not found by address, search by symbol (e.g., "SOL-USDC")
                if not defillama_found and symbol_for_search:
                    # Normalize symbol for matching (remove fee tier like "0.05%")
                    clean_symbol = symbol_for_search.split(" ")[0].upper().replace("-", "")
                    
                    for p in chain_pools:
                        pool_symbol = (p.get("symbol", "") or "").upper().replace("-", "")
                        # Check if symbols match (order insensitive)
                        if clean_symbol == pool_symbol or set(clean_symbol.split("/")) == set(pool_symbol.split("/")):
                            defillama_apy = p.get("apy", 0)
                            defillama_found = True
                            
                            if pool_data and defillama_apy:
                                if not pool_data.get("apy") or defillama_apy > pool_data.get("apy", 0):
                                    pool_data["apy"] = defillama_apy
                                    pool_data["apy_base"] = p.get("apyBase", 0)
                                    pool_data["apy_reward"] = p.get("apyReward", 0)
                                pool_data["project"] = p.get("project", pool_data.get("project", "Unknown"))
                                source = f"{source}+defillama" if "defillama" not in source else source
                            
                            logger.info(f"DefiLlama found by symbol '{symbol_for_search}', APY: {defillama_apy}%")
                            break
    except Exception as e:
        logger.debug(f"DefiLlama lookup failed: {e}")
    
    # PRIORITY 2.5: AERODROME ON-CHAIN APY (Base only - most accurate)
    # Override DefiLlama APY if discrepancy > 5%
    if chain == "base" and pool_data:
        try:
            from data_sources.aerodrome import aerodrome_client
            onchain_apy_data = await aerodrome_client.get_real_time_apy(pool_address)
            
            if onchain_apy_data and onchain_apy_data.get("apy", 0) > 0:
                onchain_apy = onchain_apy_data.get("apy", 0)
                current_apy = pool_data.get("apy", 0) or 0
                
                # Calculate discrepancy
                if current_apy > 0:
                    discrepancy = abs(onchain_apy - current_apy) / current_apy
                else:
                    discrepancy = 1.0  # If no API APY, always use on-chain
                
                # Override if >5% discrepancy or no APY
                if discrepancy > 0.05 or current_apy == 0:
                    logger.info(f"APY Override: {current_apy:.2f}% → {onchain_apy:.2f}% (on-chain, diff: {discrepancy*100:.1f}%)")
                    pool_data["apy"] = onchain_apy
                    pool_data["apy_reward"] = onchain_apy_data.get("apy_reward", 0)
                    pool_data["apy_base"] = onchain_apy_data.get("apy_base", 0)
                    pool_data["apy_source"] = "aerodrome_onchain"
                    pool_data["gauge_address"] = onchain_apy_data.get("gauge_address")
                    pool_data["aero_price"] = onchain_apy_data.get("aero_price")
                    pool_data["epoch_remaining"] = onchain_apy_data.get("epoch_remaining") or aerodrome_client.get_epoch_time_remaining()
                    source = f"{source}+aerodrome_onchain" if "aerodrome" not in source else source
                    
                # Set project to Aerodrome if has gauge
                if onchain_apy_data.get("has_gauge"):
                    pool_data["project"] = pool_data.get("project") or "Aerodrome"
                    
        except Exception as e:
            logger.debug(f"Aerodrome on-chain APY failed: {e}")
    
    # PRIORITY 3: On-chain RPC (universal)
    if not pool_data:
        try:
            onchain_data = await onchain_client.get_any_pool_data(chain, pool_address)
            if onchain_data:
                symbol0 = onchain_data.get("symbol0", "???")
                symbol1 = onchain_data.get("symbol1", "???")
                pool_type = onchain_data.get("pool_type", "unknown")
                
                # Calculate TVL from balances
                tvl = 0
                if pool_type == "v2":
                    price0 = await get_token_price(symbol0, onchain_data.get("token0"))
                    price1 = await get_token_price(symbol1, onchain_data.get("token1"))
                    tvl = (onchain_data.get("reserve0", 0) * price0) + (onchain_data.get("reserve1", 0) * price1)
                elif pool_type == "cl":
                    price0 = await get_token_price(symbol0, onchain_data.get("token0"))
                    price1 = await get_token_price(symbol1, onchain_data.get("token1"))
                    tvl = (onchain_data.get("balance0", 0) * price0) + (onchain_data.get("balance1", 0) * price1)
                
                pool_data = {
                    "symbol": f"{symbol0}-{symbol1}",
                    "project": "Unknown Protocol",
                    "chain": chain.capitalize(),
                    "tvl": tvl,
                    "apy": 0,  # Can't determine APY from on-chain only
                    "pool_type": pool_type,
                    "pool_address": pool_address,
                    "token0": symbol0,
                    "token1": symbol1,
                }
                source = "onchain"
                logger.info(f"Found on-chain ({pool_type}): {symbol0}-{symbol1}")
        except Exception as e:
            logger.error(f"On-chain lookup failed: {e}")
    
    # PRIORITY LAST: Universal Scanner (fingerprinting for ANY unknown contract)
    if not pool_data:
        try:
            from data_sources.universal_adapter import universal_scanner
            logger.info(f"Trying UniversalScanner for {pool_address[:10]}...")
            scan_result = await universal_scanner.scan(pool_address, chain)
            
            if scan_result and scan_result.get("tvl", 0) > 0:
                pool_data = scan_result
                source = f"universal_{scan_result.get('contract_type', 'unknown')}"
                logger.info(f"UniversalScanner found: {scan_result.get('symbol')} (type: {scan_result.get('contract_type')})")
            elif scan_result:
                # Even with 0 TVL, return the data
                pool_data = scan_result
                source = f"universal_{scan_result.get('contract_type', 'unknown')}"
                logger.info(f"UniversalScanner identified: {scan_result.get('contract_type')} (TVL: 0)")
        except Exception as e:
            logger.error(f"UniversalScanner failed: {e}")
    
    # If still no data, return error
    if not pool_data:
        return {
            "success": False,
            "error": "Pool not found on any data source",
            "chain": chain,
            "pool_address": pool_address,
            "available_chains": onchain_client.get_available_chains()
        }
    
    # =========================================================
    # SECURITY CHECK (Legacy flow - RugCheck/GoPlus)
    # =========================================================
    security_result = {"status": "skipped", "tokens": {}, "summary": {}}
    try:
        from api.security_module import security_checker
        
        # Get token addresses
        token0 = pool_data.get("token0", "")
        token1 = pool_data.get("token1", "")
        tokens = [t for t in [token0, token1] if t]
        
        if tokens:
            security_result = await security_checker.check_security(tokens, chain)
            logger.info(f"Security check ({security_result.get('source', 'unknown')}): {len(security_result.get('tokens', {}))} tokens checked")
            
            # Add security data to pool
            pool_data["security"] = {
                "checked": security_result.get("status") == "success",
                "source": security_result.get("source", "unknown"),
                "tokens": security_result.get("tokens", {}),
                "summary": security_result.get("summary", {})
            }
    except Exception as e:
        logger.warning(f"Security check failed in legacy flow: {e}")
    
    # Generate risk analysis
    risk_level = "Medium"
    risk_score = 50
    risk_reasons = []
    
    tvl = pool_data.get("tvl", 0)
    apy = pool_data.get("apy", 0)
    
    # TVL-based risk
    if tvl < 100000:
        risk_level = "High"
        risk_score += 25
        risk_reasons.append("Low TVL (<$100K) - potential liquidity issues")
    elif tvl < 500000:
        risk_score += 10
        risk_reasons.append("Moderate TVL - monitor liquidity")
    elif tvl > 10000000:
        risk_score -= 15
    
    # APY-based risk
    if apy > 100:
        risk_level = "High"
        risk_score += 20
        risk_reasons.append(f"Very high APY ({apy:.1f}%) - verify sustainability")
    elif apy > 50:
        risk_score += 10
        risk_reasons.append(f"High APY ({apy:.1f}%) - check token emissions")
    
    # IL risk
    if pool_data.get("il_risk") == "yes" or pool_data.get("pool_type") in ["v2", "cl"]:
        risk_reasons.append("Impermanent loss risk for non-stablecoin pairs")
    
    # Unknown protocol
    if pool_data.get("project") == "Unknown Protocol" or source == "onchain":
        risk_score += 15
        risk_reasons.append("Unknown protocol - DYOR (do your own research)")
    
    # Clamp score
    risk_score = max(10, min(90, risk_score))
    
    if risk_score >= 60:
        risk_level = "High"
    elif risk_score <= 35:
        risk_level = "Low"
    
    return {
        "success": True,
        "pool": pool_data,
        "risk_analysis": {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_reasons": risk_reasons,
        },
        "source": source,
        "chain": chain
    }
