"""
On-chain Data Client
Provides real-time pool data directly from blockchain RPC nodes
Supports Base, Ethereum, and Solana with fallback endpoints
"""
import logging
from typing import Optional, Dict, Any, List
from web3 import Web3
from web3.exceptions import Web3Exception
import asyncio

logger = logging.getLogger("OnChain")

# Multi-chain RPC configuration with fallbacks
RPC_ENDPOINTS = {
    "base": {
        "primary": "https://mainnet.base.org",
        "fallback": "https://base.llamarpc.com",
        "chain_id": 8453,
    },
    "ethereum": {
        "primary": "https://eth.llamarpc.com",
        "fallback": "https://rpc.ankr.com/eth",
        "chain_id": 1,
    },
    "arbitrum": {
        "primary": "https://arb1.arbitrum.io/rpc",
        "fallback": "https://arbitrum.llamarpc.com",
        "chain_id": 42161,
    },
    "optimism": {
        "primary": "https://mainnet.optimism.io",
        "fallback": "https://optimism.llamarpc.com",
        "chain_id": 10,
    },
    "polygon": {
        "primary": "https://polygon-rpc.com",
        "fallback": "https://polygon.llamarpc.com",
        "chain_id": 137,
    },
}

# Solana RPC (separate handling due to different architecture)
SOLANA_ENDPOINTS = {
    "primary": "https://api.mainnet-beta.solana.com",
    "fallback": "https://solana.public-rpc.com",
}

# Common LP Pool ABI (Uniswap V2 style - works for Aerodrome, Velodrome, etc.)
LP_POOL_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "reserve0", "type": "uint112"},
            {"name": "reserve1", "type": "uint112"},
            {"name": "blockTimestampLast", "type": "uint32"}
        ],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
]

# ERC20 ABI for token info
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
]


class OnChainClient:
    """Multi-chain on-chain data client with fallback support"""
    
    def __init__(self):
        self.web3_instances: Dict[str, Web3] = {}
        self._init_connections()
        logger.info("⛓️ On-chain client initialized with multi-chain RPC")
    
    def _init_connections(self):
        """Initialize Web3 connections for all chains"""
        for chain, config in RPC_ENDPOINTS.items():
            try:
                # Try primary endpoint
                w3 = Web3(Web3.HTTPProvider(config["primary"], request_kwargs={'timeout': 10}))
                if w3.is_connected():
                    self.web3_instances[chain] = w3
                    logger.info(f"  ✅ {chain}: connected to primary RPC")
                else:
                    # Try fallback
                    w3 = Web3(Web3.HTTPProvider(config["fallback"], request_kwargs={'timeout': 10}))
                    if w3.is_connected():
                        self.web3_instances[chain] = w3
                        logger.info(f"  ⚠️ {chain}: connected to fallback RPC")
                    else:
                        logger.warning(f"  ❌ {chain}: failed to connect to any RPC")
            except Exception as e:
                logger.error(f"  ❌ {chain}: RPC init error: {e}")
    
    def get_web3(self, chain: str) -> Optional[Web3]:
        """Get Web3 instance for chain, with fallback retry"""
        chain = chain.lower()
        
        if chain in self.web3_instances:
            w3 = self.web3_instances[chain]
            if w3.is_connected():
                return w3
        
        # Try to reconnect
        if chain in RPC_ENDPOINTS:
            config = RPC_ENDPOINTS[chain]
            for endpoint in [config["primary"], config["fallback"]]:
                try:
                    w3 = Web3(Web3.HTTPProvider(endpoint, request_kwargs={'timeout': 10}))
                    if w3.is_connected():
                        self.web3_instances[chain] = w3
                        return w3
                except:
                    continue
        
        return None
    
    async def get_lp_reserves(self, chain: str, pool_address: str) -> Optional[Dict[str, Any]]:
        """
        Get LP pool reserves directly from on-chain
        
        Args:
            chain: Chain name (base, ethereum, etc.)
            pool_address: Pool contract address
            
        Returns:
            Dict with reserve0, reserve1, token addresses, or None
        """
        w3 = self.get_web3(chain)
        if not w3:
            logger.warning(f"No Web3 connection for {chain}")
            return None
        
        try:
            pool_address = Web3.to_checksum_address(pool_address)
            pool_contract = w3.eth.contract(address=pool_address, abi=LP_POOL_ABI)
            
            # Get reserves
            reserves = pool_contract.functions.getReserves().call()
            token0 = pool_contract.functions.token0().call()
            token1 = pool_contract.functions.token1().call()
            
            # Get token decimals
            token0_contract = w3.eth.contract(address=token0, abi=ERC20_ABI)
            token1_contract = w3.eth.contract(address=token1, abi=ERC20_ABI)
            
            decimals0 = token0_contract.functions.decimals().call()
            decimals1 = token1_contract.functions.decimals().call()
            
            symbol0 = token0_contract.functions.symbol().call()
            symbol1 = token1_contract.functions.symbol().call()
            
            return {
                "reserve0": reserves[0] / (10 ** decimals0),
                "reserve1": reserves[1] / (10 ** decimals1),
                "token0": token0.lower(),
                "token1": token1.lower(),
                "symbol0": symbol0,
                "symbol1": symbol1,
                "decimals0": decimals0,
                "decimals1": decimals1,
                "raw_reserve0": reserves[0],
                "raw_reserve1": reserves[1],
                "block_timestamp": reserves[2],
            }
            
        except Exception as e:
            logger.error(f"Failed to get LP reserves for {pool_address}: {e}")
            return None
    
    async def calculate_tvl(
        self, 
        chain: str, 
        pool_address: str,
        token0_price: float,
        token1_price: float
    ) -> Optional[float]:
        """
        Calculate TVL from on-chain reserves and prices
        
        Args:
            chain: Chain name
            pool_address: Pool contract address
            token0_price: USD price of token0
            token1_price: USD price of token1
            
        Returns:
            TVL in USD or None
        """
        reserves = await self.get_lp_reserves(chain, pool_address)
        if not reserves:
            return None
        
        tvl = (reserves["reserve0"] * token0_price) + (reserves["reserve1"] * token1_price)
        return tvl
    
    def is_chain_available(self, chain: str) -> bool:
        """Check if chain RPC is available"""
        w3 = self.get_web3(chain)
        return w3 is not None and w3.is_connected()
    
    def get_available_chains(self) -> List[str]:
        """Get list of chains with working RPC connections"""
        return [chain for chain in RPC_ENDPOINTS.keys() if self.is_chain_available(chain)]


# Singleton instance
onchain_client = OnChainClient()
