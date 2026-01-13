"""
Smart Pool Router - The "Brain" of Pool Analysis
Intelligently routes to correct adapter based on on-chain factory detection.

Tiered Adapter System:
- Tier 1 (Premium): AerodromeOnChain - Full APY, Gauge, Epoch data
- Tier 2 (High): UniswapV3Adapter - Fee APY, Tick data
- Tier 3 (Basic): UniversalScanner - TVL & Tokens only
"""
import logging
import re
from typing import Optional, Dict, Any, Tuple, List
from web3 import Web3
from enum import Enum

logger = logging.getLogger("SmartRouter")

# Import security checker (GoPlus RugCheck)
try:
    from api.security_module import security_checker
    SECURITY_CHECKER_AVAILABLE = True
except ImportError:
    SECURITY_CHECKER_AVAILABLE = False
    logger.warning("Security checker not available")

# Import holder analysis (Moralis/Covalent for whale concentration)
try:
    from data_sources.holder_analysis import holder_analyzer
    HOLDER_ANALYSIS_AVAILABLE = True
except ImportError:
    HOLDER_ANALYSIS_AVAILABLE = False
    logger.warning("Holder analysis not available")

# Import liquidity lock checker (Team Finance/Unicrypt)
try:
    from data_sources.liquidity_lock import liquidity_lock_checker
    LIQUIDITY_LOCK_AVAILABLE = True
except ImportError:
    LIQUIDITY_LOCK_AVAILABLE = False
    logger.warning("Liquidity lock checker not available")


class Protocol(Enum):
    """Detected protocol based on factory address"""
    AERODROME_V2 = "aerodrome_v2"
    AERODROME_SLIPSTREAM = "aerodrome_slipstream"
    UNISWAP_V3 = "uniswap_v3"
    ALIENBASE = "alienbase"
    BASESWAP = "baseswap"
    SUSHISWAP = "sushiswap"
    VELODROME = "velodrome"
    # Single-sided vaults
    BEEFY = "beefy"
    YEARN = "yearn"
    # Lending protocols
    MOONWELL = "moonwell"
    COMPOUND = "compound"
    AAVE = "aave"
    UNKNOWN = "unknown"


class DataQuality(Enum):
    """Response data quality tier"""
    PREMIUM = "premium"   # Full APY, Gauge, Epoch
    HIGH = "high"         # Fee APY, Tick data
    BASIC = "basic"       # TVL & Tokens only


# =============================================================================
# KNOWN FACTORIES BY CHAIN
# =============================================================================

KNOWN_FACTORIES = {
    "base": {
        # Aerodrome
        "0x420dd381b31aef6683db6b902084cb0ffece40da": Protocol.AERODROME_V2,
        "0x5e7bb104d84c7cb9b682aac2f3d509f5f406809a": Protocol.AERODROME_SLIPSTREAM,
        "0xade65c38cd4849adba595a4323a8c7ddfe89716a": Protocol.AERODROME_SLIPSTREAM,  # Slipstream Stable
        # Uniswap
        "0x33128a8fc17869897dce68ed026d694621f6fdfd": Protocol.UNISWAP_V3,
        # Other DEXes
        "0x3e84d913803b02a4a7f027165e8ca42c14c0fde7": Protocol.ALIENBASE,
        "0xfda619b6d20975be80a10332cd39b9a4b0faaa27": Protocol.BASESWAP,
        "0x71524b4f93c58fcbf659783284e38825f0622859": Protocol.SUSHISWAP,
    },
    "optimism": {
        # Velodrome
        "0x25cbddb98b35ab1ff77413456b31ec81a6b6b746": Protocol.VELODROME,
    },
    "ethereum": {
        # Uniswap V3
        "0x1f98431c8ad98523631ae4a59f267346ea31f984": Protocol.UNISWAP_V3,
    }
}

# Protocol -> Adapter mapping
PROTOCOL_ADAPTERS = {
    Protocol.AERODROME_V2: "aerodrome",
    Protocol.AERODROME_SLIPSTREAM: "aerodrome",
    Protocol.ALIENBASE: "aerodrome",  # Uses same gauge system
    Protocol.VELODROME: "aerodrome",  # Velodrome is Aerodrome on Optimism
    Protocol.UNISWAP_V3: "uniswap_v3",
    Protocol.BASESWAP: "universal",
    Protocol.SUSHISWAP: "universal",
    Protocol.UNKNOWN: "universal",
}

# Factory ABI for detection
FACTORY_ABI = [{
    "constant": True,
    "inputs": [],
    "name": "factory",
    "outputs": [{"type": "address"}],
    "type": "function"
}]

# RPC endpoints
RPC_ENDPOINTS = {
    "base": "https://mainnet.base.org",
    "ethereum": "https://eth.llamarpc.com",
    "optimism": "https://mainnet.optimism.io",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
}


class SmartRouter:
    """
    Intelligent routing system that detects protocol via factory() call
    and routes to the appropriate adapter for maximum data quality.
    """
    
    def __init__(self):
        self._web3_cache: Dict[str, Web3] = {}
        logger.info("🧠 SmartRouter initialized")
    
    def _get_web3(self, chain: str) -> Optional[Web3]:
        """Get Web3 instance with caching"""
        chain = chain.lower()
        if chain in self._web3_cache:
            return self._web3_cache[chain]
        
        rpc = RPC_ENDPOINTS.get(chain)
        if not rpc:
            return None
        
        try:
            w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                self._web3_cache[chain] = w3
                return w3
        except Exception as e:
            logger.debug(f"RPC connection failed for {chain}: {e}")
        
        return None
    
    # =========================================================================
    # INPUT PARSING
    # =========================================================================
    
    def parse_input(self, input_str: str) -> Tuple[Optional[str], Optional[str], Optional[Protocol]]:
        """
        Parse user input - could be address, URL, or vault ID.
        Returns (pool_address_or_vault_id, chain, protocol_hint)
        """
        input_str = input_str.strip()
        
        # Check if it's a URL
        if input_str.startswith("http"):
            return self._parse_url(input_str)
        
        # Check if it's an address
        if input_str.startswith("0x") and len(input_str) == 42:
            return input_str.lower(), None, None  # Chain and protocol unknown
        
        return None, None, None
    
    def _parse_url(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[Protocol]]:
        """
        Parse pool URL to extract address, chain, and protocol hint.
        Returns (address_or_vault_id, chain, protocol_hint)
        """
        url_lower = url.lower()
        
        # =================================================================
        # SINGLE-SIDED VAULTS
        # =================================================================
        
        # Beefy: app.beefy.com/vault/{vault-id}
        if "beefy.com/vault/" in url_lower or "beefy.finance/vault/" in url_lower:
            # Extract vault ID from URL
            match = re.search(r'/vault/([\w\-]+)', url_lower)
            if match:
                vault_id = match.group(1)
                # Determine chain from vault ID prefix (e.g., base-aerodrome-usdc-weth)
                chain = "base"  # Default
                if vault_id.startswith("base-"):
                    chain = "base"
                elif vault_id.startswith("op-") or vault_id.startswith("optimism-"):
                    chain = "optimism"
                elif vault_id.startswith("arb-") or vault_id.startswith("arbitrum-"):
                    chain = "arbitrum"
                elif vault_id.startswith("eth-") or vault_id.startswith("ethereum-"):
                    chain = "ethereum"
                elif vault_id.startswith("bsc-"):
                    chain = "bsc"
                logger.info(f"🐄 Beefy vault detected: {vault_id} on {chain}")
                return vault_id, chain, Protocol.BEEFY
        
        # Moonwell: moonwell.fi/markets/{chain}/{token}
        if "moonwell.fi" in url_lower:
            match = re.search(r'/markets?/([\w]+)/([\w]+)', url_lower)
            if match:
                chain = match.group(1).lower()
                token = match.group(2).upper()
                logger.info(f"🌙 Moonwell market detected: {token} on {chain}")
                return token, chain, Protocol.MOONWELL
            # Also handle direct mToken address
            addr_match = re.search(r'0x[a-f0-9]{40}', url_lower)
            if addr_match:
                return addr_match.group(0), "base", Protocol.MOONWELL
        
        # =================================================================
        # LP POOLS
        # =================================================================
        
        # Aerodrome: aerodrome.finance/pools/0x...
        if "aerodrome.finance" in url_lower:
            match = re.search(r'0x[a-f0-9]{40}', url_lower)
            return (match.group(0), "base", None) if match else (None, None, None)
        
        # Uniswap: app.uniswap.org/...base/pools/0x...
        if "uniswap.org" in url_lower:
            match = re.search(r'0x[a-f0-9]{40}', url_lower)
            chain = "base" if "/base/" in url_lower else "ethereum"
            return (match.group(0), chain, None) if match else (None, None, None)
        
        # GeckoTerminal: geckoterminal.com/base/pools/0x...
        if "geckoterminal.com" in url_lower:
            match = re.search(r'/(base|eth|arbitrum|optimism)/pools/(0x[a-f0-9]{40})', url_lower)
            if match:
                chain_map = {"eth": "ethereum"}
                chain = chain_map.get(match.group(1), match.group(1))
                return match.group(2), chain, None
        
        # Fallback: try to find address
        match = re.search(r'0x[a-f0-9]{40}', url_lower)
        return (match.group(0), None, None) if match else (None, None, None)
    
    # =========================================================================
    # PROTOCOL DETECTION (The "Factory Check")
    # =========================================================================
    
    async def detect_protocol(self, pool_address: str, chain: str = "base") -> Protocol:
        """
        Detect protocol by calling pool.factory() and matching against known factories.
        This is the core of the "factory check" strategy.
        """
        w3 = self._get_web3(chain)
        if not w3:
            logger.warning(f"No RPC for chain {chain}")
            return Protocol.UNKNOWN
        
        try:
            pool_address = Web3.to_checksum_address(pool_address)
            pool = w3.eth.contract(address=pool_address, abi=FACTORY_ABI)
            
            # Call factory()
            factory_address = pool.functions.factory().call()
            factory_lower = factory_address.lower()
            
            # Look up in known factories
            chain_factories = KNOWN_FACTORIES.get(chain.lower(), {})
            protocol = chain_factories.get(factory_lower, Protocol.UNKNOWN)
            
            if protocol != Protocol.UNKNOWN:
                logger.info(f"🔍 Detected {protocol.value} via factory {factory_lower[:10]}...")
            else:
                logger.info(f"🔍 Unknown factory: {factory_lower}")
            
            return protocol
            
        except Exception as e:
            logger.debug(f"Factory detection failed: {e}")
            return Protocol.UNKNOWN
    
    # =========================================================================
    # SMART ROUTING (The "Brain")
    # =========================================================================
    
    async def smart_route_pool_check(
        self, 
        input_str: str, 
        chain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Intelligently route to correct adapter based on factory detection.
        
        Args:
            input_str: Pool address, URL, or vault ID
            chain: Optional chain hint (will be auto-detected from URL if possible)
        
        Returns:
            Unified pool data with quality tier indicator
        """
        # Step 1: Parse input (now returns protocol hint for vaults)
        parsed_address, parsed_chain, protocol_hint = self.parse_input(input_str)
        
        if not parsed_address:
            return {
                "success": False,
                "error": "Invalid input - could not parse pool address or vault ID",
                "input": input_str
            }
        
        chain = chain or parsed_chain or "base"
        
        # Step 2: If we have a protocol hint from URL parsing, use it directly
        if protocol_hint == Protocol.BEEFY:
            logger.info(f"🐄 SmartRouter routing to Beefy: {parsed_address}")
            return await self._route_beefy(parsed_address, chain)
        
        if protocol_hint == Protocol.MOONWELL:
            logger.info(f"🌙 SmartRouter routing to Moonwell: {parsed_address}")
            return await self._route_moonwell(parsed_address, chain)
        
        if protocol_hint == Protocol.YEARN:
            # TODO: Implement Yearn routing
            return {
                "success": False,
                "error": "Yearn vaults not yet supported",
                "input": input_str
            }
        
        # Step 3: For pool addresses, detect protocol via factory
        logger.info(f"🧠 SmartRouter processing: {parsed_address[:10]}... on {chain}")
        protocol = await self.detect_protocol(parsed_address, chain)
        adapter_type = PROTOCOL_ADAPTERS.get(protocol, "universal")
        
        # Step 4: Route to appropriate adapter
        if adapter_type == "aerodrome":
            return await self._route_aerodrome(parsed_address, chain, protocol)
        elif adapter_type == "uniswap_v3":
            return await self._route_uniswap_v3(parsed_address, chain)
        else:
            return await self._route_universal(parsed_address, chain, protocol)
    
    async def _route_aerodrome(
        self, 
        pool_address: str, 
        chain: str,
        protocol: Protocol
    ) -> Dict[str, Any]:
        """
        Tier 1 (Premium): Full Aerodrome analysis.
        OPTIMIZED: Use GeckoTerminal first (no RPC), then minimal RPC for APY only.
        - GeckoTerminal: TVL, symbols, volume (API call, fast)
        - On-chain: Only gauge + rewardRate (3-5 RPC calls vs ~18 before)
        """
        pool_data = None
        source = "unknown"
        
        # STEP 1: ALWAYS try GeckoTerminal first (no RPC calls, fast)
        try:
            from data_sources.geckoterminal import gecko_client
            gecko_data = await gecko_client.get_pool_by_address(chain, pool_address)
            
            if gecko_data and gecko_data.get("tvl", 0) > 0:
                pool_data = gecko_data
                source = "geckoterminal+factory_detected"
                logger.info(f"Aerodrome pool via GeckoTerminal: TVL=${gecko_data.get('tvl', 0):,.0f}")
        except Exception as e:
            logger.warning(f"GeckoTerminal fetch failed: {e}")
        
        # If we have data, enrich and return
        if pool_data:
            # Enrich with GeckoTerminal market data (volume, TVL trend)
            pool_data = await self._enrich_with_gecko_data(pool_data, pool_address, chain)
            
            # =========================================================
            # APY CALCULATION - Using APY Capability Response Contract
            # Zero heuristics - explicit branching on apy_status
            # =========================================================
            current_apy = pool_data.get("apy", 0)
            
            if not current_apy or current_apy == 0:
                logger.info(f"Fetching APY from Aerodrome gauge for {pool_address[:10]}...")
                try:
                    from data_sources.aerodrome import aerodrome_client
                    
                    # Pass protocol hint to avoid double detection
                    pool_type_hint = "cl" if protocol == Protocol.AERODROME_SLIPSTREAM else "v2"
                    apy_data = await aerodrome_client.get_real_time_apy(pool_address, pool_type_hint)
                    
                    apy_status = apy_data.get("apy_status", "unknown")
                    reason = apy_data.get("reason", "UNKNOWN")
                    
                    # Always propagate pool_type and has_gauge for frontend
                    pool_data["pool_type"] = apy_data.get("pool_type", "unknown")
                    pool_data["has_gauge"] = apy_data.get("has_gauge", False)
                    
                    logger.info(f"APY Response: status={apy_status}, reason={reason}, pool_type={pool_data['pool_type']}")
                    
                    # CONTRACT-BASED BRANCHING (no heuristics)
                    if apy_status == "ok":
                        # V2 pool - APY already calculated on-chain
                        pool_data["apy"] = apy_data.get("apy", 0)
                        pool_data["apy_reward"] = apy_data.get("apy_reward", 0)
                        pool_data["apy_source"] = "aerodrome_v2_onchain"
                        pool_data["gauge_address"] = apy_data.get("gauge_address")
                        pool_data["epoch_remaining"] = apy_data.get("epoch_end")
                        pool_data["apy_status"] = "ok"
                        logger.info(f"✅ V2 APY from on-chain: {pool_data['apy']:.2f}%")
                        
                    elif apy_status == "requires_external_tvl" or apy_status == "requires_staked_tvl_conversion":
                        # Pool needs TVL from external source (GeckoTerminal)
                        total_tvl = pool_data.get("tvl", 0) or pool_data.get("tvlUsd", 0)
                        yearly_rewards = apy_data.get("yearly_rewards_usd", 0)
                        pool_type = apy_data.get("pool_type", "unknown")
                        
                        if total_tvl > 0 and yearly_rewards > 0:
                            # V2 pools: Simple APR = yearly_rewards / TVL
                            if pool_type == "v2":
                                # For V2, TVL from GeckoTerminal represents all liquidity
                                v2_apr = (yearly_rewards / total_tvl) * 100
                                pool_data["apy"] = v2_apr
                                pool_data["apy_reward"] = v2_apr
                                pool_data["apy_source"] = "aerodrome_v2_tvl_fallback"
                                pool_data["gauge_address"] = apy_data.get("gauge_address")
                                pool_data["yearly_emissions_usd"] = yearly_rewards
                                pool_data["epoch_remaining"] = apy_data.get("epoch_end")
                                pool_data["apy_status"] = "ok"
                                logger.info(f"✅ V2 APR (TVL fallback): {v2_apr:.2f}% (${yearly_rewards:,.0f} / ${total_tvl:,.0f})")
                            
                            # CL pools: Use staked ratio for accurate staker APR
                            else:
                                staked_ratio = apy_data.get("staked_ratio", 1.0)
                                staked_tvl = total_tvl * staked_ratio
                                
                                # Realistic Staker APR = rewards / staked TVL
                                staker_apr = (yearly_rewards / staked_tvl) * 100 if staked_tvl > 0 else 0
                                
                                # Optimal Range APR (Aerodrome-style) - FOR REFERENCE ONLY
                                OPTIMAL_RANGE_FACTOR = 0.20
                                optimal_tvl = total_tvl * OPTIMAL_RANGE_FACTOR
                                optimal_apr = (yearly_rewards / optimal_tvl) * 100 if optimal_tvl > 0 else 0
                                
                                pool_apr = (yearly_rewards / total_tvl) * 100
                                
                                # Use REALISTIC staker APR as primary
                                pool_data["apy"] = staker_apr
                                pool_data["apy_reward"] = staker_apr
                                pool_data["apy_optimal"] = optimal_apr
                                pool_data["apy_pool_wide"] = pool_apr
                                pool_data["apy_source"] = "aerodrome_cl_staker_apr"
                                pool_data["gauge_address"] = apy_data.get("gauge_address")
                                pool_data["yearly_emissions_usd"] = yearly_rewards
                                pool_data["epoch_remaining"] = apy_data.get("epoch_end")
                                pool_data["staked_ratio"] = staked_ratio
                                pool_data["staked_tvl"] = staked_tvl
                                pool_data["apy_status"] = "ok"
                                logger.info(f"✅ CL APR: staker={staker_apr:.2f}%, optimal={optimal_apr:.2f}% (${yearly_rewards:,.0f})")
                        else:
                            pool_data["apy_status"] = "unavailable"
                            pool_data["apy_reason"] = f"TVL_ZERO (tvl={total_tvl}, rewards={yearly_rewards})"
                            logger.warning(f"APY unavailable: TVL=${total_tvl:,.0f}, rewards=${yearly_rewards:,.0f}")
                    
                    elif apy_status == "unsupported":
                        # Pool type not supported for APY
                        pool_data["apy_status"] = "unsupported"
                        pool_data["apy_reason"] = reason
                        logger.info(f"APY unsupported: {reason}")
                        
                    elif apy_status == "error":
                        # Explicit error - bubble it up
                        pool_data["apy_status"] = "error"
                        pool_data["apy_reason"] = reason
                        logger.warning(f"APY error: {reason}")
                        
                    else:
                        # Unknown status - defensive
                        pool_data["apy_status"] = "unknown"
                        pool_data["apy_reason"] = f"UNEXPECTED_STATUS: {apy_status}"
                        logger.warning(f"Unexpected APY status: {apy_status}")
                        
                except Exception as e:
                    pool_data["apy_status"] = "error"
                    pool_data["apy_reason"] = f"EXCEPTION: {str(e)}"
                    logger.warning(f"Aerodrome APY call failed: {e}")
            
            # =================================================================
            # GOPLUS SECURITY CHECK (RugCheck)
            # =================================================================
            security_result = {"status": "skipped", "tokens": {}}
            if SECURITY_CHECKER_AVAILABLE:
                try:
                    # Extract token addresses - first try from pool_data
                    token0 = pool_data.get("token0")
                    token1 = pool_data.get("token1")
                    
                    # If no token addresses, fetch from RPC (pool.token0(), pool.token1())
                    if not token0 or not token1:
                        try:
                            from data_sources.onchain import onchain_client
                            logger.info(f"Fetching token addresses from RPC for {pool_address[:10]}...")
                            
                            rpc_data = await onchain_client.get_lp_reserves(chain, pool_address)
                            if rpc_data:
                                token0 = rpc_data.get("token0")
                                token1 = rpc_data.get("token1")
                                # Also save symbols if we got them
                                pool_data["token0"] = token0
                                pool_data["token1"] = token1
                                pool_data["symbol0"] = rpc_data.get("symbol0", "")
                                pool_data["symbol1"] = rpc_data.get("symbol1", "")
                                logger.info(f"Got tokens from RPC: {rpc_data.get('symbol0')}/{rpc_data.get('symbol1')}")
                        except Exception as e:
                            logger.debug(f"RPC token fetch failed: {e}")
                    
                    tokens_to_check = [t for t in [token0, token1] if t and t.startswith("0x")]
                    
                    if tokens_to_check:
                        security_result = await security_checker.check_security(tokens_to_check, chain)
                        
                        # Check for critical issues (honeypot)
                        summary = security_result.get("summary", {})
                        if summary.get("has_critical"):
                            pool_data["security_status"] = "critical"
                            pool_data["is_honeypot"] = True
                            logger.warning(f"HONEYPOT DETECTED: {pool_address}")
                        elif summary.get("total_penalty", 0) > 40:
                            pool_data["security_status"] = "high_risk"
                        elif summary.get("total_penalty", 0) > 15:
                            pool_data["security_status"] = "medium_risk"
                        else:
                            pool_data["security_status"] = "safe"
                        
                        pool_data["security_penalty"] = summary.get("total_penalty", 0)
                        pool_data["security_risks"] = summary.get("all_risks", [])
                        
                except Exception as e:
                    logger.warning(f"Security check failed: {e}")
                    security_result = {"status": "error", "error": str(e), "tokens": {}}
            
            pool_data["security_result"] = security_result
            
            # =================================================================
            # COMPREHENSIVE RISK ANALYSIS (IL, Volatility, Pool Age, Whale)
            # =================================================================
            if SECURITY_CHECKER_AVAILABLE:
                try:
                    # Get peg status for stablecoins
                    peg_status = await security_checker.check_stablecoin_peg(pool_data, chain)
                    pool_data["peg_status"] = peg_status
                    
                    # Determine audit status from protocol
                    audit_status = self._get_audit_status(pool_data, protocol)
                    pool_data["audit_status"] = audit_status
                    
                    # =========================================================
                    # LIQUIDITY LOCK CHECK (Team Finance / Unicrypt)
                    # =========================================================
                    liquidity_lock = {"has_lock": False, "source": "not_checked"}
                    if LIQUIDITY_LOCK_AVAILABLE:
                        try:
                            liquidity_lock = await liquidity_lock_checker.check_lp_lock(pool_address, chain)
                            logger.info(f"LP Lock: {liquidity_lock.get('has_lock')} ({liquidity_lock.get('source')})")
                        except Exception as e:
                            logger.debug(f"LP lock check failed: {e}")
                    pool_data["liquidity_lock"] = liquidity_lock
                    
                    # =========================================================
                    # WHALE CONCENTRATION ANALYSIS (Moralis API)
                    # =========================================================
                    whale_analysis = {"source": "not_available"}
                    if HOLDER_ANALYSIS_AVAILABLE:
                        try:
                            # Analyze LP token holders (the pool address IS the LP token)
                            lp_analysis = await holder_analyzer.get_holder_analysis(pool_address, chain)
                            if lp_analysis.get("source") != "error":
                                whale_analysis = {
                                    "lp_token": lp_analysis,
                                    "source": lp_analysis.get("source", "moralis")
                                }
                                logger.info(f"Whale analysis: top10={lp_analysis.get('top_10_percent', 'N/A')}% ({lp_analysis.get('source')})")
                        except Exception as e:
                            logger.debug(f"Whale analysis failed: {e}")
                    pool_data["whale_analysis"] = whale_analysis
                    
                    # Calculate full risk score (includes IL, volatility, age, audit, whale)
                    risk_analysis = security_checker.calculate_risk_score(
                        pool_data, 
                        security_result, 
                        peg_status,
                        pool_data.get("symbol_warnings"),
                        audit_status=audit_status,
                        liquidity_lock=liquidity_lock,
                        whale_analysis=whale_analysis
                    )
                    
                    # Add all risk data to pool
                    pool_data["risk_score"] = risk_analysis.get("risk_score")
                    pool_data["risk_level"] = risk_analysis.get("risk_level")
                    pool_data["risk_reasons"] = risk_analysis.get("risk_reasons", [])
                    pool_data["risk_breakdown"] = risk_analysis.get("risk_breakdown", {})
                    pool_data["il_analysis"] = risk_analysis.get("il_analysis", {})
                    pool_data["volatility_analysis"] = risk_analysis.get("volatility_analysis", {})
                    pool_data["pool_age_analysis"] = risk_analysis.get("pool_age_analysis", {})
                    
                except Exception as e:
                    logger.warning(f"Risk analysis failed: {e}")
            
            # Generate specific risk flags (now includes security info)
            risk_flags = self._generate_risk_flags(pool_data, protocol)
            
            return {
                "success": True,
                "pool": {
                    **pool_data,
                    "protocol": protocol.value,
                    "protocol_name": self._get_protocol_name(protocol),
                    "risk_flags": risk_flags,  # Specific risk explanations
                },
                "data_quality": DataQuality.PREMIUM.value,
                "quality_reason": "Aerodrome pool with verified factory",
                "source": source,
                "chain": chain
            }
        
        # Fallback to universal scanner if all else fails
        return await self._route_universal(pool_address, chain, protocol)
    
    async def _route_beefy(
        self, 
        vault_id: str, 
        chain: str
    ) -> Dict[str, Any]:
        """
        Route Beefy vault verification.
        Uses Beefy API for vault info, APY, TVL.
        """
        try:
            from data_sources.beefy import beefy_client
            
            # Get full vault data (includes APY and TVL)
            vault_data = await beefy_client.get_vault_full_data(vault_id)
            
            if not vault_data:
                return {
                    "success": False,
                    "error": f"Beefy vault not found: {vault_id}",
                    "input": vault_id
                }
            
            # Generate vault-specific risk flags
            risk_flags = self._generate_vault_risk_flags(vault_data)
            
            return {
                "success": True,
                "pool": {
                    **vault_data,
                    "protocol": Protocol.BEEFY.value,
                    "protocol_name": "Beefy Finance",
                    "risk_flags": risk_flags,
                    "isVerified": True,
                },
                "data_quality": DataQuality.HIGH.value,
                "quality_reason": "Beefy vault with verified API data",
                "source": "beefy_api",
                "chain": chain
            }
            
        except Exception as e:
            logger.error(f"Beefy routing failed: {e}")
            return {
                "success": False,
                "error": f"Failed to fetch Beefy vault: {str(e)}",
                "input": vault_id
            }
    
    def _generate_vault_risk_flags(self, vault_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate risk flags specific to single-sided vaults.
        Different risk profile than LP pools.
        """
        flags = []
        
        # 1. Strategy Risk (inherent to all vaults)
        strategy = vault_data.get("vault_strategy", "unknown")
        flags.append({
            "id": "strategy_risk",
            "label": "Strategy Risk",
            "severity": "medium",
            "description": f"Vault uses {strategy or 'automated'} strategy. Smart contract risk applies.",
            "icon": "🏗️"
        })
        
        # 2. Platform/Underlying Risk
        platform = vault_data.get("vault_platform", "unknown")
        if platform:
            flags.append({
                "id": "platform_risk",
                "label": f"Uses {platform.title()}",
                "severity": "low",
                "description": f"Vault deposits into {platform}. Additional protocol risk.",
                "icon": "🔗"
            })
        
        # 3. Withdrawal Fee
        withdrawal_fee = vault_data.get("vault_withdrawal_fee", 0)
        if withdrawal_fee and withdrawal_fee > 0:
            severity = "high" if withdrawal_fee > 0.5 else "medium" if withdrawal_fee > 0.1 else "low"
            flags.append({
                "id": "withdrawal_fee",
                "label": f"Withdrawal Fee: {withdrawal_fee}%",
                "severity": severity,
                "description": f"Vault charges {withdrawal_fee}% on withdrawals",
                "icon": "💸"
            })
        
        # 4. Vault Status (deprecated/EOL)
        status = vault_data.get("vault_status", "active")
        if status == "eol" or status == "paused":
            flags.append({
                "id": "deprecated_vault",
                "label": "Deprecated Vault",
                "severity": "high",
                "description": "This vault is no longer active. Withdraw your funds.",
                "icon": "⚠️"
            })
        
        # 5. Low TVL
        tvl = vault_data.get("tvl", 0)
        if tvl < 100000:
            flags.append({
                "id": "low_tvl",
                "label": "Low TVL",
                "severity": "medium",
                "description": f"TVL of ${tvl:,.0f} is relatively low",
                "icon": "💧"
            })
        
        # 6. High APY Warning
        apy = vault_data.get("apy", 0)
        if apy > 100:
            flags.append({
                "id": "high_apy",
                "label": "High APY",
                "severity": "high",
                "description": f"APY of {apy:.1f}% is unusually high. Verify sustainability.",
                "icon": "🔥"
            })
        
        # 7. Beefy-provided risks
        beefy_risks = vault_data.get("vault_risks", [])
        for risk in beefy_risks[:3]:  # Limit to top 3
            flags.append({
                "id": f"beefy_{risk.lower().replace(' ', '_')}",
                "label": risk,
                "severity": "low",
                "description": f"Beefy-identified risk factor: {risk}",
                "icon": "📋"
            })
        
        return flags

    async def _route_moonwell(
        self, 
        token_or_address: str, 
        chain: str
    ) -> Dict[str, Any]:
        """
        Route Moonwell lending market verification.
        Uses Moonwell API for supply/borrow APY, utilization.
        """
        try:
            from data_sources.moonwell import moonwell_client
            
            # Get full market data (includes APY and TVL)
            market_data = await moonwell_client.get_market_full_data(token_or_address, chain)
            
            if not market_data:
                return {
                    "success": False,
                    "error": f"Moonwell market not found: {token_or_address}",
                    "input": token_or_address
                }
            
            # Generate lending-specific risk flags
            risk_flags = self._generate_lending_risk_flags(market_data)
            
            return {
                "success": True,
                "pool": {
                    **market_data,
                    "protocol": Protocol.MOONWELL.value,
                    "protocol_name": "Moonwell",
                    "risk_flags": risk_flags,
                    "isVerified": True,
                },
                "data_quality": DataQuality.HIGH.value,
                "quality_reason": "Moonwell lending market with verified API data",
                "source": "moonwell_api",
                "chain": chain
            }
            
        except Exception as e:
            logger.error(f"Moonwell routing failed: {e}")
            return {
                "success": False,
                "error": f"Failed to fetch Moonwell market: {str(e)}",
                "input": token_or_address
            }
    
    def _generate_lending_risk_flags(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate risk flags specific to lending protocols.
        Different risk profile than LP pools or vaults.
        """
        flags = []
        
        # 1. Protocol Risk (inherent to lending)
        flags.append({
            "id": "lending_risk",
            "label": "Lending Protocol",
            "severity": "low",
            "description": "Funds are lent to borrowers. Smart contract and liquidation risks apply.",
            "icon": "🏦"
        })
        
        # 2. High Utilization Warning
        utilization = market_data.get("utilization_rate", 0)
        if utilization > 90:
            flags.append({
                "id": "high_utilization",
                "label": "High Utilization",
                "severity": "high",
                "description": f"{utilization:.0f}% utilization - withdrawals may be delayed",
                "icon": "⚠️"
            })
        elif utilization > 75:
            flags.append({
                "id": "elevated_utilization",
                "label": "Elevated Utilization",
                "severity": "medium",
                "description": f"{utilization:.0f}% utilization - monitor withdrawal liquidity",
                "icon": "📊"
            })
        
        # 3. Collateral Factor
        collateral_factor = market_data.get("collateral_factor", 0)
        if collateral_factor > 0:
            flags.append({
                "id": "collateral_enabled",
                "label": f"Collateral: {collateral_factor:.0f}%",
                "severity": "low",
                "description": f"Can borrow up to {collateral_factor:.0f}% of deposit value",
                "icon": "🔐"
            })
        
        # 4. Rewards APY
        apy_reward = market_data.get("apy_reward", 0)
        if apy_reward > 0:
            apy_total = market_data.get("apy", 0)
            reward_pct = (apy_reward / apy_total * 100) if apy_total > 0 else 0
            if reward_pct > 50:
                flags.append({
                    "id": "reward_dependent",
                    "label": "WELL Rewards",
                    "severity": "medium",
                    "description": f"{reward_pct:.0f}% of APY from WELL tokens - may decrease",
                    "icon": "🌙"
                })
        
        # 5. Low TVL
        tvl = market_data.get("tvl", 0)
        if tvl < 1000000:
            flags.append({
                "id": "low_tvl",
                "label": "Low Liquidity",
                "severity": "medium" if tvl < 100000 else "low",
                "description": f"${tvl:,.0f} total supply - may affect withdrawal speed",
                "icon": "💧"
            })
        
        # 6. High APY Warning
        apy = market_data.get("apy", 0)
        if apy > 50:
            flags.append({
                "id": "high_apy",
                "label": "High APY",
                "severity": "high" if apy > 100 else "medium",
                "description": f"Supply APY of {apy:.1f}% - verify sustainability",
                "icon": "🔥"
            })
        
        return flags

    async def _route_uniswap_v3(
        self, 
        pool_address: str, 
        chain: str
    ) -> Dict[str, Any]:
        """
        Tier 2 (High): Uniswap V3 analysis with fee APY calculation.
        For now, use UniversalScanner for V3 pools.
        TODO: Implement dedicated UniswapV3Adapter with fee growth calculation.
        """
        # Use universal scanner for now (detects CLAMM automatically)
        from data_sources.universal_adapter import universal_scanner
        
        result = await universal_scanner.scan(pool_address, chain)
        
        if result:
            return {
                "success": True,
                "pool": {
                    **result,
                    "protocol": Protocol.UNISWAP_V3.value,
                    "protocol_name": "Uniswap V3",
                },
                "data_quality": DataQuality.HIGH.value,
                "quality_reason": "CLAMM pool detected, fee APY estimation available",
                "source": "universal_scanner+protocol_detected",
                "chain": chain
            }
        
        return {
            "success": False,
            "error": "Failed to analyze Uniswap V3 pool",
            "pool_address": pool_address,
            "chain": chain
        }
    
    async def _route_universal(
        self, 
        pool_address: str, 
        chain: str,
        protocol: Protocol
    ) -> Dict[str, Any]:
        """
        Tier 3 (Basic): Universal scanner fallback for unknown protocols.
        OPTIMIZED: GeckoTerminal FIRST (fast), then on-chain fallback if needed.
        """
        from data_sources.geckoterminal import gecko_client
        
        # STEP 1: Try GeckoTerminal FIRST - single fast API call (~2s)
        gecko_data = await gecko_client.get_pool_by_address(chain, pool_address)
        
        if gecko_data and gecko_data.get("tvl", 0) > 0:
            # GeckoTerminal has data - use it as primary source
            logger.info(f"[Universal] GeckoTerminal fast-path: TVL=${gecko_data.get('tvl'):,.0f}")
            
            pool_data = {
                **gecko_data,
                "address": pool_address,
                "pool_address": pool_address,
                "protocol": protocol.value if protocol != Protocol.UNKNOWN else gecko_data.get("project", "unknown"),
                "protocol_name": self._get_protocol_name(protocol) if protocol != Protocol.UNKNOWN else gecko_data.get("project", "Unknown Protocol"),
                "contract_type": "v2_lp",  # Default assumption
            }
            
            # Try to enrich with Merkl APY data
            pool_data = await self._patch_with_merkl(pool_data, pool_address, chain)
            
            # Generate specific risk flags
            risk_flags = self._generate_risk_flags(pool_data, protocol)
            pool_data["risk_flags"] = risk_flags
            
            return {
                "success": True,
                "pool": pool_data,
                "data_quality": DataQuality.BASIC.value,
                "quality_reason": "GeckoTerminal fast-path" + (" + Merkl APY" if pool_data.get("apy_source") == "merkl" else ""),
                "source": "geckoterminal",
                "chain": chain
            }
        
        # STEP 2: Fallback to UniversalScanner (slow but thorough)
        logger.info(f"[Universal] GeckoTerminal miss, falling back to on-chain scan...")
        from data_sources.universal_adapter import universal_scanner
        
        result = await universal_scanner.scan(pool_address, chain)
        
        if result and result.get("contract_type") != "generic":
            return {
                "success": True,
                "pool": {
                    **result,
                    "protocol": protocol.value if protocol != Protocol.UNKNOWN else result.get("project", "unknown"),
                    "protocol_name": self._get_protocol_name(protocol) if protocol != Protocol.UNKNOWN else result.get("project", "Unknown Protocol"),
                },
                "data_quality": DataQuality.BASIC.value,
                "quality_reason": "On-chain scan fallback",
                "warning": "Unrecognized Protocol - contract verification recommended" if protocol == Protocol.UNKNOWN else None,
                "source": "universal_scanner",
                "chain": chain
            }
        
        if result:
            return {
                "success": True,
                "pool": result,
                "data_quality": DataQuality.BASIC.value,
                "quality_reason": "Generic contract - limited data available",
                "warning": "Not a standard pool contract - limited analysis available",
                "source": "universal_scanner",
                "chain": chain
            }
        
        return {
            "success": False,
            "error": "Invalid Contract Address - not a pool or vault",
            "pool_address": pool_address,
            "chain": chain
        }
    
    async def _patch_with_defillama(
        self, 
        pool_data: Dict[str, Any], 
        pool_address: str, 
        chain: str
    ) -> Dict[str, Any]:
        """
        Try to patch pool data with APY from DefiLlama.
        OPTIMIZED: Short timeout, skip only if already has APY.
        """
        import httpx
        
        # Skip only if already has APY (volume doesn't mean we have APY!)
        if pool_data.get("apy", 0) > 0:
            return pool_data
        
        try:
            # Short timeout - DefiLlama pools endpoint is SLOW (1.5MB)
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get("https://yields.llama.fi/pools")
                if response.status_code == 200:
                    pools = response.json().get("data", [])
                    
                    # Search by address
                    for p in pools:
                        if pool_address.lower() in (p.get("pool", "") or "").lower():
                            pool_data["apy"] = p.get("apy", 0)
                            pool_data["apy_base"] = p.get("apyBase", 0)
                            pool_data["apy_reward"] = p.get("apyReward", 0)
                            pool_data["apy_source"] = "defillama"
                            pool_data["project"] = p.get("project", pool_data.get("project"))
                            logger.info(f"Patched APY from DefiLlama: {pool_data['apy']:.2f}%")
                            break
        except Exception as e:
            logger.debug(f"DefiLlama patch skipped (timeout): {e}")
        
        return pool_data
    
    async def _patch_with_merkl(
        self, 
        pool_data: Dict[str, Any], 
        pool_address: str, 
        chain: str
    ) -> Dict[str, Any]:
        """
        Try to patch pool data with APY from Merkl API.
        Merkl provides real-time APR for incentivized LP positions.
        """
        # Skip if already has APY from higher-tier source
        if pool_data.get("apy", 0) > 0 and pool_data.get("apy_source") not in [None, "defillama"]:
            return pool_data
        
        try:
            from data_sources.merkl import merkl_client
            
            merkl_data = await merkl_client.get_pool_apr(pool_address, chain)
            
            if merkl_data and merkl_data.get("apr", 0) > 0:
                apr = merkl_data.get("apr", 0)
                
                # Only patch if Merkl has better APR data
                current_apy = pool_data.get("apy", 0) or 0
                if apr > current_apy or pool_data.get("apy_source") == "defillama":
                    pool_data["apy"] = apr
                    pool_data["apy_reward"] = apr
                    pool_data["apy_source"] = "merkl"
                    pool_data["merkl_rewards"] = merkl_data.get("rewards", [])
                    
                    # Update TVL if Merkl has more recent data
                    merkl_tvl = merkl_data.get("tvl", 0)
                    if merkl_tvl > 0:
                        pool_data["tvl_merkl"] = merkl_tvl
                    
                    logger.info(f"Patched APY from Merkl: {apr:.2f}%")
                    
        except Exception as e:
            logger.debug(f"Merkl patch skipped: {e}")
        
        return pool_data
    
    async def _enrich_with_gecko_data(
        self, 
        pool_data: Dict[str, Any], 
        pool_address: str, 
        chain: str
    ) -> Dict[str, Any]:
        """
        Enrich pool data with GeckoTerminal market data (volume, TVL change).
        Called after on-chain data to add missing market metrics.
        """
        try:
            from data_sources.geckoterminal import gecko_client
            
            gecko_data = await gecko_client.get_pool_by_address(chain, pool_address)
            
            if gecko_data:
                # Add volume data
                pool_data["volume_24h"] = gecko_data.get("volume_24h", 0)
                pool_data["volume_24h_formatted"] = gecko_data.get("volume_24h_formatted", "N/A")
                
                # Add TVL change/trend data
                pool_data["tvl_change_24h"] = gecko_data.get("tvl_change_24h", 0)
                pool_data["tvl_change_7d"] = gecko_data.get("tvl_change_7d", 0)
                
                # Add trading fee and other market data
                if gecko_data.get("trading_fee"):
                    pool_data["trading_fee"] = gecko_data.get("trading_fee")
                if gecko_data.get("fee_24h_usd"):
                    pool_data["fee_24h_usd"] = gecko_data.get("fee_24h_usd")
                
                # Use GeckoTerminal project name if we don't have one
                if not pool_data.get("project") or pool_data.get("project") == "Unknown":
                    pool_data["project"] = gecko_data.get("project", pool_data.get("project"))
                
                logger.info(f"Enriched with GeckoTerminal: volume=${gecko_data.get('volume_24h', 0):,.0f}")
                
        except Exception as e:
            logger.debug(f"GeckoTerminal enrichment failed: {e}")
        
        return pool_data
    
    def _generate_risk_flags(self, pool_data: Dict[str, Any], protocol: Protocol) -> List[Dict[str, Any]]:
        """
        Generate specific risk flags based on pool characteristics.
        This is core value - explains WHY the risk level is what it is.
        
        Returns list of flags with: id, label, severity (low/medium/high), description
        """
        flags = []
        
        # 1. Emissions-based APY
        apy_reward = pool_data.get("apy_reward", 0) or pool_data.get("apyReward", 0) or 0
        apy_total = pool_data.get("apy", 0) or 0
        if apy_reward > 0 and apy_total > 0:
            reward_pct = (apy_reward / apy_total) * 100 if apy_total > 0 else 0
            if reward_pct > 50:
                flags.append({
                    "id": "emissions_based_apy",
                    "label": "Emissions-based APY",
                    "severity": "high" if reward_pct > 80 else "medium",
                    "description": f"{reward_pct:.0f}% of yield comes from token emissions, which may decrease over time",
                    "icon": "⚠️"
                })
        
        # 2. Concentrated Liquidity
        pool_type = pool_data.get("pool_type", "")
        is_cl = pool_type == "cl" or "slipstream" in str(protocol.value).lower()
        if is_cl:
            flags.append({
                "id": "concentrated_liquidity",
                "label": "Concentrated Liquidity",
                "severity": "medium",
                "description": "CL pools require active position management. Out-of-range positions earn 0 fees.",
                "icon": "📊"
            })
        
        # 3. External TVL Dependency (APY calculated from external source)
        apy_source = pool_data.get("apy_source", "")
        if "external" in apy_source or "defillama" in apy_source or "gecko" in apy_source:
            flags.append({
                "id": "external_tvl",
                "label": "External TVL Source",
                "severity": "low",
                "description": "TVL data sourced from external aggregator, may have 5-15 min delay",
                "icon": "🔗"
            })
        
        # 4. Admin-controlled Gauge (Aerodrome/Velodrome specific)
        has_gauge = pool_data.get("has_gauge", False)
        if has_gauge and protocol in [Protocol.AERODROME_V2, Protocol.AERODROME_SLIPSTREAM, Protocol.VELODROME]:
            flags.append({
                "id": "admin_gauge",
                "label": "Admin-controlled Gauge",
                "severity": "low",
                "description": "Gauge emissions are controlled by veAERO/veVELO voters and can change weekly",
                "icon": "🗳️"
            })
        
        # 5. Epoch-based Rewards
        epoch_remaining = pool_data.get("epoch_remaining")
        if epoch_remaining:
            flags.append({
                "id": "epoch_rewards",
                "label": "Epoch-based Rewards",
                "severity": "low",
                "description": "Rewards reset each epoch. APY may change after epoch ends.",
                "icon": "⏳"
            })
        
        # 6. High APY Warning
        if apy_total > 100:
            flags.append({
                "id": "high_apy",
                "label": "High APY",
                "severity": "high",
                "description": f"APY of {apy_total:.1f}% is unusually high - verify sustainability",
                "icon": "🔥"
            })
        
        # 7. Low TVL Warning
        tvl = pool_data.get("tvl", 0) or pool_data.get("tvlUsd", 0) or 0
        if tvl < 500000:
            flags.append({
                "id": "low_tvl",
                "label": "Low TVL",
                "severity": "medium" if tvl < 100000 else "low",
                "description": f"TVL of ${tvl:,.0f} may cause slippage on larger trades",
                "icon": "💧"
            })
        
        # 8. Impermanent Loss Risk
        il_risk = pool_data.get("il_risk", "") or pool_data.get("ilRisk", "")
        if il_risk == "yes" or il_risk == "high":
            flags.append({
                "id": "il_risk",
                "label": "IL Risk",
                "severity": "medium",
                "description": "Volatile pair is subject to impermanent loss during price swings",
                "icon": "📉"
            })
        
        # 9. Security Risks (from GoPlus RugCheck)
        security_status = pool_data.get("security_status", "")
        if security_status == "critical":
            flags.insert(0, {  # Insert at beginning - critical!
                "id": "honeypot",
                "label": "🍯 HONEYPOT",
                "severity": "critical",
                "description": "CRITICAL: This token cannot be sold! DO NOT INVEST.",
                "icon": "🚨"
            })
        elif security_status == "high_risk":
            flags.append({
                "id": "token_security",
                "label": "Token Security Issues",
                "severity": "high",
                "description": "GoPlus detected high-risk token features (high taxes, hidden owner, etc.)",
                "icon": "🛡️"
            })
        elif security_status == "medium_risk":
            flags.append({
                "id": "token_risk",
                "label": "Token Risk",
                "severity": "medium",
                "description": "Some security concerns detected - verify contract before depositing",
                "icon": "⚡"
            })
        
        # Add specific security risks as separate flags
        for risk in pool_data.get("security_risks", [])[:3]:  # Top 3 risks
            severity_map = {"CRITICAL": "high", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
            flags.append({
                "id": f"security_{risk.get('type', 'unknown').lower()}",
                "label": risk.get("reason", "Security issue"),
                "severity": severity_map.get(risk.get("type", ""), "medium"),
                "description": risk.get("reason", ""),
                "icon": "🔒"
            })
        
        return flags
    
    def _get_audit_status(self, pool_data: Dict[str, Any], protocol: Protocol) -> Dict[str, Any]:
        """
        Get audit status for a protocol.
        Returns audit information for risk scoring.
        """
        # Known audited protocols (Tier 1 = top audits, Tier 2 = standard audits)
        AUDITED_PROTOCOLS = {
            Protocol.AERODROME_V2: {"audited": True, "auditor": "OpenZeppelin", "tier": 1},
            Protocol.AERODROME_SLIPSTREAM: {"audited": True, "auditor": "OpenZeppelin", "tier": 1},
            Protocol.UNISWAP_V3: {"audited": True, "auditor": "ABDK, Trail of Bits", "tier": 1},
            Protocol.VELODROME: {"audited": True, "auditor": "Code4rena", "tier": 2},
            Protocol.BEEFY: {"audited": True, "auditor": "Certik", "tier": 2},
            Protocol.MOONWELL: {"audited": True, "auditor": "Halborn", "tier": 2},
            Protocol.COMPOUND: {"audited": True, "auditor": "OpenZeppelin", "tier": 1},
            Protocol.AAVE: {"audited": True, "auditor": "OpenZeppelin, Trail of Bits", "tier": 1},
            Protocol.SUSHISWAP: {"audited": True, "auditor": "Peckshield", "tier": 2},
        }
        
        # Check if protocol is in known audited list
        if protocol in AUDITED_PROTOCOLS:
            return AUDITED_PROTOCOLS[protocol]
        
        # Check by project name (for pools detected via other means)
        project = (pool_data.get("project", "") or "").lower()
        PROJECT_AUDITS = {
            "aerodrome": {"audited": True, "auditor": "OpenZeppelin", "tier": 1},
            "uniswap": {"audited": True, "auditor": "ABDK", "tier": 1},
            "curve": {"audited": True, "auditor": "Trail of Bits", "tier": 1},
            "aave": {"audited": True, "auditor": "OpenZeppelin", "tier": 1},
            "compound": {"audited": True, "auditor": "OpenZeppelin", "tier": 1},
            "morpho": {"audited": True, "auditor": "Spearbit", "tier": 1},
            "moonwell": {"audited": True, "auditor": "Halborn", "tier": 2},
            "beefy": {"audited": True, "auditor": "Certik", "tier": 2},
            "yearn": {"audited": True, "auditor": "Multiple", "tier": 1},
            "convex": {"audited": True, "auditor": "MixBytes", "tier": 2},
            "balancer": {"audited": True, "auditor": "Trail of Bits", "tier": 1},
            "merkl": {"audited": True, "auditor": "Angle Labs", "tier": 2},
        }
        
        for name, audit in PROJECT_AUDITS.items():
            if name in project:
                return audit
        
        # Unknown protocol
        return {"audited": False, "auditor": None, "tier": 0}
    
    def _get_protocol_name(self, protocol: Protocol) -> str:
        """Get human-readable protocol name"""
        names = {
            Protocol.AERODROME_V2: "Aerodrome V2",
            Protocol.AERODROME_SLIPSTREAM: "Aerodrome Slipstream",
            Protocol.UNISWAP_V3: "Uniswap V3",
            Protocol.ALIENBASE: "AlienBase",
            Protocol.BASESWAP: "BaseSwap",
            Protocol.SUSHISWAP: "SushiSwap",
            Protocol.VELODROME: "Velodrome",
            Protocol.UNKNOWN: "Unknown Protocol",
        }
        return names.get(protocol, "Unknown Protocol")


# Singleton instance
smart_router = SmartRouter()
