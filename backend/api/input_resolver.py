"""
Input Resolver - Universal Address Extraction ("Vacuum Cleaner" Approach)
Extracts pool addresses from ANY input: raw addresses, Aerodrome URLs, Uniswap URLs, DexScreener, etc.
"""
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from web3 import Web3

logger = logging.getLogger("InputResolver")

# =============================================================================
# CONSTANTS
# =============================================================================

# Ethereum address pattern
ETH_ADDRESS_PATTERN = re.compile(r'(0x[a-fA-F0-9]{40})', re.IGNORECASE)

# Factory addresses (Base mainnet)
FACTORIES = {
    "aerodrome_v2": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
    "aerodrome_cl": "0x5e7BB104d84c7CB9B682AaC2F3d509f5F406809A",
    "aerodrome_cl_stable": "0xaDe65c38CD4849aDBA595a4323a8C7DdfE89716a",
    "uniswap_v3": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
    "alienbase": "0x3E84D913803b02A4a7f027165E8cA42C14C0FdE7",
}

# Factory ABI for getPool
FACTORY_ABI = [
    {
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"},
            {"name": "stable", "type": "bool"}
        ],
        "name": "getPool",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Uniswap V3 Factory has different signature
UNISWAP_V3_FACTORY_ABI = [
    {
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"},
            {"name": "fee", "type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Pool detection ABI
POOL_DETECTION_ABI = [
    {"inputs": [], "name": "factory", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token0", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "token1", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
]

# RPC endpoint
BASE_RPC = "https://mainnet.base.org"


class InvalidInputError(Exception):
    """Raised when input cannot be resolved to a pool address"""
    pass


class InputResolver:
    """
    Universal input resolver using "Vacuum Cleaner" approach.
    Extracts all 0x addresses from any input and determines pool address.
    """
    
    def __init__(self, web3_instance: Optional[Web3] = None):
        if web3_instance:
            self.w3 = web3_instance
        else:
            self.w3 = Web3(Web3.HTTPProvider(BASE_RPC, request_kwargs={'timeout': 15}))
        
        # Initialize factory contracts
        self.factories = {}
        for name, addr in FACTORIES.items():
            try:
                abi = UNISWAP_V3_FACTORY_ABI if "uniswap" in name else FACTORY_ABI
                self.factories[name] = self.w3.eth.contract(
                    address=Web3.to_checksum_address(addr),
                    abi=abi
                )
            except Exception as e:
                logger.warning(f"Failed to init factory {name}: {e}")
        
        logger.info("🔍 InputResolver initialized (Vacuum Cleaner mode)")
    
    def extract_addresses(self, input_str: str) -> List[str]:
        """
        Extract all unique Ethereum addresses from input string.
        Returns list of lowercase addresses.
        """
        if not input_str:
            return []
        
        matches = ETH_ADDRESS_PATTERN.findall(input_str)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for addr in matches:
            addr_lower = addr.lower()
            if addr_lower not in seen:
                seen.add(addr_lower)
                unique.append(addr_lower)
        
        return unique
    
    def is_pool_address(self, address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if address is a pool (has factory() method).
        Returns (is_pool, factory_address or None)
        """
        try:
            checksum = Web3.to_checksum_address(address)
            
            # Check if it's a contract
            code = self.w3.eth.get_code(checksum)
            if code == b'' or code == b'0x':
                return False, None
            
            # Try to call factory()
            contract = self.w3.eth.contract(address=checksum, abi=POOL_DETECTION_ABI)
            factory = contract.functions.factory().call()
            
            if factory and factory != "0x0000000000000000000000000000000000000000":
                return True, factory.lower()
            
            return False, None
            
        except Exception as e:
            logger.debug(f"is_pool_address check failed for {address[:10]}: {e}")
            return False, None
    
    def get_pool_from_tokens(
        self, 
        token0: str, 
        token1: str, 
        prefer_stable: bool = False,
        preferred_factory: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find pool address from token pair using factory calls.
        If preferred_factory is specified, try it first.
        """
        token0_cs = Web3.to_checksum_address(token0)
        token1_cs = Web3.to_checksum_address(token1)
        
        found_pools = []
        
        # Determine factory order based on preference
        # If preferred_factory matches a known factory, try it first
        factory_order = ["aerodrome_v2", "aerodrome_cl", "aerodrome_cl_stable"]
        if preferred_factory:
            pf_lower = preferred_factory.lower()
            # Match factory address to name
            for name, addr in FACTORIES.items():
                if addr.lower() == pf_lower:
                    # Move this factory to front
                    if name in factory_order:
                        factory_order.remove(name)
                        factory_order.insert(0, name)
                    logger.info(f"Preferring factory {name} based on URL")
                    break
        
        # Try Aerodrome factories
        for stable in [prefer_stable, not prefer_stable]:
            for factory_name in factory_order:
                if factory_name not in self.factories:
                    continue
                    
                try:
                    factory = self.factories[factory_name]
                    pool_addr = factory.functions.getPool(token0_cs, token1_cs, stable).call()
                    
                    if pool_addr and pool_addr != "0x0000000000000000000000000000000000000000":
                        logger.info(f"Found pool via {factory_name} (stable={stable}): {pool_addr}")
                        found_pools.append({
                            "address": pool_addr.lower(),
                            "factory": factory_name,
                            "stable": stable,
                            "protocol": "Aerodrome"
                        })
                        # Return immediately if this is the preferred factory
                        if preferred_factory and factory_name == factory_order[0]:
                            return found_pools[0]
                except Exception as e:
                    logger.debug(f"Factory {factory_name} getPool failed: {e}")
        
        # Try Uniswap V3 Factory (different fee tiers)
        if "uniswap_v3" in self.factories:
            for fee in [500, 3000, 10000, 100]:  # 0.05%, 0.3%, 1%, 0.01%
                try:
                    factory = self.factories["uniswap_v3"]
                    pool_addr = factory.functions.getPool(token0_cs, token1_cs, fee).call()
                    
                    if pool_addr and pool_addr != "0x0000000000000000000000000000000000000000":
                        logger.info(f"Found pool via Uniswap V3 (fee={fee}): {pool_addr}")
                        found_pools.append({
                            "address": pool_addr.lower(),
                            "factory": "uniswap_v3",
                            "fee": fee,
                            "protocol": "Uniswap V3"
                        })
                except Exception as e:
                    logger.debug(f"Uniswap V3 getPool fee={fee} failed: {e}")
        
        # Return first found (Aerodrome preferred)
        if found_pools:
            return found_pools[0]
        
        return None
    
    async def resolve(self, input_str: str, chain: str = "base") -> Dict[str, Any]:
        """
        Main resolver - takes ANY input and returns pool info.
        
        Returns:
            {
                "pool_address": "0x...",
                "type": "direct" | "from_tokens",
                "protocol": "Aerodrome" | "Uniswap V3" | "Unknown",
                "tokens": [token0, token1] if from_tokens
            }
        """
        if not input_str or not input_str.strip():
            raise InvalidInputError("Empty input")
        
        # Step 1: Extract all addresses
        addresses = self.extract_addresses(input_str)
        logger.info(f"[Resolve] Extracted {len(addresses)} addresses from input")
        
        if not addresses:
            raise InvalidInputError("No Ethereum addresses found in input")
        
        # Step 2: Scenario A - Single address
        if len(addresses) == 1:
            addr = addresses[0]
            is_pool, factory = self.is_pool_address(addr)
            
            if is_pool:
                # It's a pool - return directly
                protocol = "Unknown"
                if factory:
                    factory_lower = factory.lower()
                    if factory_lower in [v.lower() for v in FACTORIES.values() if "aerodrome" in FACTORIES.get(factory_lower, "")]:
                        protocol = "Aerodrome"
                    elif "uniswap" in factory_lower:
                        protocol = "Uniswap V3"
                
                return {
                    "pool_address": addr,
                    "type": "direct",
                    "protocol": protocol,
                    "factory": factory,
                    "tokens": None
                }
            else:
                # Single address but not a pool - might be a token
                raise InvalidInputError(f"Address {addr[:10]}... is not a pool. If it's a token, provide both tokens.")
        
        # Step 3: Scenario B - Two or more addresses (token pair)
        if len(addresses) >= 2:
            token0 = addresses[0]
            token1 = addresses[1]
            
            # Determine if stable from URL hints
            prefer_stable = "stable" in input_str.lower() or "type=10" in input_str or "type=1" in input_str
            
            # Extract factory from URL if present (for correct pool type selection)
            preferred_factory = None
            factory_match = re.search(r'factory=(0x[a-fA-F0-9]{40})', input_str, re.IGNORECASE)
            if factory_match:
                preferred_factory = factory_match.group(1).lower()
                logger.info(f"[Resolve] Found factory in URL: {preferred_factory[:10]}...")
            
            pool_info = self.get_pool_from_tokens(token0, token1, prefer_stable, preferred_factory)
            
            if pool_info:
                return {
                    "pool_address": pool_info["address"],
                    "type": "from_tokens",
                    "protocol": pool_info["protocol"],
                    "factory": pool_info.get("factory"),
                    "stable": pool_info.get("stable", False),
                    "tokens": [token0, token1]
                }
            else:
                raise InvalidInputError(f"No pool found for token pair {token0[:10]}.../{token1[:10]}...")
        
        raise InvalidInputError("Could not resolve input to pool address")


# Singleton instance
input_resolver = InputResolver()


async def resolve_input_to_pool_address(input_str: str, chain: str = "base") -> Dict[str, Any]:
    """
    Convenience function to resolve any input to pool address.
    
    Usage:
        result = await resolve_input_to_pool_address("https://aerodrome.finance/deposit?token0=0x...&token1=0x...")
        pool_address = result["pool_address"]
    """
    return await input_resolver.resolve(input_str, chain)
