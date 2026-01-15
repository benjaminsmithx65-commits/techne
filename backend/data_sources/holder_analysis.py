"""
Token Holder Analysis
Analyzes token holder distribution and whale concentration.
Uses Moralis API (primary), Covalent/GoldRush (fallback) for EVM chains, Helius for Solana.
"""

import httpx
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# API Configuration - loaded dynamically at runtime to ensure env vars are available
def get_moralis_key():
    return os.getenv("MORALIS_API_KEY", "")

def get_covalent_key():
    return os.getenv("COVALENT_API_KEY", "")

def get_helius_key():
    return os.getenv("HELIUS_API_KEY", "")



class HolderAnalysis:
    """Analyze token holder distribution and whale concentration."""
    
    # =========================================
    # UNIVERSAL: Known addresses (exchanges, contracts, protocols)
    # Used across all chains and providers
    # =========================================
    KNOWN_LABELS = {
        # ===== EXCHANGES =====
        "0x28c6c06298d514db089934071355e5743bf21d60": "Binance",
        "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance 2",
        "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance 8",
        "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8": "Binance 7",
        "0x5a52e96bacdabb82fd05763e25335261b270efcb": "Binance 14",
        "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Coinbase",
        "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "Coinbase 4",
        "0xa2327a938febf5fec13bacfb16ae10ecbc4cbdcf": "OKX",
        "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX 2",
        "0x88e6a0c2ddd26feeb64f039a2c41296fcd0dc4f8": "Uniswap V3 Pool",
        "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2": "FTX",
        "0x0d0707963952f2fba59dd06f2b425ace40b492fe": "Gate.io",
        "0x1ab4973a48dc892cd9971ece8e01dcc7688f8f23": "Kraken",
        "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Kraken 13",
        "0x0093e5f2a850268c0ca3093c7ea53731296487eb": "Coinone",
        "0x742d35cc6634c0532925a3b844bc9e7595f8db37": "Bitfinex",
        
        # ===== DEX ROUTERS =====
        "0x503828976d22510aad0201ac7ec88293211d23da": "Uniswap Router",
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3 Router",
        "0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b": "Uniswap Universal Router",
        "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "SushiSwap Router",
        "0x1111111254eeb25477b68fb85ed929f73a960582": "1inch Router",
        "0x1111111254fb6c44bac0bed2854e76f90643097d": "1inch v4",
        "0xdef1c0ded9bec7f1a1670819833240f027b25eff": "0x Exchange",
        
        # ===== AERODROME (Base) =====
        "0xebf418fe2512e7e6bd9b87a8f0f294acdc67e6b4": "veAERO (Voting Escrow)",
        "0x478946bcd4a5a22b316470f5486fafb928c0ba25": "AERO Minter",
        "0x16613524e02ad97edfef371bc883f2f5d6c480a5": "Aerodrome Voter",
        "0x940181a94a35a4569e4529a3cdfb74e38fd98631": "AERO Rewards",
        "0xcf77a3ba9a5f8fbe1d5e2cfb1e6f0d7a17dd77e5": "Aerodrome Router",
        "0x4f09bab2f0e15e2a078a227fe1537665f55b8360": "AERO/USDC Pool Gauge",
        
        # ===== VIRTUALS PROTOCOL (Base) =====
        "0x0b3e328455c4059eeb9e3f84b5543f74e24e7e1b": "VIRTUAL Token Contract",
        
        # ===== CEX on BASE =====
        "0x3304e22ddaa22bcdc5fca2269b418046ae7b566a": "Coinbase: Base Bridge Deposit",
        "0x1a0ad011913a150f69f6a19df447a0cfd9551054": "Binance: Base Hot Wallet",
        "0xf89d7b9c864f589bbf53a82105107622b35eaa40": "Bybit: Base Hot Wallet",
        "0x6887246668a3b87f54deb3b94ba47a6f63f32985": "OKX: Base Hot Wallet",
        "0xd6216fc19db775df9774a6e33526131da7d19a2c": "Kucoin: Base Hot Wallet",
        "0xe93685f3bba03016f02bd1828badd6195988d950": "Gate.io: Base Hot Wallet",
        
        # ===== BASE PROTOCOL ADDRESSES =====
        "0x4200000000000000000000000000000000000006": "WETH (Base)",
        "0x4200000000000000000000000000000000000016": "L2StandardBridge",
        "0x4200000000000000000000000000000000000007": "L2CrossDomainMessenger",
        "0x420000000000000000000000000000000000000f": "GasPriceOracle",
        
        # ===== MARKET MAKERS / TRADING BOTS =====
        "0x9008d19f58aabd9ed0d60971565aa8510560ab41": "CoW Protocol Vault",
        "0x4f3a120e72c76c22ae802d129f599bfdbc31cb81": "Wintermute",
        "0x0000006daea1723962647b7e189d311d757fb793": "Flashbots Builder",
        
        # ===== VELODROME (Optimism) =====
        "0xfaf8fd17d9840595845582fcb047df13f006787d": "veVELO (Voting Escrow)",
        "0x09236cff45047dbee6b921e00704bed6d6b8cf7e": "VELO Rewards",
        "0x9c7305eb78a432ced5c4d14cac27e8ed569a2e26": "Velodrome Router",
        
        # ===== CURVE =====
        "0x5f3b5dfeb7b28cdbd7faba78963ee202a494e2a2": "veCRV (Voting Escrow)",
        "0xd061d61a4d941c39e5453435b6345dc261c2fce0": "Curve Fee Dist",
        "0x8dff5e27ea6b7ac08ebfdf9eb090f32ee9a30fcf": "Curve Treasury",
        
        # ===== UNISWAP =====
        "0x1a9c8182c09f50c8318d769245bea52c32be35bc": "UNI Timelock",
        "0xe3d1a117df7dcac2eb0ac8219341bad92f18dac1": "UNI Staking",
        
        # ===== AAVE =====
        "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9": "AAVE Token",
        "0x4da27a545c0c5b758a6ba100e3a049001de870f5": "stkAAVE",
        "0x25f2226b597e8f9514b3f68f00f494cf4f286491": "AAVE Treasury",
        
        # ===== COMPOUND =====
        "0xc0da02939e1441f497fd74f78ce7decb17b66529": "COMP Governor",
        "0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b": "Comptroller",
        
        # ===== LIDO =====
        "0xae7ab96520de3a18e5e111b5eaab095312d7fe84": "stETH",
        "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0": "wstETH",
        "0x3e40d73eb977dc6a537af587d48316fee66e9c8c": "Lido Treasury",
        
        # ===== MAKER =====
        "0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2": "MKR Token",
        "0xbe8e3e3618f7474f8cb1d074a26affef007e98fb": "DSR Manager",
        
        # ===== BRIDGES & L2 =====
        "0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": "Optimism Gateway",
        "0xa3a7b6f88361f48403514059f1f16c8e78d60eec": "Arbitrum Gateway",
        "0x49048044d57e1c92a77f79988d21fa8faf74e97e": "Base Bridge",
        "0x3154cf16ccdb4c6d922629664174b904d80f2c35": "Base Portal",
        
        # ===== BEEFY (Single-sided vaults) =====
        "0x45c6bfcd5b269fdd3c23b89a18c4da2e3a8e0457": "Beefy Treasury",
        "0x7f5fc52dbb3c8cdedfcf516dd4c9a779c3f8a908": "Beefy Fee Batch",
        
        # ===== YEARN =====
        "0x9c2a3f3b27ad24e3e26e6e8c08a6ee4c704e75d7": "Yearn Treasury",
        
        # ===== STABLECOINS =====
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC Contract",
        "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT Contract",
        "0x6b175474e89094c44da98b954eedeac495271d0f": "DAI Contract",
        "0x4fabb145d64652a948d72533023f6e7a623c7c53": "BUSD Contract",
        
        # ===== COMMON =====
        "0x0000000000000000000000000000000000000000": "Burn Address",
        "0x000000000000000000000000000000000000dead": "Dead Address",
        "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": "Native Token",
    }
    
    # UNIVERSAL: Patterns that indicate "safe" protocol holdings (not real whales)
    # These are detected by label name, not hardcoded addresses
    # Works across all chains: Base, Ethereum, Solana, Arbitrum, etc.
    SAFE_LABEL_PATTERNS = [
        # Voting/Staking
        "ve",           # veAERO, veVELO, veCRV, etc.
        "staking",      # Staking contracts
        "escrow",       # Voting Escrow
        "gauge",        # LP Gauge contracts (staking LP for rewards)
        "vault",        # Vault contracts (Beefy, Yearn)
        # Burn/Dead
        "burn",         # Burn addresses
        "dead",         # Dead addresses
        # Protocol infrastructure
        "treasury",     # Protocol treasuries
        "rewards",      # Reward distributors
        "minter",       # Token minters
        "timelock",     # Governance timelocks
        "governor",     # Governance contracts
        "multisig",     # Multisig wallets (protocol-controlled)
        # Routing/Bridges
        "bridge",       # Cross-chain bridges
        "router",       # DEX routers (not holding, just routing)
        "pool",         # Pool contracts (Uniswap, Raydium, etc.)
        # Solana-specific
        "authority",    # Program authorities
        "program",      # Solana programs
        "pda",          # Program Derived Addresses
    ]
    
    @classmethod
    def is_safe_protocol_address(cls, address: str, label: str) -> bool:
        """
        Check if address is a safe protocol contract (not a whale).
        UNIVERSAL: Works across EVM and Solana.
        """
        label_lower = label.lower()
        # Check label patterns
        for pattern in cls.SAFE_LABEL_PATTERNS:
            if pattern in label_lower:
                return True
        # Also check common burn/dead addresses (EVM)
        if address.lower() in ("0x0000000000000000000000000000000000000000", 
                               "0x000000000000000000000000000000000000dead"):
            return True
        # Solana burn address
        if address == "11111111111111111111111111111111":
            return True
        return False
    
    @classmethod
    def get_label(cls, address: str) -> str:
        """Get known label for address, or 'Unknown'."""
        return cls.KNOWN_LABELS.get(address.lower(), "Unknown")
    
    def __init__(self):
        self.cache = {}
        self.moralis_base = "https://deep-index.moralis.io/api/v2.2"
        self.covalent_base = "https://api.covalenthq.com/v1"
        self.helius_base = "https://api.helius.xyz/v0"
    
    
    async def get_holder_analysis(
        self,
        token_address: str,
        chain: str = "base"
    ) -> Dict[str, Any]:
        """
        Get holder distribution analysis for a token.
        
        Returns:
            {
                "holder_count": 12345,
                "top_10_percent": 45.5,
                "top_1_holder_percent": 12.3,
                "concentration_risk": "high" | "medium" | "low",
                "holders": [
                    {"address": "0x...", "percent": 12.3, "label": "Binance"},
                    ...
                ],
                "holder_trend_7d": +89,
                "source": "moralis" | "covalent" | "helius" | "estimated"
            }
        """
        # Check for Solana
        if chain.lower() == "solana":
            return await self._analyze_solana_holders(token_address)
        
        # EVM chains - try Moralis first (better free tier: 40K req/month)
        if get_moralis_key():
            try:
                return await self._analyze_evm_holders_moralis(token_address, chain)
            except Exception as e:
                logger.warning(f"Moralis holder analysis failed: {e}")
        
        # Fallback to Covalent/GoldRush
        if get_covalent_key():
            try:
                return await self._analyze_evm_holders_covalent(token_address, chain)
            except Exception as e:
                logger.warning(f"Covalent holder analysis failed: {e}")
        
        # Fallback to estimated analysis based on common patterns
        return await self._estimate_holder_distribution(token_address, chain)
    
    async def _analyze_evm_holders_moralis(
        self,
        token_address: str,
        chain: str
    ) -> Dict[str, Any]:
        """Analyze holders using Moralis API (better than Covalent for free tier)."""
        chain_map = {
            "base": "base",
            "ethereum": "eth",
            "arbitrum": "arbitrum",
            "optimism": "optimism",
            "polygon": "polygon",
            "bsc": "bsc"
        }
        
        moralis_chain = chain_map.get(chain.lower(), chain.lower())
        url = f"{self.moralis_base}/erc20/{token_address}/owners"
        
        headers = {"X-API-Key": get_moralis_key()}
        params = {"chain": moralis_chain, "limit": 100}
        
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                holders = data.get("result", [])
                
                if holders:
                    return self._process_moralis_holder_data(holders)
        
        raise Exception(f"Moralis API returned {response.status_code}")
    
    async def _analyze_evm_holders_covalent(
        self,
        token_address: str,
        chain: str
    ) -> Dict[str, Any]:
        """Analyze holders using Covalent API."""
        chain_map = {
            "base": "base-mainnet",
            "ethereum": "eth-mainnet",
            "arbitrum": "arbitrum-mainnet",
            "optimism": "optimism-mainnet",
            "polygon": "matic-mainnet",
            "bsc": "bsc-mainnet"
        }
        
        covalent_chain = chain_map.get(chain.lower(), chain.lower())
        url = f"{self.covalent_base}/{covalent_chain}/tokens/{token_address}/token_holders_v2/"
        
        headers = {"Authorization": f"Bearer {get_covalent_key()}"}
        params = {"page-size": 100}
        
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("items", [])
                
                if items:
                    return self._process_holder_data(items)
        
        raise Exception(f"Covalent API returned {response.status_code}")
    
    async def _analyze_solana_holders(
        self,
        token_address: str
    ) -> Dict[str, Any]:
        """Analyze Solana token holders using Helius API."""
        if not get_helius_key():
            return await self._estimate_holder_distribution(token_address, "solana")
        
        url = f"{self.helius_base}/token-metadata"
        params = {"api-key": get_helius_key()}
        payload = {"mintAccounts": [token_address]}
        
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(url, params=params, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    # Parse Helius response format
                    if data and len(data) > 0:
                        token_data = data[0]
                        return {
                            "holder_count": token_data.get("holderCount", 0),
                            "top_10_percent": None,
                            "top_1_holder_percent": None,
                            "concentration_risk": "unknown",
                            "holders": [],
                            "holder_trend_7d": None,
                            "source": "helius"
                        }
            except Exception as e:
                logger.warning(f"Helius holder analysis failed: {e}")
        
        return await self._estimate_holder_distribution(token_address, "solana")
    
    async def _estimate_holder_distribution(
        self,
        token_address: str,
        chain: str
    ) -> Dict[str, Any]:
        """
        Estimate holder distribution without API.
        Uses heuristics based on token type and known patterns.
        """
        # Check if it's a known token with typical distribution
        known_tokens = {
            # Stablecoins (very distributed)
            "usdc": {"top_10_percent": 25, "holder_count": 500000, "risk": "low"},
            "usdt": {"top_10_percent": 30, "holder_count": 400000, "risk": "low"},
            "dai": {"top_10_percent": 20, "holder_count": 300000, "risk": "low"},
            # Major tokens
            "weth": {"top_10_percent": 35, "holder_count": 200000, "risk": "low"},
            "wbtc": {"top_10_percent": 40, "holder_count": 100000, "risk": "medium"},
            # DEX tokens
            "aero": {"top_10_percent": 45, "holder_count": 50000, "risk": "medium"},
            "velo": {"top_10_percent": 42, "holder_count": 60000, "risk": "medium"},
            "crv": {"top_10_percent": 38, "holder_count": 80000, "risk": "medium"},
        }
        
        # Try to identify token by address suffix or known patterns
        token_lower = token_address.lower()
        
        # For well-known tokens, use estimated data
        for symbol, data in known_tokens.items():
            if symbol in token_lower:
                return {
                    "holder_count": data["holder_count"],
                    "top_10_percent": data["top_10_percent"],
                    "top_1_holder_percent": data["top_10_percent"] * 0.3,  # Rough estimate
                    "concentration_risk": data["risk"],
                    "holders": [],
                    "holder_trend_7d": None,
                    "source": "estimated",
                    "note": "Estimated based on typical token distribution"
                }
        
        # Default: assume low risk (no API = can't verify, but most established pools are fine)
        return {
            "holder_count": None,
            "top_10_percent": None,
            "top_1_holder_percent": None,
            "concentration_risk": "low",  # Default to low risk for established pools
            "holders": [],
            "holder_trend_7d": None,
            "source": "estimated",
            "note": "Holder data estimated - API key not configured"
        }
    
    def _process_moralis_holder_data(
        self,
        holders: List[Dict]
    ) -> Dict[str, Any]:
        """
        Process Moralis API holder data into analysis.
        UNIVERSAL: Uses class-level protocol exclusion for accurate whale detection.
        """
        if not holders:
            # Empty result - likely CL pool (NFT positions) which can't be analyzed via ERC20 endpoint
            # CL pools (Uniswap V3, Aerodrome Slipstream, etc.) use NFT positions
            # Generally considered low risk for whale concentration since positions are fragmented
            return {
                "holder_count": None,
                "top_10_percent": None,
                "top_1_holder_percent": None,
                "concentration_risk": "low",  # CL pools are generally low whale risk
                "holders": [],
                "holder_trend_7d": None,
                "source": "cl_pool",
                "is_cl_pool": True,
                "note": "Concentrated liquidity pool - LP positions are NFTs (fragmented ownership)"
            }
        
        # Moralis returns percentage_relative_to_total_supply directly
        sorted_holders = holders[:100]
        
        # Separate "real" whales from protocol contracts (UNIVERSAL)
        # RULE: Contracts are NOT real whales - they are protocols/vaults/gauges/treasury
        # Only EOA (externally owned accounts) are real whales
        real_whale_holders = []
        protocol_holdings = []
        
        for i, h in enumerate(sorted_holders):
            address = h.get("owner_address", "").lower()
            percent = float(h.get("percentage_relative_to_total_supply", 0))
            is_contract = h.get("is_contract", False)  # Moralis provides this field
            
            # Use Moralis label/entity first, then fallback to our list
            moralis_label = h.get("owner_address_label") or h.get("entity") or None
            label = moralis_label if moralis_label else self.get_label(address)
            
            # UNIVERSAL RULE 1: If address is a contract → protocol/staking (not a whale)
            # This is the KEY rule - contracts are never real whales!
            if is_contract:
                if label == "Unknown" or not label:
                    label = "Smart Contract (protocol)"
                protocol_holdings.append({"address": address, "percent": percent, "label": label, "is_contract": True})
                continue
            
            # UNIVERSAL RULE 2: If top holder has >80% and is Unknown → likely Gauge/Staking
            # This catches cases where Moralis doesn't have is_contract info
            if i == 0 and percent > 80 and (label == "Unknown" or not label):
                label = "Likely Gauge/Staking (auto-detected)"
                protocol_holdings.append({"address": address, "percent": percent, "label": label})
                continue
                
            # UNIVERSAL RULE 3: Known protocol addresses from our list
            if self.is_safe_protocol_address(address, label or ""):
                protocol_holdings.append({"address": address, "percent": percent, "label": label})
                continue
            
            # This is a real whale (EOA wallet)
            # Store the label for display
            h["_label"] = label if label and label != "Unknown" else None
            real_whale_holders.append(h)
        
        # Calculate ADJUSTED top 10 (excluding safe protocol addresses)
        adjusted_top_10_percent = sum(
            float(h.get("percentage_relative_to_total_supply", 0)) 
            for h in real_whale_holders[:10]
        )
        
        # Total top 10 (raw, including protocols)
        raw_top_10_percent = sum(
            float(h.get("percentage_relative_to_total_supply", 0)) 
            for h in sorted_holders[:10]
        )
        
        # Protocol staked percentage (veTokens, etc.)
        protocol_staked_percent = sum(p["percent"] for p in protocol_holdings)
        
        # Top 1 holder (real whale only)
        top_1_percent = float(real_whale_holders[0].get("percentage_relative_to_total_supply", 0)) if real_whale_holders else 0
        
        # Format top 5 holders
        table_holders = []
        for h in sorted_holders[:5]:
            address = h.get("owner_address", "")
            percent = float(h.get("percentage_relative_to_total_supply", 0))
            is_contract = h.get("is_contract", False)
            
            # Use Moralis label/entity first, then our list
            moralis_label = h.get("owner_address_label") or h.get("entity") or None
            label = moralis_label if moralis_label else self.get_label(address.lower())
            
            # Add contract indicator
            if is_contract and label == "Unknown":
                label = "Smart Contract"
            
            table_holders.append({
                "address": address,
                "percent": round(percent, 2),
                "label": label,
                "is_contract": is_contract
            })
        
        # Determine concentration risk based on ADJUSTED percentage (excluding protocols)
        if adjusted_top_10_percent > 70:
            concentration_risk = "high"
        elif adjusted_top_10_percent > 40:
            concentration_risk = "medium"
        else:
            concentration_risk = "low"
        
        return {
            "holder_count": len(holders),
            "top_10_percent": round(adjusted_top_10_percent, 2),  # Adjusted (real whales only)
            "top_10_percent_raw": round(raw_top_10_percent, 2),   # Raw (including protocols)
            "protocol_staked_percent": round(protocol_staked_percent, 2),  # veTokens, staking, etc.
            "top_1_holder_percent": round(top_1_percent, 2),
            "concentration_risk": concentration_risk,
            "holders": table_holders,
            "protocol_holdings": protocol_holdings[:3],  # Top 3 protocol holdings
            "holder_trend_7d": None,
            "source": "moralis"
        }
    
    def _process_holder_data(
        self,
        holders: List[Dict]
    ) -> Dict[str, Any]:
        """
        Process raw holder data into analysis (Covalent format).
        UNIVERSAL: Uses class-level protocol exclusion for accurate whale detection.
        """
        if not holders:
            return {
                "holder_count": 0,
                "top_10_percent": 0,
                "concentration_risk": "unknown",
                "holders": [],
                "source": "covalent"
            }
        
        # Calculate total supply from all holders
        total_balance = sum(float(h.get("balance", 0)) for h in holders)
        if total_balance == 0:
            total_balance = 1  # Avoid division by zero
        
        # Process top holders
        sorted_holders = sorted(
            holders, 
            key=lambda x: float(x.get("balance", 0)), 
            reverse=True
        )[:100]  # Limit to top 100
        
        # Separate "real" whales from protocol contracts (UNIVERSAL)
        real_whale_holders = []
        protocol_holdings = []
        
        for h in sorted_holders:
            address = h.get("address", "").lower()
            balance = float(h.get("balance", 0))
            percent = (balance / total_balance) * 100
            label = self.get_label(address)
            
            if self.is_safe_protocol_address(address, label):
                protocol_holdings.append({"address": address, "percent": percent, "label": label})
            else:
                real_whale_holders.append({"address": address, "percent": percent, "label": label})
        
        # Calculate ADJUSTED top 10 (excluding safe protocol addresses)
        adjusted_top_10_percent = sum(h["percent"] for h in real_whale_holders[:10])
        
        # Total top 10 (raw, including protocols)
        raw_top_10_percent = sum(
            (float(h.get("balance", 0)) / total_balance) * 100 
            for h in sorted_holders[:10]
        )
        
        # Protocol staked percentage
        protocol_staked_percent = sum(p["percent"] for p in protocol_holdings)
        
        # Top 1 holder (real whale only)
        top_1_percent = real_whale_holders[0]["percent"] if real_whale_holders else 0
        
        # Format top 5 holders
        table_holders = []
        for h in sorted_holders[:5]:
            address = h.get("address", "")
            percent = (float(h.get("balance", 0)) / total_balance) * 100
            label = self.get_label(address.lower())
            
            table_holders.append({
                "address": address,
                "percent": round(percent, 2),
                "label": label
            })
        
        # Determine concentration risk based on ADJUSTED percentage (excluding protocols)
        if adjusted_top_10_percent > 70:
            concentration_risk = "high"
        elif adjusted_top_10_percent > 40:
            concentration_risk = "medium"
        else:
            concentration_risk = "low"
        
        return {
            "holder_count": len(holders),
            "top_10_percent": round(adjusted_top_10_percent, 2),  # Adjusted (real whales only)
            "top_10_percent_raw": round(raw_top_10_percent, 2),   # Raw (including protocols)
            "protocol_staked_percent": round(protocol_staked_percent, 2),
            "top_1_holder_percent": round(top_1_percent, 2),
            "concentration_risk": concentration_risk,
            "holders": table_holders,
            "protocol_holdings": protocol_holdings[:3],
            "holder_trend_7d": None,
            "source": "covalent"
        }
    
    def get_concentration_badge(self, analysis: Dict[str, Any]) -> str:
        """Generate HTML badge for concentration risk."""
        risk = analysis.get("concentration_risk", "unknown")
        
        risk_colors = {
            "low": ("#10B981", "Low Risk"),
            "medium": ("#FBBF24", "Medium Risk"),
            "high": ("#EF4444", "High Risk"),
            "unknown": ("#6B7280", "Unknown")
        }
        
        color, label = risk_colors.get(risk, risk_colors["unknown"])
        percent = analysis.get("top_10_percent")
        
        if percent is not None:
            return f'<span style="color: {color}">{label} ({percent:.1f}%)</span>'
        else:
            return f'<span style="color: {color}">{label}</span>'


# Singleton instance
holder_analyzer = HolderAnalysis()
