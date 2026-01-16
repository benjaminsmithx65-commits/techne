"""
Techne Scout Agent - Yield Discovery
Skanuje wszystkie protokoły DeFi i znajduje najlepsze yield opportunities
"""

import asyncio
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Top DeFi Protocols by TVL (from DefiLlama research)
TOP_PROTOCOLS = {
    "tier1": [  # Najpopularniejsze - widoczne na górze
        {"name": "aave", "displayName": "Aave", "tvl": "32B", "chains": ["Ethereum", "Base", "Arbitrum", "Polygon", "Optimism"]},
        {"name": "lido", "displayName": "Lido", "tvl": "25B", "chains": ["Ethereum"]},
        {"name": "uniswap", "displayName": "Uniswap", "tvl": "2.1B", "chains": ["Ethereum", "Base", "Arbitrum", "Polygon", "Optimism"]},
        {"name": "curve", "displayName": "Curve", "tvl": "2.1B", "chains": ["Ethereum", "Base", "Arbitrum", "Polygon"]},
        {"name": "compound", "displayName": "Compound", "tvl": "1.6B", "chains": ["Ethereum", "Base", "Arbitrum", "Polygon"]},
        {"name": "aerodrome", "displayName": "Aerodrome", "tvl": "500M", "chains": ["Base"]},
    ],
    "tier2": [  # Drugorzędne - w slidebar
        {"name": "pendle", "displayName": "Pendle", "tvl": "3.7B", "chains": ["Ethereum", "Arbitrum"]},
        {"name": "morpho", "displayName": "Morpho", "tvl": "5.7B", "chains": ["Ethereum", "Base"]},
        {"name": "sparklend", "displayName": "SparkLend", "tvl": "3.2B", "chains": ["Ethereum"]},
        {"name": "kamino", "displayName": "Kamino", "tvl": "2.1B", "chains": ["Solana"]},
        {"name": "justlend", "displayName": "JustLend", "tvl": "3.7B", "chains": ["Tron"]},
        {"name": "maple", "displayName": "Maple", "tvl": "2.5B", "chains": ["Ethereum"]},
        {"name": "venus", "displayName": "Venus", "tvl": "1.5B", "chains": ["Binance"]},
        {"name": "raydium", "displayName": "Raydium", "tvl": "1.4B", "chains": ["Solana"]},
        {"name": "convex", "displayName": "Convex", "tvl": "923M", "chains": ["Ethereum"]},
    ],
    "tier3": [  # Nowe protokoły z potencjałem airdrop
        {"name": "midas", "displayName": "Midas", "tvl": "Unknown", "chains": ["Multi-Chain"], "airdrop_potential": "high"},
        {"name": "infinifi", "displayName": "InfiniFi", "tvl": "Unknown", "chains": ["Ethereum"], "airdrop_potential": "high"},
        {"name": "scroll", "displayName": "Scroll Pools", "tvl": "500M", "chains": ["Scroll"], "airdrop_potential": "high"},
        {"name": "linea", "displayName": "Linea Pools", "tvl": "600M", "chains": ["Linea"], "airdrop_potential": "medium"},
        {"name": "zksync", "displayName": "zkSync Pools", "tvl": "400M", "chains": ["zkSync Era"], "airdrop_potential": "medium"},
    ]
}

# Airdrop detection patterns
AIRDROP_INDICATORS = {
    "high": ["midas", "infinifi", "scroll", "linea", "pendle", "eigenlayer"],
    "medium": ["aerodrome", "kamino", "zksync", "starknet", "base"],
    "low": ["aave", "compound", "curve", "uniswap"]  # Already have tokens
}


class ScoutAgent:
    """
    Scout Agent - Yield Discovery
    Skanuje protokoły DeFi i znajduje najlepsze yield opportunities
    """
    
    def __init__(self):
        self.defillama_base = "https://yields.llama.fi"
        self.gecko_base = "https://api.geckoterminal.com/api/v2"
        self.last_scan = None
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        # APY history for 7-day validation
        self.apy_history = {}  # pool_id -> [(timestamp, apy), ...]
        self.apy_history_days = 7
        
    async def scan_all_protocols(self, chain: str = "Base", min_tvl: float = 100000) -> List[Dict]:
        """Skanuje wszystkie protokoły na danym chainie"""
        pools = []
        
        # 1. DefiLlama Yields
        try:
            llama_pools = await self._fetch_defillama_pools(chain, min_tvl)
            pools.extend(llama_pools)
        except Exception as e:
            print(f"DefiLlama error: {e}")
            
        # 2. GeckoTerminal (dla dodatkowych DEX pools)
        try:
            gecko_pools = await self._fetch_gecko_pools(chain, min_tvl)
            pools.extend(gecko_pools)
        except Exception as e:
            print(f"GeckoTerminal error: {e}")
            
        # 3. Enrich with airdrop potential
        pools = self._add_airdrop_potential(pools)
        
        # 4. Calculate risk scores (including IL)
        pools = self._calculate_risk_scores(pools)
        
        # 5. Add APY validation (history, spike detection)
        pools = self._validate_apy(pools)
        
        # 6. Sort by APY (descending)
        pools.sort(key=lambda x: x.get('apy', 0), reverse=True)
        
        self.last_scan = datetime.utcnow()
        return pools
    
    def _validate_apy(self, pools: List[Dict]) -> List[Dict]:
        """Validate APY with history tracking and spike detection"""
        now = datetime.utcnow()
        
        for pool in pools:
            pool_id = pool.get("id", pool.get("symbol"))
            current_apy = pool.get("apy", 0)
            
            # Initialize history for new pools
            if pool_id not in self.apy_history:
                self.apy_history[pool_id] = []
            
            # Add current APY to history
            self.apy_history[pool_id].append((now, current_apy))
            
            # Keep only last 7 days of history
            cutoff = now - timedelta(days=self.apy_history_days)
            self.apy_history[pool_id] = [
                (ts, apy) for ts, apy in self.apy_history[pool_id] 
                if ts > cutoff
            ]
            
            history = self.apy_history[pool_id]
            
            if len(history) >= 3:
                # Calculate 7-day average
                avg_apy = sum(apy for _, apy in history) / len(history)
                pool["apy_7d_avg"] = round(avg_apy, 2)
                
                # Detect spikes (current > 2x average)
                if avg_apy > 0 and current_apy > avg_apy * 2:
                    pool["apy_spike"] = True
                    pool["apy_warning"] = f"⚠️ APY spike: {current_apy:.1f}% vs {avg_apy:.1f}% avg"
                    # Add to risk reasons
                    if "risk_reasons" in pool:
                        pool["risk_reasons"].append(pool["apy_warning"])
                else:
                    pool["apy_spike"] = False
            else:
                pool["apy_7d_avg"] = current_apy
                pool["apy_spike"] = False
                pool["apy_warning"] = "Insufficient history"
        
        return pools
    
    def _get_whitelisted_projects(self) -> set:
        """Get set of all whitelisted project slugs/names"""
        allowed = set()
        for tier in ["tier1", "tier2", "tier3"]:
            for p in TOP_PROTOCOLS.get(tier, []):
                allowed.add(p["name"].lower())
                # Add potential variations/overrides if needed
        return allowed

    async def _fetch_defillama_pools(self, chain: str, min_tvl: float) -> List[Dict]:
        """Fetch pools from DefiLlama"""
        allowed_projects = self._get_whitelisted_projects()
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.defillama_base}/pools")
            if response.status_code != 200:
                return []
            
            data = response.json()
            pools = data.get('data', [])
            
            # Filter by chain and TVL
            filtered = []
            for pool in pools:
                if pool.get('chain', '').lower() != chain.lower():
                    continue
                if pool.get('tvlUsd', 0) < min_tvl:
                    continue
                
                # STRICT WHITELIST CHECK
                project_slug = (pool.get('project') or '').lower()
                # Check for partial matches or exact matches in our allowed list
                # e.g. "aave-v3" should match "aave"
                is_whitelisted = False
                for allowed in allowed_projects:
                    if allowed in project_slug:
                        is_whitelisted = True
                        break
                
                if not is_whitelisted:
                    continue
                    
                filtered.append({
                    "id": pool.get('pool'),
                    "chain": pool.get('chain'),
                    "project": pool.get('project'),
                    "symbol": pool.get('symbol'),
                    "apy": round(pool.get('apy', 0), 2),
                    "apyBase": round(pool.get('apyBase', 0) or 0, 2),
                    "apyReward": round(pool.get('apyReward', 0) or 0, 2),
                    "tvl": pool.get('tvlUsd', 0),
                    "tvl_formatted": self._format_tvl(pool.get('tvlUsd', 0)),
                    "stablecoin": pool.get('stablecoin', False),
                    "exposure": pool.get('exposure'),
                    "pool_link": self._generate_pool_link(pool.get('project'), pool.get('pool')),
                    "source": "defillama",
                    "source_name": "DefiLlama",
                    "source_badge": "📊",
                })
                
            return filtered[:50]  # Limit to top 50
    
    async def _fetch_gecko_pools(self, chain: str, min_tvl: float) -> List[Dict]:
        """Fetch pools from GeckoTerminal"""
        allowed_projects = self._get_whitelisted_projects()
        chain_map = {
            "Base": "base",
            "Ethereum": "eth",
            "Arbitrum": "arbitrum",
            "Polygon": "polygon_pos",
            "Optimism": "optimism"
        }
        
        gecko_chain = chain_map.get(chain, chain.lower())
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.gecko_base}/networks/{gecko_chain}/trending_pools",
                    headers={"Accept": "application/json"}
                )
            except Exception:
                return []

            if response.status_code != 200:
                return []
            
            data = response.json()
            pools = data.get('data', [])
            
            filtered = []
            for pool in pools:
                attrs = pool.get('attributes', {})
                reserve_usd = float(attrs.get('reserve_in_usd', '0') or '0')
                
                if reserve_usd < min_tvl:
                    continue

                # STRICT WHITELIST CHECK
                name = (attrs.get('name', '')).lower()
                is_whitelisted = False
                for allowed in allowed_projects:
                    if allowed in name:
                        is_whitelisted = True
                        break
                
                if not is_whitelisted:
                    continue
                    
                # Estimate APY from volume (simplified)
                volume_24h = float(attrs.get('volume_usd', {}).get('h24', '0') or '0')
                fee_rate = 0.003  # Assume 0.3% fee
                estimated_apy = (volume_24h * fee_rate * 365 / max(reserve_usd, 1)) * 100
                
                filtered.append({
                    "id": pool.get('id'),
                    "chain": chain,
                    "project": attrs.get('name', '').split('/')[0] if '/' in attrs.get('name', '') else 'Unknown',
                    "symbol": attrs.get('name', ''),
                    "apy": round(estimated_apy, 2),
                    "tvl": reserve_usd,
                    "tvl_formatted": self._format_tvl(reserve_usd),
                    "stablecoin": False,
                    "pool_link": attrs.get('pool_url'),
                    "source": "geckoterminal",
                    "source_name": "GeckoTerminal",
                    "source_badge": "🦎",
                })
                
            return filtered[:20]  # Limit
    
    def _add_airdrop_potential(self, pools: List[Dict]) -> List[Dict]:
        """Add airdrop potential score to pools"""
        for pool in pools:
            project = (pool.get('project') or '').lower()
            
            if any(p in project for p in AIRDROP_INDICATORS["high"]):
                pool["airdrop_potential"] = "high"
                pool["airdrop_badge"] = "🎁🎁"
            elif any(p in project for p in AIRDROP_INDICATORS["medium"]):
                pool["airdrop_potential"] = "medium"
                pool["airdrop_badge"] = "🎁"
            else:
                pool["airdrop_potential"] = "low"
                pool["airdrop_badge"] = ""
                
        return pools
    
    def _calculate_risk_scores(self, pools: List[Dict]) -> List[Dict]:
        """Calculate risk score for each pool including IL risk"""
        # Volatility indicators for common tokens (higher = more volatile)
        VOLATILITY = {
            "btc": 0.3, "wbtc": 0.3, "eth": 0.4, "weth": 0.4,
            "usdc": 0.01, "usdt": 0.01, "dai": 0.02, "frax": 0.02,
            "aero": 0.8, "crv": 0.6, "uni": 0.5, "aave": 0.5,
            "link": 0.5, "op": 0.6, "arb": 0.6
        }
        
        for pool in pools:
            risk_score = "Medium"
            risk_reasons = []
            
            tvl = pool.get('tvl', 0)
            apy = pool.get('apy', 0)
            stablecoin = pool.get('stablecoin', False)
            symbol = (pool.get('symbol') or '').lower()
            
            # Detect if LP pool
            is_lp = any(sep in symbol for sep in ["-", "/", " / "])
            
            # TVL-based risk
            if tvl >= 10_000_000:
                risk_reasons.append("High TVL (>$10M)")
            elif tvl >= 1_000_000:
                risk_reasons.append("Medium TVL ($1M-$10M)")
            else:
                risk_reasons.append("Low TVL (<$1M)")
                risk_score = "High"
            
            # APY-based risk
            if apy > 100:
                risk_reasons.append("Very high APY (>100%) ⚠️")
                risk_score = "High"
            elif apy > 50:
                risk_reasons.append("High APY (50-100%)")
            elif apy > 20:
                risk_reasons.append("Moderate APY (20-50%)")
            else:
                risk_reasons.append("Conservative APY (<20%)")
                if risk_score != "High":
                    risk_score = "Low"
            
            # IMPERMANENT LOSS RISK for LP pools
            if is_lp:
                # Parse token pair
                tokens = symbol.replace(" / ", "/").replace("-", "/").split("/")
                if len(tokens) >= 2:
                    t1 = tokens[0].strip().lower()
                    t2 = tokens[1].strip().lower()
                    
                    v1 = VOLATILITY.get(t1, 0.5)
                    v2 = VOLATILITY.get(t2, 0.5)
                    
                    # IL risk = difference in volatility
                    il_risk = abs(v1 - v2)
                    
                    if v1 < 0.05 and v2 < 0.05:
                        # Stablecoin pair - minimal IL
                        pool["il_risk"] = "Minimal"
                        risk_reasons.append("Stablecoin pair - minimal IL")
                    elif il_risk < 0.2:
                        pool["il_risk"] = "Low"
                        risk_reasons.append(f"Low IL risk ({t1}/{t2})")
                    elif il_risk < 0.5:
                        pool["il_risk"] = "Medium"
                        risk_reasons.append(f"Medium IL risk ({t1}/{t2})")
                        if risk_score == "Low":
                            risk_score = "Medium"
                    else:
                        pool["il_risk"] = "High"
                        risk_reasons.append(f"⚠️ High IL risk ({t1}/{t2})")
                        risk_score = "High"
            else:
                pool["il_risk"] = "None"
            
            # Stablecoin bonus
            if stablecoin:
                risk_reasons.append("Stablecoin pair")
                if risk_score == "Medium":
                    risk_score = "Low"
            
            # Project reputation
            project = (pool.get('project') or '').lower()
            trusted = ['aave', 'compound', 'curve', 'uniswap', 'lido']
            if any(t in project for t in trusted):
                risk_reasons.append("Trusted protocol ✓")
                if risk_score == "High":
                    risk_score = "Medium"
            
            pool["risk_score"] = risk_score
            pool["risk_reasons"] = risk_reasons
            
        return pools
    
    def _format_tvl(self, tvl: float) -> str:
        """Format TVL for display"""
        if tvl >= 1_000_000_000:
            return f"${tvl/1_000_000_000:.1f}B"
        elif tvl >= 1_000_000:
            return f"${tvl/1_000_000:.1f}M"
        elif tvl >= 1_000:
            return f"${tvl/1_000:.1f}K"
        return f"${tvl:.0f}"
    
    def _generate_pool_link(self, project: str, pool_id: str) -> Optional[str]:
        """Generate direct link to pool"""
        links = {
            "aave-v3": f"https://app.aave.com/",
            "compound-v3": "https://app.compound.finance/",
            "curve-dex": "https://curve.fi/",
            "uniswap-v3": "https://app.uniswap.org/",
            "aerodrome-v2": f"https://aerodrome.finance/deposit",
            "aerodrome-slipstream": f"https://aerodrome.finance/deposit",
        }
        return links.get(project, None)
    
    def get_protocol_list(self) -> Dict:
        """Return organized protocol list for frontend"""
        return TOP_PROTOCOLS
    
    def get_recommended_protocols(self, chain: str = "Base") -> List[Dict]:
        """Get recommended protocols for a chain"""
        all_protocols = []
        for tier in ["tier1", "tier2", "tier3"]:
            for proto in TOP_PROTOCOLS[tier]:
                if chain in proto.get("chains", []) or "Multi-Chain" in proto.get("chains", []):
                    all_protocols.append({
                        **proto,
                        "tier": tier,
                        "airdrop_potential": proto.get("airdrop_potential", "low")
                    })
        return all_protocols


# Singleton instance
scout_agent = ScoutAgent()


async def get_scout_pools(
    chain: str = "Base",
    min_tvl: float = 100000,
    max_tvl: float = 100000000,
    min_apy: float = 5,
    max_apy: float = 200,
    stablecoin_only: bool = False,
    protocols: List[str] = None,
    max_risk: str = "all"
) -> Dict:
    """
    Main function to get pools from Scout Agent
    Returns filtered and scored pools
    """
    # Get all pools
    pools = await scout_agent.scan_all_protocols(chain, min_tvl)
    
    # Apply filters
    filtered = []
    for pool in pools:
        # TVL filter
        if pool.get('tvl', 0) > max_tvl:
            continue
            
        # APY filter
        if pool.get('apy', 0) < min_apy or pool.get('apy', 0) > max_apy:
            continue
            
        # Stablecoin filter
        if stablecoin_only and not pool.get('stablecoin', False):
            continue
            
        # Protocol filter
        if protocols and len(protocols) > 0:
            project_lower = (pool.get('project') or '').lower()
            if not any(p.lower() in project_lower for p in protocols):
                continue
                
        # Risk filter
        if max_risk == "Low" and pool.get('risk_score') != "Low":
            continue
        if max_risk == "Medium" and pool.get('risk_score') == "High":
            continue
            
        filtered.append(pool)
    
    return {
        "pools": filtered,
        "total": len(filtered),
        "chain": chain,
        "scan_time": scout_agent.last_scan.isoformat() if scout_agent.last_scan else None,
        "protocols": scout_agent.get_protocol_list()
    }
