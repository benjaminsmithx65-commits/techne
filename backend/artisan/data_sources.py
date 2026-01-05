"""
Multi-Source Data Aggregator for Techne.finance
Sources: DefiLlama (yields), GeckoTerminal (pools), CoinGecko (prices)
Supported Chains: Base, Ethereum, Solana, Monad, Hyperliquid
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

# ============================================
# CHAIN CONFIGURATION
# ============================================

SUPPORTED_CHAINS = {
    "base": {
        "name": "Base",
        "gecko_network": "base",
        "defillama_name": "Base",
        "icon": "🔵",
        "explorer": "https://basescan.org"
    },
    "ethereum": {
        "name": "Ethereum",
        "gecko_network": "eth",
        "defillama_name": "Ethereum",
        "icon": "⟠",
        "explorer": "https://etherscan.io"
    },
    "solana": {
        "name": "Solana",
        "gecko_network": "solana",
        "defillama_name": "Solana",
        "icon": "◎",
        "explorer": "https://solscan.io"
    },
    "hyperliquid": {
        "name": "Hyperliquid",
        "gecko_network": None,  # No GeckoTerminal support yet
        "defillama_name": "Hyperliquid",
        "icon": "💧",
        "explorer": "https://hyperliquid.xyz"
    },
    "monad": {
        "name": "Monad",
        "gecko_network": None,  # Not launched yet
        "defillama_name": None,  # Not on DefiLlama yet
        "icon": "🟣",
        "explorer": None
    }
}

def get_chain_config(chain: str) -> Dict[str, Any]:
    """Get chain configuration by name (case-insensitive)"""
    return SUPPORTED_CHAINS.get(chain.lower(), SUPPORTED_CHAINS["base"])

# ============================================
# API ENDPOINTS
# ============================================

APIS = {
    "defillama": {
        "yields": "https://yields.llama.fi/pools",
        "protocols": "https://api.llama.fi/protocols",
        "badge": "🦙",
        "color": "#1A5B1A"
    },
    "geckoterminal": {
        "pools_base": "https://api.geckoterminal.com/api/v2/networks/{network}/pools",
        "trending": "https://api.geckoterminal.com/api/v2/networks/{network}/trending_pools",
        "badge": "🦎", 
        "color": "#6BAE54"
    },
    "coingecko": {
        "prices": "https://api.coingecko.com/api/v3/simple/price",
        "badge": "🪙",
        "color": "#8DC647"
    }
}

# ============================================
# STABLECOIN WHITELIST - For accurate IL risk
# ============================================

STABLE_WHITELIST = {
    'USDC', 'USDT', 'DAI', 'USDbC', 'FRAX', 'USDe', 'crvUSD', 
    'LUSD', 'sUSD', 'BUSD', 'TUSD', 'GUSD', 'USDP', 'PYUSD',
    'USD+', 'DOLA', 'MIM', 'alUSD', 'USDD', 'USDN', 'USDX'
}

# ============================================
# PROTOCOL CATEGORIES - For pool type labels
# Dual-sided (is_single=False) = IL Risk!
# ============================================
PROTOCOL_CATEGORIES = {
    # Lending Protocols (Single-sided, No IL)
    "lending": {
        "protocols": ["aave", "compound", "morpho", "moonwell", "seamless", "sonne", 
                      "exactly", "radiant", "benqi", "solend", "marginfi", "kamino",
                      "spark", "maker", "frax-lend"],
        "icon": "🏦",
        "label": "Lending",
        "is_single": True
    },
    # Yield Vaults (Single deposit, auto-compound)
    "vault": {
        "protocols": ["beefy", "yearn", "convex", "origin", "infinifi", "stargate"],
        "icon": "🏛️",
        "label": "Vault",
        "is_single": True
    },
    # Liquid Staking (Single-sided, No IL)
    "staking": {
        "protocols": ["lido", "rocketpool", "marinade", "jito", "sanctum", "frax",
                      "eigenlayer", "mango"],
        "icon": "💎",
        "label": "Staking",
        "is_single": True
    },
    # AMM DEX (Dual-sided LP = IL Risk!)
    "amm": {
        "protocols": ["uniswap", "curve", "balancer", "aerodrome", "velodrome", 
                      "raydium", "orca", "meteora", "sushiswap"],
        "icon": "🔄",
        "label": "AMM",
        "is_single": False  # IL RISK!
    },
    # Perpetuals/Derivatives (Single-sided usually)
    "perps": {
        "protocols": ["gmx", "drift", "avantis", "jupiter-perps"],
        "icon": "📊",
        "label": "Perps",
        "is_single": True
    },
    # Reward Aggregators (Depends on underlying)
    "rewards": {
        "protocols": ["merkl", "pendle", "extra"],
        "icon": "🎁",
        "label": "Rewards",
        "is_single": False  # Usually on top of LP = IL Risk
    }
}

def get_pool_category(project: str, symbol: str = "") -> dict:
    """Get pool category based on protocol name."""
    project_lower = project.lower() if project else ""
    
    for cat_name, cat_data in PROTOCOL_CATEGORIES.items():
        for proto in cat_data["protocols"]:
            if proto in project_lower:
                return {
                    "category": cat_name,
                    "category_icon": cat_data["icon"],
                    "category_label": cat_data["label"],
                    "is_single_sided": cat_data["is_single"]
                }
    
    # Fallback: detect by symbol if has separator = dual-sided
    has_separator = any(sep in symbol for sep in ["-", "/", " / "])
    if has_separator:
        return {
            "category": "lp",
            "category_icon": "💧",
            "category_label": "LP Pool",
            "is_single_sided": False
        }
    
    return {
        "category": "unknown",
        "category_icon": "❓",
        "category_label": "DeFi",
        "is_single_sided": True
    }

def is_stablecoin(token: str) -> bool:
    """Check if token symbol is a known stablecoin"""
    if not token:
        return False
    token_clean = token.upper().strip()
    # Direct match
    if token_clean in STABLE_WHITELIST:
        return True
    # Partial match (e.g., USDC.e, axlUSDC)
    for stable in STABLE_WHITELIST:
        if stable in token_clean:
            return True
    return False

def classify_pool_type(symbol: str) -> dict:
    """
    Classify pool as stable/volatile and calculate IL risk.
    Both tokens must be stable for pool to be 'stable' type.
    """
    if not symbol:
        return {"pool_type": "volatile", "il_risk": "yes", "il_risk_level": "High"}
    
    # Parse tokens from symbol (e.g., "USDC-AVAIL" or "USDC/WETH")
    tokens = [t.strip() for t in symbol.replace('-', '/').split('/')]
    tokens = [t.split(' ')[0] for t in tokens if t]  # Remove % parts like "0.05%"
    
    if len(tokens) < 2:
        return {"pool_type": "volatile", "il_risk": "yes", "il_risk_level": "High"}
    
    all_stable = all(is_stablecoin(t) for t in tokens)
    
    return {
        "pool_type": "stable" if all_stable else "volatile",
        "il_risk": "no" if all_stable else "yes",
        "il_risk_level": "None" if all_stable else "High",
        "tokens": tokens,
        "token_stability": {t: is_stablecoin(t) for t in tokens}
    }


# ============================================

# Import advanced caching infrastructure
try:
    from infrastructure.api_cache import cache_manager, CacheEndpointType
    from infrastructure.request_coalescer import request_coalescer
    from infrastructure.rate_limiter import rate_limiter, RateLimitTier
    ADVANCED_CACHE_AVAILABLE = True
except ImportError:
    ADVANCED_CACHE_AVAILABLE = False
    # Fallback to basic cache if infrastructure not available
    print("[DataSources] Warning: Advanced cache not available, using basic cache")

# Basic fallback cache (used when advanced not available)
_cache = {
    "defillama_yields": {"data": None, "timestamp": None},
    "geckoterminal_pools": {"data": None, "timestamp": None},
    "coingecko_prices": {"data": None, "timestamp": None},
    "ttl_minutes": 2  # Reduced from 5 to 2 for fresher data
}

def is_cache_valid(key: str) -> bool:
    """Check if basic cache is still valid."""
    cache = _cache.get(key)
    if not cache or not cache["data"] or not cache["timestamp"]:
        return False
    return datetime.now() - cache["timestamp"] < timedelta(minutes=_cache["ttl_minutes"])


# ============================================
# PROJECT WHITELIST (Multi-chain)
# ============================================
PROJECT_WHITELIST = {
    # Base chain protocols
    "morpho", "morpho-blue", "morpho-v1",
    "aave", "aave-v3", "aave-v2",
    "moonwell",
    "compound", "compound-v3", "compound-v2",
    "aerodrome", "aerodrome-v2", "aerodrome-slipstream",
    "beefy",
    "merkl",  # Reward aggregator
    "avantis",  # Perpetuals
    "origin", "origin-ether",  # Origin Protocol
    "extra-finance", "extra",
    "seamless", "seamless-protocol",
    "sonne", "sonne-finance",
    "exactly", "exactly-protocol",
    "infinifi",
    
    # Solana protocols
    "marinade", "marinade-finance",
    "jito", "jito-staking",
    "drift", "drift-protocol",
    "marginfi", "margin-fi",
    "kamino", "kamino-finance",
    "meteora",
    "sanctum",
    "jupiter", "jupiter-perps",
    "solend",
    "mango", "mango-markets",
    "raydium",
    "orca",
    
    # Ethereum/Multi-chain protocols
    "lido", "lido-staked-ether",
    "curve", "curve-dex",
    "convex", "convex-finance",
    "yearn", "yearn-finance",
    "uniswap", "uniswap-v3", "uniswap-v4",
    "sushiswap",
    "balancer",
    "gmx",
    "pendle",
    "eigenlayer", "eigen-layer",
    "rocketpool", "rocket-pool",
    "frax", "frax-finance", "frax-lend",
    "maker", "makerdao",
    "spark", "spark-protocol",
    "radiant", "radiant-capital",
    "benqi",
    "stargate",
    "velodrome", "velodrome-v2",
}

# ============================================
# DEFILLAMA - Yield Farming
# ============================================

# NOTE: Previously had hardcoded SINGLE_SIDED_LENDING_POOLS list.
# Now relying 100% on live DefiLlama API data for real-time APY/TVL.


async def fetch_defillama_yields(chain: str = "Base") -> List[Dict[str, Any]]:
    """
    Fetch yields from DefiLlama with advanced caching.
    
    OPTIMIZATIONS:
    - Stale-while-revalidate: Returns stale data instantly, refreshes in background
    - Request coalescing: Multiple concurrent requests share one API call
    - Rate limiting: Prevents API throttling
    - Fallback to cache on errors
    """
    cache_key = f"defillama_yields_{chain.lower()}"
    
    # Initialize basic cache entry if needed (fallback)
    if cache_key not in _cache:
        _cache[cache_key] = {"data": None, "timestamp": None}
    
    async def _do_fetch() -> List[Dict[str, Any]]:
        """Actual API fetch - separated for coalescing."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(APIS["defillama"]["yields"])
            response.raise_for_status()
            data = response.json()
            
            pools = data.get("data", [])
            
            # Filter by chain and add source info
            filtered = []
            for pool in pools:
                if pool.get("chain", "").lower() == chain.lower():
                    # STRICT WHITELIST CHECK
                    project = (pool.get("project") or "").lower()
                    if not any(allowed in project for allowed in PROJECT_WHITELIST):
                        continue

                    pool["_source"] = "defillama"
                    pool["_source_badge"] = APIS["defillama"]["badge"]
                    pool["_source_color"] = APIS["defillama"]["color"]
                    filtered.append(pool)
            
            # Update basic cache as backup
            _cache[cache_key]["data"] = filtered
            _cache[cache_key]["timestamp"] = datetime.now()
            
            return filtered
    
    # Use advanced cache if available
    if ADVANCED_CACHE_AVAILABLE:
        try:
            # Request coalescing: if 10 users request same data, only 1 API call
            result = await request_coalescer.execute(
                key=cache_key,
                fetcher=lambda: cache_manager.get(
                    endpoint=cache_key,
                    endpoint_type=CacheEndpointType.POOLS,
                    fetcher=_do_fetch
                )
            )
            if result:
                return result
        except Exception as e:
            print(f"[DefiLlama] Advanced cache error: {e}, falling back to basic")
    
    # Fallback to basic cache
    if is_cache_valid(cache_key):
        return _cache[cache_key]["data"]
    
    try:
        return await _do_fetch()
    except Exception as e:
        print(f"[DefiLlama] Error: {e}")
        return _cache[cache_key]["data"] or []



def format_defillama_pool(pool: Dict[str, Any], blur: bool = True) -> Dict[str, Any]:
    """Format DefiLlama pool for frontend with premium analytics"""
    tvl = pool.get("tvlUsd", 0) or 0
    apy = pool.get("apy", 0) or 0
    chain_name = pool.get("chain", "Unknown")
    chain_config = get_chain_config(chain_name)
    
    # Risk calculation with reasons
    risk_points = 0
    risk_reasons = []
    
    if tvl < 1000000:
        risk_points += 2
        risk_reasons.append(f"TVL < $1M (${tvl:,.0f})")
    if apy > 50:
        risk_points += 2
        risk_reasons.append(f"High APY ({apy:.1f}%)")
    if pool.get("ilRisk") == "yes":
        risk_points += 1
        risk_reasons.append("Impermanent Loss risk")
    
    risk = "Low" if risk_points <= 2 else "Medium" if risk_points <= 4 else "High"
    if not risk_reasons:
        risk_reasons.append("Stable pool metrics")
    
    # Generate pool link (DefiLlama pools page)
    pool_link = f"https://defillama.com/yields/pool/{pool.get('pool')}" if pool.get('pool') else None
    
    # ============================================
    # PREMIUM ANALYTICS (justifies 0.1 USDC)
    # ============================================
    
    # APY Breakdown
    apy_base = pool.get("apyBase", 0) or 0
    apy_reward = pool.get("apyReward", 0) or 0
    
    # TVL & APY Changes (1D, 7D, 30D percentages)
    tvl_change_1d = pool.get("tvlPct1D", 0) or 0
    tvl_change_7d = pool.get("tvlPct7D", 0) or 0
    apy_change_1d = pool.get("apyPct1D", 0) or 0
    apy_change_7d = pool.get("apyPct7D", 0) or 0
    apy_change_30d = pool.get("apyPct30D", 0) or 0
    
    # Volume (if available)
    volume_1d = pool.get("volumeUsd1d", 0) or 0
    volume_7d = pool.get("volumeUsd7d", 0) or 0
    
    # Pool age - use apyBaseInception if available
    apy_inception = pool.get("apyBaseInception", None)
    
    # Pool count by same project (for diversification analysis)
    pool_count = pool.get("count", 0)
    
    # Exposure type
    symbol = pool.get("symbol", "")
    exposure_type = "Single-Asset" if not any(sep in symbol for sep in ["-", "/"]) else "LP Pair"
    underlying_tokens = symbol.split("-") if "-" in symbol else symbol.split("/") if "/" in symbol else [symbol]
    
    # Smart Risk Insights based on trends
    premium_insights = []
    
    # TVL trend analysis
    if tvl_change_7d > 20:
        premium_insights.append({"type": "positive", "text": f"📈 Strong TVL growth (+{tvl_change_7d:.1f}% 7D)", "icon": "🟢"})
    elif tvl_change_7d < -20:
        premium_insights.append({"type": "warning", "text": f"📉 TVL declining ({tvl_change_7d:.1f}% 7D)", "icon": "🔴"})
        risk_reasons.append(f"TVL down {abs(tvl_change_7d):.1f}% this week")
    elif tvl_change_7d > 5:
        premium_insights.append({"type": "neutral", "text": f"📊 Healthy TVL growth (+{tvl_change_7d:.1f}% 7D)", "icon": "🟡"})
    
    # APY stability analysis
    if apy_change_7d > 50:
        premium_insights.append({"type": "warning", "text": f"⚠️ APY volatile (+{apy_change_7d:.1f}% 7D) - likely temporary boost", "icon": "🔴"})
    elif apy_change_7d < -30:
        premium_insights.append({"type": "warning", "text": f"⚠️ APY declining ({apy_change_7d:.1f}% 7D)", "icon": "🟡"})
    elif abs(apy_change_7d) < 10:
        premium_insights.append({"type": "positive", "text": f"✅ Stable APY (±{abs(apy_change_7d):.1f}% 7D)", "icon": "🟢"})
    
    # Yield composition analysis
    if apy_reward > 0 and apy_base > 0:
        reward_pct = (apy_reward / apy) * 100 if apy > 0 else 0
        if reward_pct > 70:
            premium_insights.append({"type": "warning", "text": f"⚠️ {reward_pct:.0f}% from rewards (emissions may end)", "icon": "🟡"})
        else:
            premium_insights.append({"type": "positive", "text": f"✅ {100-reward_pct:.0f}% sustainable base yield", "icon": "🟢"})
    elif apy_base > 0 and apy_reward == 0:
        premium_insights.append({"type": "positive", "text": "✅ 100% organic yield (no token emissions)", "icon": "🟢"})
    
    # Volume insight
    if volume_1d > 1000000:
        premium_insights.append({"type": "positive", "text": f"💎 High volume (${volume_1d/1000000:.1f}M/day)", "icon": "🟢"})
    elif volume_1d > 100000:
        premium_insights.append({"type": "neutral", "text": f"📊 Active pool (${volume_1d/1000:.0f}K/day)", "icon": "🟡"})
    
    # FIXED: Use classify_pool_type for accurate IL risk
    classification = classify_pool_type(pool.get("symbol", ""))
    
    # Extract reward token from project name or symbol
    reward_token = pool.get("rewardTokens", ["TOKEN"])[0] if pool.get("rewardTokens") else "TOKEN"
    
    # Build explorer link
    pool_address = pool.get("pool", "").split("_")[-1] if "_" in pool.get("pool", "") else ""
    explorer_link = f"{chain_config.get('explorer')}/address/{pool_address}" if pool_address and chain_config.get('explorer') else None
    
    return {
        "id": pool.get("pool"),
        "chain": chain_name,
        "chain_icon": chain_config.get("icon", ""),
        "explorer": chain_config.get("explorer"),
        "explorer_link": explorer_link,
        "pool_link": pool_link,
        "project": "***" if blur else pool.get("project", "Unknown"),
        "symbol": pool.get("symbol", "???"),
        "apy": round(apy, 2),
        "tvl": round(tvl),
        "tvl_formatted": f"${tvl:,.0f}",
        "volume_24h": round(volume_1d),
        "volume_24h_formatted": f"${volume_1d:,.0f}" if volume_1d else None,
        "volume_7d": round(volume_7d),
        "stablecoin": classification["pool_type"] == "stable",  # FIXED
        "pool_type": classification["pool_type"],  # NEW: "stable" or "volatile"
        "risk_score": risk,
        "risk_reasons": risk_reasons,
        "il_risk": classification["il_risk"],  # FIXED: Uses token analysis
        "il_risk_level": classification["il_risk_level"],  # NEW: "None" or "High"
        "reward_token": reward_token,  # NEW: Token symbol for rewards
        "source": "defillama",
        "source_badge": "",
        "source_name": "DefiLlama",
        "unlock_price_usd": 0.50,
        # PREMIUM FIELDS
        "apy_base": round(apy_base, 2),
        "apy_reward": round(apy_reward, 2),
        "tvl_change_1d": round(tvl_change_1d, 2),
        "tvl_change_7d": round(tvl_change_7d, 2),
        "apy_change_1d": round(apy_change_1d, 2),
        "apy_change_7d": round(apy_change_7d, 2),
        "apy_change_30d": round(apy_change_30d, 2),
        "apy_inception": round(apy_inception, 2) if apy_inception else None,
        "exposure_type": exposure_type,
        "underlying_tokens": underlying_tokens,
        "premium_insights": premium_insights,
        # POOL CATEGORY - Auto-classified by protocol
        **get_pool_category(pool.get("project", ""), pool.get("symbol", "")),
    }


# ============================================
# GECKOTERMINAL - DEX Pools & Volume
# ============================================

async def fetch_geckoterminal_pools(chain: str = "Base", page: int = 1) -> List[Dict[str, Any]]:
    """Fetch pools from GeckoTerminal for any supported chain"""
    chain_config = get_chain_config(chain)
    network = chain_config.get("gecko_network")
    
    if not network:
        print(f"[GeckoTerminal] Chain {chain} not supported")
        return []
    
    cache_key = f"geckoterminal_{chain.lower()}"
    
    # Initialize cache if needed
    if cache_key not in _cache:
        _cache[cache_key] = {"data": None, "timestamp": None}
    
    if is_cache_valid(cache_key):
        return _cache[cache_key]["data"]
    
    try:
        url = APIS['geckoterminal']['pools_base'].format(network=network)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{url}?page={page}")
            response.raise_for_status()
            data = response.json()
            
            pools = []
            for pool in data.get("data", []):
                attrs = pool.get("attributes", {})
                rels = pool.get("relationships", {})
                
                # Check whitelist against DEX name
                dex_name = rels.get("dex", {}).get("data", {}).get("id", "unknown").lower()
                pool_name = attrs.get("name", "").lower()
                
                # Strict check: DEX ID must be in whitelist
                # (e.g. "aerodrome", "uniswap-v3-base")
                is_whitelisted = False
                for allowed in PROJECT_WHITELIST:
                     if allowed in dex_name:
                         is_whitelisted = True
                         break
                
                if not is_whitelisted:
                     continue
                
                pools.append({
                    "pool": pool.get("id"),
                    "name": attrs.get("name"),
                    "address": attrs.get("address"),
                    "dex": rels.get("dex", {}).get("data", {}).get("id", "unknown"),
                    "chain": chain_config["name"],
                    "chain_icon": chain_config["icon"],
                    "explorer": chain_config["explorer"],
                    "tvl_usd": float(attrs.get("reserve_in_usd", 0) or 0),
                    "volume_24h": float(attrs.get("volume_usd", {}).get("h24", 0) or 0),
                    "price_change_24h": float(attrs.get("price_change_percentage", {}).get("h24", 0) or 0),
                    "transactions_24h": (
                        attrs.get("transactions", {}).get("h24", {}).get("buys", 0) +
                        attrs.get("transactions", {}).get("h24", {}).get("sells", 0)
                    ),
                    "_source": "geckoterminal",
                    "_source_badge": APIS["geckoterminal"]["badge"],
                    "_source_color": APIS["geckoterminal"]["color"]
                })
            
            _cache[cache_key]["data"] = pools
            _cache[cache_key]["timestamp"] = datetime.now()
            
            return pools
    except Exception as e:
        print(f"[GeckoTerminal] Error for {chain}: {e}")
        return _cache[cache_key]["data"] or []


def format_gecko_pool(pool: Dict[str, Any], blur: bool = True) -> Dict[str, Any]:
    """Format GeckoTerminal pool for frontend"""
    tvl = pool.get("tvl_usd", 0)
    volume = pool.get("volume_24h", 0)
    chain = pool.get("chain", "Base")
    txns = pool.get("transactions_24h", 0)
    
    # Estimate APY from volume (very rough)
    estimated_apy = (volume * 0.003 / max(tvl, 1)) * 365 * 100 if tvl > 0 else 0
    estimated_apy = min(estimated_apy, 500)  # Cap
    
    # Risk calculation with reasons
    risk_points = 0
    risk_reasons = []
    
    if tvl < 100000:
        risk_points += 3
        risk_reasons.append(f"Low TVL (${tvl:,.0f})")
    elif tvl < 500000:
        risk_points += 2
        risk_reasons.append(f"TVL < $500K (${tvl:,.0f})")
    
    if txns < 100:
        risk_points += 2
        risk_reasons.append(f"Low activity ({txns} txns/24h)")
    
    if estimated_apy > 100:
        risk_points += 1
        risk_reasons.append(f"Very high APY ({estimated_apy:.0f}%)")
    
    # IL Risk check
    has_il = "ETH" in pool.get("name", "") and "USD" not in pool.get("name", "").upper()
    if has_il:
        risk_points += 1
        risk_reasons.append("Impermanent Loss risk")
    
    risk = "Low" if risk_points <= 2 else "Medium" if risk_points <= 4 else "High"
    if not risk_reasons:
        risk_reasons.append("Stable pool metrics")
    
    return {
        "id": pool.get("pool"),
        "chain": chain,
        "chain_icon": pool.get("chain_icon", ""),
        "explorer": pool.get("explorer"),
        "pool_link": f"{pool.get('explorer')}/address/{pool.get('address')}" if pool.get("explorer") and pool.get("address") else None,
        "project": "***" if blur else pool.get("dex", "DEX"),
        "symbol": pool.get("name", "???"),
        "apy": round(estimated_apy, 2),
        "tvl": round(tvl),
        "tvl_formatted": f"${tvl:,.0f}",
        "volume_24h": round(volume),
        "volume_formatted": f"${volume:,.0f}",
        "stablecoin": any(s in pool.get("name", "").upper() for s in ["USDC", "USDT", "DAI"]),
        "risk_score": risk,
        "risk_reasons": risk_reasons,
        "il_risk": "yes" if has_il else "no",
        "source": "geckoterminal",
        "source_badge": "",
        "source_name": "GeckoTerminal",
        "unlock_price_usd": 0.50
    }


# ============================================
# COINGECKO - Price Data (supplementary)
# ============================================

async def fetch_coingecko_prices(symbols: List[str] = None) -> Dict[str, float]:
    """Fetch token prices from CoinGecko"""
    cache_key = "coingecko_prices"
    
    if is_cache_valid(cache_key):
        return _cache[cache_key]["data"]
    
    try:
        default_ids = "ethereum,usd-coin,wrapped-bitcoin"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                APIS["coingecko"]["prices"],
                params={"ids": default_ids, "vs_currencies": "usd"}
            )
            response.raise_for_status()
            
            data = response.json()
            prices = {k: v.get("usd", 0) for k, v in data.items()}
            
            _cache[cache_key]["data"] = prices
            _cache[cache_key]["timestamp"] = datetime.now()
            
            return prices
    except Exception as e:
        print(f"[CoinGecko] Error: {e}")
        return _cache[cache_key]["data"] or {}


# ============================================
# AGGREGATOR - Combine all sources
# ============================================

async def get_aggregated_pools(
    chain: str = "Base",
    min_tvl: float = 100000,
    min_apy: float = 1.0,
    stablecoin_only: bool = False,
    pool_type: str = "all",  # "single", "dual", "all"
    limit: int = 20,
    blur: bool = False,
    protocol_filter: List[str] = None
) -> Dict[str, Any]:
    """
    Get pools from all available sources for a specific chain.
    """
    chain_config = get_chain_config(chain)
    
    results = {
        "defillama": [],
        "geckoterminal": [],
        "combined": [],
        "sources_used": []
    }
    
    # Fetch from both sources in parallel
    try:
        defillama_pools, gecko_pools = await asyncio.gather(
            fetch_defillama_yields(chain),
            fetch_geckoterminal_pools(chain),  # Pass chain parameter
            return_exceptions=True
        )
    except Exception as e:
        print(f"[Aggregator] Error: {e}")
        defillama_pools, gecko_pools = [], []
    
    # Handle exceptions
    if isinstance(defillama_pools, Exception):
        print(f"[Aggregator] DefiLlama failed: {defillama_pools}")
        defillama_pools = []
    if isinstance(gecko_pools, Exception):
        print(f"[Aggregator] GeckoTerminal failed: {gecko_pools}")
        gecko_pools = []
    
    # Normalise protocol filter
    allowed_protocols = set(p.lower() for p in (protocol_filter or []))

    # Process DefiLlama pools
    if defillama_pools:
        results["sources_used"].append("defillama")
        for pool in defillama_pools:
            tvl = pool.get("tvlUsd", 0) or 0
            apy = pool.get("apy", 0) or 0
            is_stable = pool.get("stablecoin", False)
            symbol = pool.get("symbol", "")
            project = pool.get("project", "").lower()
            
            # Check protocol filter FIRST
            if allowed_protocols:
                # partial match allowed e.g. "lido" matches "lido" or "lido-finance"
                if not any(ap in project for ap in allowed_protocols):
                    continue

            # Use get_pool_category for proper single/dual-sided classification
            category_info = get_pool_category(project, symbol)
            is_single_sided = category_info["is_single_sided"]
            
            # Pool type filter
            if pool_type == "single" and not is_single_sided:
                continue
            if pool_type == "dual" and is_single_sided:
                continue
            
            if tvl >= min_tvl and apy >= min_apy:
                # Stablecoin filter
                if not stablecoin_only or is_stable:
                    formatted = format_defillama_pool(pool, blur)
                    results["defillama"].append(formatted)

    
    # Process GeckoTerminal pools - skip for stablecoin_only (these are DEX LPs)
    if gecko_pools and not stablecoin_only:
        results["sources_used"].append("geckoterminal")
        for pool in gecko_pools:
            tvl = pool.get("tvl_usd", 0)
            dex = pool.get("dex", "").lower()

            # Protocol filter
            if allowed_protocols:
                 if not any(ap in dex for ap in allowed_protocols):
                     continue
            
            if tvl >= min_tvl:
                formatted = format_gecko_pool(pool, blur)
                results["geckoterminal"].append(formatted)
    
    # Sort each source by APY
    results["defillama"].sort(key=lambda x: x["apy"], reverse=True)
    results["geckoterminal"].sort(key=lambda x: x["volume_24h"] if "volume_24h" in x else x["apy"], reverse=True)
    
    # Combine - interleave sources for variety
    combined = []
    dl_idx, gt_idx = 0, 0
    
    # If using protocol filter, we likely want ALL results, not just a small limit
    # But keep limit if large to prevent overload
    effective_limit = limit if not allowed_protocols else max(limit, 500)

    while len(combined) < effective_limit:
        # Alternate between sources
        if dl_idx < len(results["defillama"]):
            combined.append(results["defillama"][dl_idx])
            dl_idx += 1
        if gt_idx < len(results["geckoterminal"]) and len(combined) < effective_limit:
            combined.append(results["geckoterminal"][gt_idx])
            gt_idx += 1
        
        # Break if no more pools
        if dl_idx >= len(results["defillama"]) and gt_idx >= len(results["geckoterminal"]):
            break
    
    results["combined"] = combined
    
    # Re-add chain info after processing
    results["chain"] = chain_config["name"]
    results["chain_icon"] = chain_config["icon"]
    
    return results


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    async def test():
        print("🔍 Testing Multi-Source Aggregator...\n")
        
        result = await get_aggregated_pools(
            chain="Base",
            min_tvl=500000,
            limit=10
        )
        
        print(f"Sources used: {result['sources_used']}")
        print(f"DefiLlama pools: {len(result['defillama'])}")
        print(f"GeckoTerminal pools: {len(result['geckoterminal'])}")
        print(f"Combined: {len(result['combined'])}")
        
        print("\n📊 Top 5 Combined:")
        for pool in result["combined"][:5]:
            print(f"  {pool['source_badge']} {pool['symbol']} | APY: {pool['apy']}% | TVL: {pool['tvl_formatted']} | Source: {pool['source_name']}")
    
    asyncio.run(test())
