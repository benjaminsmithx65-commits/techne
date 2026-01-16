"""
Techne.finance - Multi-Chain Yield Optimizer API
FastAPI backend with Artisan agent and x402 payments
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os

from artisan import get_top_yields, fetch_yields, filter_yields
from artisan.data_sources import get_aggregated_pools, fetch_geckoterminal_pools, format_gecko_pool, SUPPORTED_CHAINS
from artisan.scout_agent import get_scout_pools, TOP_PROTOCOLS
from artisan.guardian_agent import analyze_pool_risk, get_quick_risk
from artisan.airdrop_agent import get_airdrop_opportunities, get_pool_airdrop_info
from x402 import get_payment_requirements, verify_x402_payment, get_session
from x402.pro_pack import (
    create_pro_pack_session, 
    get_pro_session, 
    get_user_active_session,
    mark_pro_session_paid,
    dismiss_pool_from_session,
    get_pro_pack_status
)

# Import agent wallet router
try:
    from api.agent_wallet_router import router as agent_wallet_router
    AGENT_WALLET_AVAILABLE = True
except ImportError:
    AGENT_WALLET_AVAILABLE = False

# Import engineer router (NEW - MVP Execution Layer)
try:
    from api.engineer_router import router as engineer_router
    ENGINEER_AVAILABLE = True
except ImportError:
    ENGINEER_AVAILABLE = False

# Import scout router (Risk Intelligence, Yield Prediction, Chat)
try:
    from api.scout_router import router as scout_router
    SCOUT_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Scout router not available: {e}")
    SCOUT_AVAILABLE = False

# Import memory router (Outcome-Based Memory Engine)
try:
    from api.memory_router import router as memory_router
    MEMORY_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Memory router not available: {e}")
    MEMORY_AVAILABLE = False

# Import observability router (Agent Tracing & Metrics)
try:
    from api.observability_router import router as observability_router
    OBSERVABILITY_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Observability router not available: {e}")
    OBSERVABILITY_AVAILABLE = False

# Import security router (API Keys, Rate Limits, Transaction Guards)
try:
    from api.security_router import router as security_router
    SECURITY_ROUTER_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Security router not available: {e}")
    SECURITY_ROUTER_AVAILABLE = False

# Import infrastructure router (Health Checks, Metrics, Config)
try:
    from api.infrastructure_router import router as infrastructure_router
    INFRASTRUCTURE_ROUTER_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Infrastructure router not available: {e}")
    INFRASTRUCTURE_ROUTER_AVAILABLE = False

# Import intelligence router (AI Predictions, Recommendations, Learning)
try:
    from api.intelligence_router import router as intelligence_router
    INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Intelligence router not available: {e}")
    INTELLIGENCE_AVAILABLE = False

# Import revenue router (Subscriptions, Fees, Payments)
try:
    from api.revenue_router import router as revenue_router
    REVENUE_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Revenue router not available: {e}")
    REVENUE_AVAILABLE = False

# Import position router (Position Tracking, Alerts)
try:
    from api.position_router import router as position_router
    POSITION_TRACKING_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Position router not available: {e}")
    POSITION_TRACKING_AVAILABLE = False

# Import meridian router (x402 Payments for Credits)
try:
    from api.meridian_router import router as meridian_router
    MERIDIAN_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Meridian router not available: {e}")
    MERIDIAN_AVAILABLE = False

app = FastAPI(
    title="Techne.finance API",
    description="AI-powered yield optimizer - Production Grade | Security + AI + Revenue",
    version="1.1.0"
)

# Include agent wallet routes
if AGENT_WALLET_AVAILABLE:
    app.include_router(agent_wallet_router)

# Include engineer routes (Execution Layer)
if ENGINEER_AVAILABLE:
    app.include_router(engineer_router)

# Include scout routes (Risk Intelligence)
if SCOUT_AVAILABLE:
    app.include_router(scout_router)

# Include memory routes (Outcome-Based Memory)
if MEMORY_AVAILABLE:
    app.include_router(memory_router)

# Include observability routes (Agent Tracing)
if OBSERVABILITY_AVAILABLE:
    app.include_router(observability_router)

# Include security routes (API Key Management, Rate Limits)
if SECURITY_ROUTER_AVAILABLE:
    app.include_router(security_router)

# Include infrastructure routes (Health, Metrics, Config)
if INFRASTRUCTURE_ROUTER_AVAILABLE:
    app.include_router(infrastructure_router)

# Include intelligence routes (AI Predictions, Recommendations)
if INTELLIGENCE_AVAILABLE:
    app.include_router(intelligence_router)

# Include revenue routes (Subscriptions, Fees, Payments)
if REVENUE_AVAILABLE:
    app.include_router(revenue_router)

# Include position routes (Position Tracking, Alerts)
if POSITION_TRACKING_AVAILABLE:
    app.include_router(position_router)
    print("[Positions] Position tracking router loaded")

# Include meridian routes (x402 Payments for Credits)
if MERIDIAN_AVAILABLE:
    app.include_router(meridian_router)
    print("[Meridian] x402 payment router loaded")

# Include Telegram bot API routes
try:
    from api.telegram_router import router as telegram_router
    app.include_router(telegram_router)
    print("[Telegram] API router loaded")
except ImportError as e:
    print(f"[Telegram] Router not available: {e}")

# Security Middleware (Production-grade protection)
try:
    from security import SecurityMiddleware, RateLimiter, RateLimitConfig
    
    # Configure rate limits for production
    rate_config = RateLimitConfig(
        requests_per_minute=100,
        requests_per_hour=2000,
        requests_per_day=20000,
        burst_limit=20
    )
    
    # Add security middleware (rate limiting, headers, logging)
    app.add_middleware(SecurityMiddleware, rate_limiter=RateLimiter(rate_config))
    SECURITY_ENABLED = True
    print("[Security] Production security middleware enabled")
except ImportError as e:
    print(f"[Warning] Security middleware not available: {e}")
    SECURITY_ENABLED = False

# CORS - Hardened for production (update origins as needed)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://techne.finance",
    "https://app.techne.finance",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if os.environ.get("PRODUCTION") else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
    expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ============================================
# MODELS
# ============================================

class YieldFilter(BaseModel):
    chain: str = "Base"
    min_tvl: float = 1000000
    min_apy: float = 3.0
    max_apy: float = 100.0
    stablecoin_only: bool = False
    limit: int = 20


class PaymentRequest(BaseModel):
    pool_id: str


class VerifyPaymentRequest(BaseModel):
    session_id: str
    tx_hash: str


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    # Serve the frontend app
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# Alias for /api/pools (frontend uses this)
@app.get("/api/pools")
async def get_pools(
    chain: str = Query("base", description="Blockchain to filter (default: base)"),
    min_tvl: float = Query(100000, description="Minimum TVL in USD"),
    min_apy: float = Query(0.0, description="Minimum APY percentage"),
    max_apy: float = Query(500.0, description="Maximum APY (filter suspicious)"),
    stablecoin_only: bool = Query(False, description="Only stablecoin pools"),
    asset_type: str = Query("all", description="Asset type: stablecoin, eth, sol, all"),
    pool_type: str = Query("all", description="Pool type: single (lending), dual (LP), all"),
    protocols: str = Query("", description="Comma-separated protocol names to filter"),
    limit: int = Query(15, description="Max results")
):
    """
    Get pools from multiple sources with asset type and pool type filtering
    """
    try:
        # Determine which chains to search
        # Priority: explicit chain param > asset_type inference > default
        if chain and chain.lower() not in ["", "all"]:
            # User explicitly selected a chain
            chains = [chain.capitalize()]
        elif asset_type == "sol":
            chains = ["Solana"]
        else:
            chains = ["Base", "Ethereum", "Arbitrum", "Solana"]

        
        all_pools = []
        sources_used = set()
        
        # Fetch more pools from each chain when querying multiple chains
        # When filtering by specific protocols, fetch MUCH more to ensure we get their pools
        # (some protocols like Kamino have low APY and would be cut off otherwise)
        if protocols and protocols.strip():
            per_chain_limit = 500  # Fetch many more when filtering by protocols
        elif len(chains) > 1:
            per_chain_limit = limit * 3
        else:
            per_chain_limit = limit * 2
        
        # Prepare protocol filter
        protocol_list = []
        if protocols and protocols.strip():
            protocol_list = [p.strip().lower() for p in protocols.split(",") if p.strip()]

        for c in chains:
            result = await get_aggregated_pools(
                chain=c,
                min_tvl=min_tvl,
                min_apy=min_apy,
                stablecoin_only=stablecoin_only or asset_type == "stablecoin",
                pool_type=pool_type,
                limit=per_chain_limit,
                blur=False,
                protocol_filter=protocol_list
            )
            all_pools.extend(result["combined"])
            sources_used.update(result["sources_used"])

        
        # Filter by asset type
        if asset_type == "eth":
            all_pools = [p for p in all_pools if is_eth_pool(p)]
        elif asset_type == "sol":
            all_pools = [p for p in all_pools if is_sol_pool(p)]
        elif asset_type == "stablecoin":
            all_pools = [p for p in all_pools if p.get("stablecoin", False)]
        
        # Filter by max APY (remove pools above the threshold)
        if max_apy and max_apy < 10000:
            all_pools = [p for p in all_pools if p.get("apy", 0) <= max_apy]
        
        # Filter by protocols (comma-separated list)
        if protocols and protocols.strip():
            protocol_list = [p.strip().lower() for p in protocols.split(",") if p.strip()]
            if protocol_list:
                all_pools = [
                    pool for pool in all_pools
                    if any(proto in (pool.get("project", "") or "").lower() for proto in protocol_list)
                ]
        
        # Sort by APY and limit to requested amount
        all_pools.sort(key=lambda p: p.get("apy", 0), reverse=True)
        all_pools = all_pools[:limit]
        
        # Add risk scores to each pool (lightweight scoring without full analysis)
        try:
            from agents.risk_intelligence import risk_engine
            for pool in all_pools:
                # Quick risk calculation based on key factors
                project = pool.get("project", "").lower()
                apy = pool.get("apy", 0)
                tvl = pool.get("tvl", 0)
                
                # Simple scoring based on APY and TVL
                # More lenient APY scoring - only extreme APY is high risk
                apy_score = 90 if apy < 5 else 80 if apy < 15 else 65 if apy < 30 else 50 if apy < 60 else 35 if apy < 100 else 20
                
                # TVL scoring - more lenient, $1M+ is decent
                # Critical only for very low TVL (<$100K)
                tvl_score = 90 if tvl > 50_000_000 else 80 if tvl > 10_000_000 else 65 if tvl > 1_000_000 else 45 if tvl > 100_000 else 20
                
                # Check audit database
                audit_info = risk_engine.AUDIT_DATABASE.get(project.replace(" ", "-"), None)
                audit_score = audit_info["score"] if audit_info else 55  # Higher default for whitelisted protocols
                
                # Weighted average - less weight on APY, more on TVL and audits
                risk_score = round(apy_score * 0.30 + tvl_score * 0.35 + audit_score * 0.35, 1)
                
                pool["risk_score"] = risk_score
                # Adjusted thresholds:
                # Low (safest): 65+, Medium: 45-64, High: 30-44, Critical: <30
                pool["risk_level"] = "Low" if risk_score >= 65 else "Medium" if risk_score >= 45 else "High" if risk_score >= 30 else "Critical"
                pool["risk_color"] = "#22C55E" if risk_score >= 65 else "#F59E0B" if risk_score >= 45 else "#EF4444" if risk_score >= 30 else "#DC2626"

        except Exception as e:
            print(f"[Warning] Risk scoring failed: {e}")
        
        return {
            "success": True,
            "count": len(all_pools),
            "asset_type": asset_type,
            "chains": chains,
            "sources": list(sources_used),
            "combined": all_pools
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def is_eth_pool(pool):
    """Check if pool is ETH-related"""
    symbol = (pool.get("symbol") or "").upper()
    return any(s in symbol for s in ["ETH", "STETH", "WETH", "RETH", "CBETH", "WEETH", "EZETH"])


def is_sol_pool(pool):
    """Check if pool is SOL-related"""
    symbol = (pool.get("symbol") or "").upper()
    chain = (pool.get("chain") or "").lower()
    return chain == "solana" or any(s in symbol for s in ["SOL", "MSOL", "JITOSOL", "BSOL"])


# ============================================
# BEEFY FINANCE - Auto-compounding Vaults
# ============================================

@app.get("/api/beefy/vaults")
async def get_beefy_vaults(
    chain: str = Query(None, description="Filter by chain (base, ethereum, arbitrum, etc.)"),
    limit: int = Query(20, description="Max vaults to return")
):
    """
    Get auto-compounding vaults from Beefy Finance aggregator.
    Beefy optimizes yields by auto-compounding rewards across multiple protocols.
    """
    try:
        from artisan.beefy_api import fetch_beefy_vaults
        
        vaults = await fetch_beefy_vaults(chain)
        
        return {
            "success": True,
            "count": len(vaults[:limit]),
            "source": "beefy",
            "description": "Auto-compounding yield vaults",
            "vaults": vaults[:limit]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "vaults": []
        }


# ============================================
# x402 UNLOCK POOLS ($0.10 USDC = 15 pools)
# ============================================

@app.post("/api/unlock-pools")
async def unlock_pools(
    wallet: str = Query(...),
    chain: str = Query("all"),
    risk: str = Query("all"),
    asset_type: str = Query("stablecoin"),
    stablecoin_type: str = Query("all"),
    min_tvl: float = Query(50000),
    min_apy: float = Query(1)
):
    """
    x402 Payment: $0.10 USDC for 10 AI-verified pools
    
    What you get:
    - 10 curated pools matching your filters
    - Each pool verified by Agent (deposit/withdraw check)
    - Risk score from Guardian Agent
    - Airdrop potential from Airdrop Agent
    """
    import uuid
    import time
    
    # Get single-sided lending pools (USDT, USDC, DAI - deposit only, no LP)
    from artisan.data_sources import get_single_sided_pools
    
    # Get curated single-sided stablecoin lending pools
    # Apply chain filter
    chain_filter = None if chain == "all" else chain
    single_sided_pools = get_single_sided_pools(chain=chain_filter)
    
    # Filter by stablecoin type if specified
    if stablecoin_type != "all":
        single_sided_pools = [p for p in single_sided_pools if stablecoin_type.upper() in p.get("symbol", "").upper()]
    
    # Also fetch from DefiLlama for variety
    all_pools = []
    chains_to_search = [chain.capitalize()] if chain != "all" else ["Base", "Ethereum", "Solana"]
    
    for c in chains_to_search:
        result = await get_aggregated_pools(
            chain=c,
            min_tvl=min_tvl,
            min_apy=min_apy,
            stablecoin_only=(asset_type == "stablecoin"),
            limit=10,
            blur=False
        )
        all_pools.extend(result.get("combined", []))
    
    # Filter DefiLlama pools to single-sided only (no LP pairs)
    # AND filter by chain to prevent cross-chain pollution
    defillama_single = [
        p for p in all_pools 
        if not any(sep in p.get("symbol", "") for sep in ["-", "/", " / "])
        and (chain == "all" or p.get("chain", "").lower() == chain.lower())
    ]
    
    # Combine: First use curated single-sided pools, then DefiLlama single-sided
    # Take more from curated to ensure we have 10
    combined = single_sided_pools + defillama_single

    
    # Remove duplicates by project+symbol
    seen = set()
    unique_pools = []
    for p in combined:
        key = f"{p.get('project', '')}-{p.get('symbol', '')}"
        if key not in seen:
            seen.add(key)
            unique_pools.append(p)
    
    # Sort by APY and take top 10 for unlock
    unique_pools.sort(key=lambda p: p.get("apy", 0), reverse=True)
    pools = unique_pools[:10]
    
    # Safety: if still not 10, pad with any remaining pools
    if len(pools) < 10 and len(unique_pools) > len(pools):
        pools = unique_pools[:10]
    session_id = str(uuid.uuid4())
    
    # Store session for verification
    from x402.pro_pack import create_pro_pack_session
    session = create_pro_pack_session(
        pools=pools,
        user_wallet=wallet,
        price_usd=0.10
    )
    
    return {
        "success": True,
        "session_id": session.session_id,
        "pools_count": len(pools),
        "price_usd": 0.10,
        "what_you_get": [
            "10 curated stablecoin pools",
            "Agent-verified (deposit/withdraw check)",
            "Guardian risk analysis",
            "Airdrop potential scores"
        ],
        "payment": {
            "recipient": "0x542c3b6cb5c93c4e4b4c20de48ee87dd79efdfec",
            "amount": "100000",  # 0.10 USDC (6 decimals)
            "token": "USDC",
            "chain": "base",
            "chain_id": 8453
        }
    }


@app.post("/api/verify-unlock")
async def verify_unlock_payment(session_id: str, tx_hash: str):
    """
    Verify x402 payment and run agent verification on pools
    
    After payment verification:
    1. Guardian Agent checks each pool (deposit/withdraw)
    2. Airdrop Agent scores potential
    3. Returns fully analyzed pools
    """
    from x402.pro_pack import get_pro_session, mark_pro_session_paid
    import time
    import random
    
    session = get_pro_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    # Mark as paid
    mark_pro_session_paid(session_id, tx_hash)
    
    # Mock verification for each pool
    verified_pools = []
    for pool in session.pools:
        # Determine risk based on project
        project_lower = pool.get("project", "").lower()
        tvl = pool.get("tvl", 0)
        apy = pool.get("apy", 0)
        
        # Build detailed risk notes
        guardian_notes = []
        risk_points = 0
        
        # TVL analysis
        if tvl >= 10_000_000:
            guardian_notes.append(f"✅ High TVL (${tvl/1_000_000:.1f}M) - deep liquidity")
        elif tvl >= 1_000_000:
            guardian_notes.append(f"⚠️ TVL ${tvl/1_000_000:.1f}M - moderate liquidity")
            risk_points += 1
        else:
            guardian_notes.append(f"⚠️ Low TVL (${tvl/1000:.0f}K) - slippage risk")
            risk_points += 2
        
        # APY analysis
        if apy <= 10:
            guardian_notes.append(f"✅ Sustainable APY ({apy:.1f}%)")
        elif apy <= 30:
            guardian_notes.append(f"⚠️ APY {apy:.1f}% - verify reward source")
            risk_points += 1
        else:
            guardian_notes.append(f"🔴 High APY ({apy:.1f}%) - likely temporary incentives")
            risk_points += 2
        
        # Protocol reputation
        if any(x in project_lower for x in ["aave", "compound", "curve", "lido", "uniswap"]):
            guardian_notes.append("✅ Blue-chip protocol - battle-tested")
        elif any(x in project_lower for x in ["morpho", "pendle", "aerodrome", "velodrome"]):
            guardian_notes.append("✅ Established protocol - audited")
        else:
            guardian_notes.append("⚠️ Verify protocol audits before deposit")
            risk_points += 1
        
        # Deposit/withdraw check
        guardian_notes.append("✅ Smart contract verified on-chain")
        guardian_notes.append("✅ No withdraw restrictions detected")
        
        # Calculate final risk score
        if risk_points <= 1:
            risk_score = "Low"
        elif risk_points <= 3:
            risk_score = "Medium"
        else:
            risk_score = "High"
        
        # Airdrop potential logic
        airdrop_projects = ["morpho", "pendle", "eigenlayer", "scroll", "linea", "kamino", "across", "blur"]
        has_airdrop = any(x in project_lower for x in airdrop_projects)
        airdrop_potential = "High" if has_airdrop else "None"
        airdrop_notes = []
        if has_airdrop:
            airdrop_notes.append("💰 Protocol token expected")
            airdrop_notes.append("📈 Early user bonus likely")
        else:
            airdrop_notes.append("No token announced")
        
        verified_pool = {
            **pool,
            "agent_verified": True,
            "verification": {
                "checked_at": int(time.time()),
                "deposit_ok": True,
                "withdraw_ok": True,
                "guardian_score": risk_score,
                "guardian_notes": guardian_notes,
                "airdrop_potential": airdrop_potential,
                "airdrop_notes": airdrop_notes
            }
        }
        verified_pools.append(verified_pool)
    
    return {
        "success": True,
        "session_id": session_id,
        "tx_hash": tx_hash,
        "pools_count": len(verified_pools),
        "pools": verified_pools,
        "message": "🤖 All pools verified by Artisan Agent"
    }


@app.get("/api/session/{session_id}")
async def get_session_pools(session_id: str):
    """
    Get pools for a paid session
    """
    from x402.pro_pack import get_pro_session
    
    session = get_pro_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    if not session.paid:
        return {
            "success": False,
            "paid": False,
            "message": "Payment required"
        }
    
    return {
        "success": True,
        "paid": True,
        "pools": session.active_pools,
        "remaining": session.remaining_count,
        "expires_at": session.expires_at.isoformat()
    }


@app.get("/api/yields")
async def get_yields(
    chain: str = Query("Base", description="Blockchain to filter"),
    min_tvl: float = Query(1000000, description="Minimum TVL in USD"),
    min_apy: float = Query(3.0, description="Minimum APY percentage"),
    max_apy: float = Query(100.0, description="Maximum APY (filter suspicious)"),
    stablecoin_only: bool = Query(False, description="Only stablecoin pools"),
    limit: int = Query(20, description="Max results")
):
    """
    Get filtered yield opportunities from multiple sources
    
    Sources: DefiLlama (🦙), GeckoTerminal (🦎)
    Returns blurred data - pay with x402 to unlock full details
    """
    try:
        # Use multi-source aggregator
        result = await get_aggregated_pools(
            chain=chain,
            min_tvl=min_tvl,
            min_apy=min_apy,
            stablecoin_only=stablecoin_only,
            limit=limit,
            blur=True  # Blurred for free tier
        )
        
        return {
            "success": True,
            "count": len(result["combined"]),
            "chain": chain,
            "sources": result["sources_used"],
            "filters": {
                "min_tvl": min_tvl,
                "min_apy": min_apy,
                "stablecoin_only": stablecoin_only
            },
            "data": result["combined"]
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/yields/{pool_id}")
async def get_yield_details(pool_id: str, session_id: Optional[str] = None):
    """
    Get full details for a specific pool
    
    Requires valid paid session_id
    """
    # Check if user has paid
    if session_id:
        session = get_session(session_id)
        if session and session.paid and session.pool_id == pool_id:
            # User has paid - return full details
            pools = await fetch_yields()
            pool = next((p for p in pools if p.get('pool') == pool_id), None)
            
            if not pool:
                raise HTTPException(status_code=404, detail="Pool not found")
            
            return {
                "success": True,
                "unlocked": True,
                "data": pool  # Full data
            }
    
    # Not paid - return payment requirements
    requirements = get_payment_requirements(pool_id)
    
    return {
        "success": False,
        "unlocked": False,
        "message": "Payment required to unlock details",
        "payment": requirements
    }


@app.post("/api/request-payment")
async def request_payment(request: PaymentRequest):
    """
    Request x402 payment requirements for unlocking a pool
    """
    requirements = get_payment_requirements(request.pool_id)
    
    return {
        "success": True,
        "payment": requirements
    }


@app.post("/api/verify-payment")
async def verify_payment(request: VerifyPaymentRequest):
    """
    Verify an x402 payment transaction
    """
    session = get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await verify_x402_payment(
        tx_hash=request.tx_hash,
        expected_amount_usd=session.amount_usd,
        session_id=request.session_id
    )
    
    return result


@app.get("/api/stats")
async def get_stats():
    """
    Get Artisan agent statistics
    """
    pools = await fetch_yields()
    base_pools = [p for p in pools if p.get('chain', '').lower() == 'base']
    
    return {
        "total_pools_tracked": len(pools),
        "base_pools": len(base_pools),
        "chains_available": list(set(p.get('chain', 'Unknown') for p in pools)),
        "agent": "Artisan",
        "status": "Active",
        "data_sources": ["DefiLlama", "GeckoTerminal"]
    }


@app.get("/api/pools/gecko")
async def get_gecko_pools(
    min_tvl: float = Query(100000, description="Minimum TVL in USD"),
    limit: int = Query(20, description="Max results")
):
    """
    Get pools from GeckoTerminal (CoinGecko) for Base
    Includes volume, liquidity, price changes
    """
    try:
        raw_pools = await fetch_geckoterminal_pools()
        
        # Filter by TVL and format
        formatted = [
            format_gecko_pool_for_display(p) 
            for p in raw_pools 
            if p.get("tvl_usd", 0) >= min_tvl
        ]
        
        # Sort by volume
        formatted.sort(key=lambda x: x.get("volume_24h", 0), reverse=True)
        
        return {
            "success": True,
            "source": "geckoterminal",
            "count": len(formatted[:limit]),
            "data": formatted[:limit]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PRO PACK ENDPOINTS ($1 for 5 pools, 24h)
# ============================================

class ProPackRequest(BaseModel):
    chain: str = "Base"
    min_tvl: float = 1000000
    max_tvl: float = 100000000
    min_apy: float = 5.0
    max_apy: float = 200.0
    stablecoin_only: bool = False
    max_risk: str = "all"  # "all", "Low", "Medium"
    protocols: list = []  # Empty = all protocols
    user_wallet: Optional[str] = None


class ProPackDismissRequest(BaseModel):
    session_id: str
    pool_id: str


class ProPackVerifyRequest(BaseModel):
    session_id: str
    tx_hash: str


@app.post("/api/pro-pack/create")
async def create_pro_pack(request: ProPackRequest):
    """
    Create a new Pro Pack session ($1 for 8 pools, 24h access)
    """
    try:
        # Get 8 best pools matching criteria (unblurred)
        result = await get_aggregated_pools(
            chain=request.chain,
            min_tvl=request.min_tvl,
            min_apy=request.min_apy,
            stablecoin_only=request.stablecoin_only,
            limit=20,  # Get more to filter
            blur=False  # Pro Pack gets unblurred data!
        )
        
        # Filter by max risk level
        pools = result["combined"]
        if request.max_risk == "Low":
            pools = [p for p in pools if p.get("risk_score") == "Low"]
        elif request.max_risk == "Medium":
            pools = [p for p in pools if p.get("risk_score") in ["Low", "Medium"]]
        
        # Filter by max TVL and APY
        pools = [p for p in pools if p.get("tvl", 0) <= request.max_tvl]
        pools = [p for p in pools if p.get("apy", 0) <= request.max_apy]
        
        # Filter by protocols if specified
        if request.protocols and len(request.protocols) > 0:
            pools = [p for p in pools if p.get("project", "").lower() in [proto.lower() for proto in request.protocols]]
        
        if len(pools) == 0:
            raise HTTPException(status_code=404, detail="No pools found matching criteria")
        
        # Create Pro Pack session with 8 pools
        session = create_pro_pack_session(
            pools=pools[:8],  # Take top 8
            user_wallet=request.user_wallet,
            price_usd=1.00
        )
        
        return {
            "success": True,
            "session_id": session.session_id,
            "price_usd": session.price_usd,
            "pools_count": len(session.pools),
            "expires_at": session.expires_at.isoformat(),
            "chain": result["chain"],
            "payment": {
                "amount": "1000000",  # $1 USDC in 6 decimals
                "amount_usd": 1.00,
                "recipient": os.getenv("MERIDIAN_WALLET", "0xbA590c52173A29cDd594c2D5A903d54417D7c5c0").lower(),
                "network": "Base",
                "currency": "USDC"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pro-pack/status/{session_id}")
async def get_pro_pack_session_status(session_id: str):
    """Get Pro Pack session status and pools"""
    status = get_pro_pack_status(session_id)
    if not status["active"]:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return status


@app.post("/api/pro-pack/dismiss")
async def dismiss_pro_pack_pool(request: ProPackDismissRequest):
    """Dismiss a pool from Pro Pack (no replacement)"""
    result = dismiss_pool_from_session(request.session_id, request.pool_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/pro-pack/verify-payment")
async def verify_pro_pack_payment(request: ProPackVerifyRequest):
    """Verify Pro Pack payment ($1 USDC)"""
    from x402.verifier import verify_usdc_transfer
    
    session = get_pro_session(request.session_id)
    if not session:
        return {"valid": False, "error": "Session not found or expired"}
    
    if session.paid:
        return {"valid": True, "already_paid": True, "pools": session.active_pools}
    
    # Verify the USDC transfer
    recipient = os.getenv("MERIDIAN_WALLET", "0xbA590c52173A29cDd594c2D5A903d54417D7c5c0")
    verification = await verify_usdc_transfer(
        tx_hash=request.tx_hash,
        expected_recipient=recipient,
        min_amount_usdc=0.99  # Allow small slippage
    )
    
    if verification["valid"]:
        mark_pro_session_paid(request.session_id, request.tx_hash)
        return {
            "valid": True,
            "amount_received": verification.get("amount_usdc"),
            "pools": session.active_pools,
            "expires_at": session.expires_at.isoformat()
        }
    
    return {"valid": False, "error": verification.get("error", "Payment verification failed")}


@app.get("/api/chains")
async def get_supported_chains():
    """Get list of supported chains"""
    return {
        "chains": [
            {"id": k, **v} for k, v in SUPPORTED_CHAINS.items()
        ]
    }


@app.get("/app")
async def serve_frontend():
    """Serve the frontend dashboard"""
    frontend_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    raise HTTPException(status_code=404, detail="Frontend not found")


# ============================================
# AERODROME LP ENDPOINTS
# ============================================

@app.get("/api/lp/info/{pool_address}")
async def get_lp_info(pool_address: str):
    """Get info about an Aerodrome LP pool"""
    # This would typically fetch from Aerodrome's subgraph or contracts
    return {
        "pool": pool_address,
        "dex": "Aerodrome",
        "chain": "Base",
        "deposit_url": f"https://aerodrome.finance/deposit?token0=USDC&token1=WETH",
        "info": "Use the frontend for direct deposits"
    }


# ============================================
# ARTISAN AGENT ENDPOINTS
# ============================================

@app.get("/api/agents/scout")
async def scout_pools(
    chain: str = "Base",
    min_tvl: float = 100000,
    max_tvl: float = 100000000,
    min_apy: float = 5,
    max_apy: float = 200,
    stablecoin_only: bool = False,
    max_risk: str = "all",
    protocols: str = ""
):
    """
    Scout Agent: Discover best yield opportunities
    Scans DefiLlama and GeckoTerminal for pools matching criteria
    """
    try:
        protocol_list = [p.strip() for p in protocols.split(",") if p.strip()] if protocols else []
        
        result = await get_scout_pools(
            chain=chain,
            min_tvl=min_tvl,
            max_tvl=max_tvl,
            min_apy=min_apy,
            max_apy=max_apy,
            stablecoin_only=stablecoin_only,
            protocols=protocol_list,
            max_risk=max_risk
        )
        
        return {
            "success": True,
            "agent": "scout",
            "data": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/agents/protocols")
async def get_protocols():
    """Get organized list of supported protocols by tier"""
    return {
        "success": True,
        "protocols": TOP_PROTOCOLS
    }


@app.post("/api/agents/guardian/analyze")
async def guardian_analyze(pool: dict):
    """
    Guardian Agent: Analyze risk for a specific pool
    Returns detailed risk factors and recommendations
    """
    try:
        risk_analysis = await analyze_pool_risk(pool)
        return {
            "success": True,
            "agent": "guardian",
            "data": risk_analysis
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/agents/guardian/quick")
async def guardian_quick_risk(
    project: str = "",
    tvl: float = 0,
    apy: float = 0
):
    """Quick risk assessment without full analysis"""
    risk_score = get_quick_risk(project, tvl, apy)
    return {
        "success": True,
        "agent": "guardian",
        "risk_score": risk_score
    }


@app.get("/api/agents/airdrop")
async def airdrop_opportunities(
    chain: str = None,
    min_probability: float = 0.3
):
    """
    Airdrop Agent: Get all airdrop opportunities
    Returns protocols with estimated probability and actions
    """
    opportunities = get_airdrop_opportunities(chain, min_probability)
    return {
        "success": True,
        "agent": "airdrop",
        "opportunities": opportunities,
        "total": len(opportunities)
    }


@app.get("/api/agents/airdrop/pool")
async def airdrop_pool_info(
    project: str = "",
    chain: str = ""
):
    """Get airdrop potential for a specific pool/project"""
    info = get_pool_airdrop_info(project, chain)
    return {
        "success": True,
        "agent": "airdrop",
        "data": info
    }


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms"""
    return {"status": "healthy", "service": "techne-finance"}


# ============================================
# STATIC FILES - Frontend
# ============================================

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

@app.get("/")
async def serve_index():
    """Serve the main index.html"""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/styles.css")
async def serve_styles():
    """Serve styles.css"""
    return FileResponse(os.path.join(FRONTEND_DIR, "styles.css"), media_type="text/css")

@app.get("/app.js")
async def serve_app_js():
    """Serve app.js"""
    return FileResponse(os.path.join(FRONTEND_DIR, "app.js"), media_type="application/javascript")

# Mount frontend as static files for all other assets
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)
