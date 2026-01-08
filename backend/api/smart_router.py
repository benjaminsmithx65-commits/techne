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
from typing import Optional, Dict, Any, Tuple
from web3 import Web3
from enum import Enum

logger = logging.getLogger("SmartRouter")


class Protocol(Enum):
    """Detected protocol based on factory address"""
    AERODROME_V2 = "aerodrome_v2"
    AERODROME_SLIPSTREAM = "aerodrome_slipstream"
    UNISWAP_V3 = "uniswap_v3"
    ALIENBASE = "alienbase"
    BASESWAP = "baseswap"
    SUSHISWAP = "sushiswap"
    VELODROME = "velodrome"
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
    
    def parse_input(self, input_str: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse user input - could be address or URL.
        Returns (pool_address, chain)
        """
        input_str = input_str.strip()
        
        # Check if it's a URL
        if input_str.startswith("http"):
            return self._parse_url(input_str)
        
        # Check if it's an address
        if input_str.startswith("0x") and len(input_str) == 42:
            return input_str.lower(), None  # Chain unknown
        
        return None, None
    
    def _parse_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse pool URL to extract address and chain"""
        url = url.lower()
        
        # Aerodrome: aerodrome.finance/pools/0x...
        if "aerodrome.finance" in url:
            match = re.search(r'0x[a-f0-9]{40}', url)
            return (match.group(0), "base") if match else (None, None)
        
        # Uniswap: app.uniswap.org/...base/pools/0x...
        if "uniswap.org" in url:
            match = re.search(r'0x[a-f0-9]{40}', url)
            chain = "base" if "/base/" in url else "ethereum"
            return (match.group(0), chain) if match else (None, None)
        
        # GeckoTerminal: geckoterminal.com/base/pools/0x...
        if "geckoterminal.com" in url:
            match = re.search(r'/(base|eth|arbitrum|optimism)/pools/(0x[a-f0-9]{40})', url)
            if match:
                chain_map = {"eth": "ethereum"}
                chain = chain_map.get(match.group(1), match.group(1))
                return match.group(2), chain
        
        # Fallback: try to find address
        match = re.search(r'0x[a-f0-9]{40}', url)
        return (match.group(0), None) if match else (None, None)
    
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
            input_str: Pool address or URL
            chain: Optional chain hint (will be auto-detected from URL if possible)
        
        Returns:
            Unified pool data with quality tier indicator
        """
        # Step 1: Parse input
        pool_address, parsed_chain = self.parse_input(input_str)
        
        if not pool_address:
            return {
                "success": False,
                "error": "Invalid input - could not parse pool address",
                "input": input_str
            }
        
        chain = chain or parsed_chain or "base"
        logger.info(f"🧠 SmartRouter processing: {pool_address[:10]}... on {chain}")
        
        # Step 2: Detect protocol via factory
        protocol = await self.detect_protocol(pool_address, chain)
        adapter_type = PROTOCOL_ADAPTERS.get(protocol, "universal")
        
        # Step 3: Route to appropriate adapter
        if adapter_type == "aerodrome":
            return await self._route_aerodrome(pool_address, chain, protocol)
        elif adapter_type == "uniswap_v3":
            return await self._route_uniswap_v3(pool_address, chain)
        else:
            return await self._route_universal(pool_address, chain, protocol)
    
    async def _route_aerodrome(
        self, 
        pool_address: str, 
        chain: str,
        protocol: Protocol
    ) -> Dict[str, Any]:
        """
        Tier 1 (Premium): Full Aerodrome analysis.
        - V2 pools: Use on-chain Gauge for APY
        - Slipstream (CL): Use GeckoTerminal + on-chain enrichment
        """
        pool_data = None
        source = "unknown"
        
        # For Slipstream (CL pools), use GeckoTerminal as primary (more reliable for CL)
        if protocol == Protocol.AERODROME_SLIPSTREAM:
            try:
                from data_sources.geckoterminal import gecko_client
                gecko_data = await gecko_client.get_pool_by_address(chain, pool_address)
                
                if gecko_data and gecko_data.get("tvl", 0) > 0:
                    pool_data = gecko_data
                    source = "geckoterminal+factory_detected"
                    logger.info(f"Slipstream pool via GeckoTerminal: TVL=${gecko_data.get('tvl', 0):,.0f}")
            except Exception as e:
                logger.warning(f"GeckoTerminal for Slipstream failed: {e}")
        
        # For V2 pools OR if Slipstream GeckoTerminal failed, try on-chain adapter
        if not pool_data:
            try:
                from data_sources.aerodrome import aerodrome_client
                pool_data = await aerodrome_client.get_pool_by_address(pool_address)
                if pool_data:
                    source = "aerodrome_onchain"
            except Exception as e:
                logger.warning(f"Aerodrome on-chain adapter failed: {e}")
        
        # If we have data, enrich and return
        if pool_data:
            # Enrich with GeckoTerminal market data (volume, TVL trend)
            pool_data = await self._enrich_with_gecko_data(pool_data, pool_address, chain)
            
            return {
                "success": True,
                "pool": {
                    **pool_data,
                    "protocol": protocol.value,
                    "protocol_name": self._get_protocol_name(protocol),
                },
                "data_quality": DataQuality.PREMIUM.value,
                "quality_reason": "Aerodrome pool with verified factory",
                "source": source,
                "chain": chain
            }
        
        # Fallback to universal scanner if all else fails
        return await self._route_universal(pool_address, chain, protocol)
    
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
            
            return {
                "success": True,
                "pool": {
                    **gecko_data,
                    "address": pool_address,
                    "pool_address": pool_address,
                    "protocol": protocol.value if protocol != Protocol.UNKNOWN else gecko_data.get("project", "unknown"),
                    "protocol_name": self._get_protocol_name(protocol) if protocol != Protocol.UNKNOWN else gecko_data.get("project", "Unknown Protocol"),
                    "contract_type": "v2_lp",  # Default assumption
                },
                "data_quality": DataQuality.BASIC.value,
                "quality_reason": "GeckoTerminal fast-path",
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
        OPTIMIZED: Short timeout, skip if already has APY.
        """
        import httpx
        
        # Skip if already has APY or if we have volume (GeckoTerminal is faster)
        if pool_data.get("apy", 0) > 0 or pool_data.get("volume_24h", 0) > 0:
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
