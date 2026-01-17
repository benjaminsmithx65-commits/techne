"""
Techne Contract Configuration
Centralized config for all contract addresses
Update here after deploying new contracts
"""

import os

# ============================================
# V2 CONTRACT (After deploy-v2.js)
# ============================================

# V2 CONTRACT - DEPLOYED!
AGENT_WALLET_V2_ADDRESS = os.environ.get(
    "AGENT_WALLET_V2_ADDRESS",
    "0x8df33b5b58212f16519ce86e810be2e8232df305"
)

# V1 Legacy (keep for reference)
AGENT_WALLET_V1_ADDRESS = "0x567D1Fc55459224132aB5148c6140E8900f9a607"

# Active version
AGENT_WALLET_ADDRESS = AGENT_WALLET_V2_ADDRESS

# ============================================
# TOKEN ADDRESSES (Base Mainnet)
# ============================================

TOKENS = {
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH": "0x4200000000000000000000000000000000000006",
    "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
    "USDbC": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
}

# ============================================
# PROTOCOL ADDRESSES (Base Mainnet)
# ============================================

PROTOCOLS = {
    # DEX
    "aerodrome_router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
    "aerodrome_factory": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
    
    # Lending
    "morpho_blue": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb",
    "aave_v3_pool": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
    "compound_v3_comet": "0x46e6b214b524310239732D51387075E0e70970bf",
    "moonwell_comptroller": "0xfBb21d0380bEE3312B33c4353c8936a0F13EF26C",
}

# ============================================
# CHAINLINK PRICE FEEDS (Base Mainnet)
# ============================================

PRICE_FEEDS = {
    "USDC/USD": "0x7e860098F58bBFC8648a4311b374B1D669a2bc6B",
    "ETH/USD": "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70",
}

# ============================================
# RPC CONFIGURATION
# ============================================

RPC_URL = os.environ.get(
    "ALCHEMY_RPC_URL",
    "https://base-mainnet.g.alchemy.com/v2/AqxI9okL6ZYv38MBFDHhb"
)

# ============================================
# V2 CONTRACT ABI (Key functions)
# ============================================

WALLET_V2_ABI = [
    # Core
    {"inputs": [{"name": "amount", "type": "uint256"}], "name": "deposit", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "token", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "depositToken", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "shares", "type": "uint256"}], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    
    # LP Operations
    {"inputs": [{"name": "tokenB", "type": "address"}, {"name": "usdcAmount", "type": "uint256"}, {"name": "stable", "type": "bool"}], "name": "enterLPPosition", "outputs": [{"type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    
    # View
    {"inputs": [], "name": "totalValue", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalShares", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "user", "type": "address"}], "name": "getUserValue", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "user", "type": "address"}], "name": "getUserShares", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    
    # Security view
    {"inputs": [], "name": "circuitBreakerTriggered", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "emergencyMode", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "paused", "outputs": [{"type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "checkUSDCPeg", "outputs": [{"name": "pegged", "type": "bool"}, {"name": "price", "type": "int256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "getWithdrawLimitStatus", "outputs": [{"name": "remaining", "type": "uint256"}, {"name": "dailyLimit", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]


def get_contract_address():
    """Get current active contract address"""
    return AGENT_WALLET_ADDRESS


def get_token_address(symbol: str) -> str:
    """Get token address by symbol"""
    return TOKENS.get(symbol.upper(), None)


def get_protocol_address(name: str) -> str:
    """Get protocol address by name"""
    return PROTOCOLS.get(name.lower(), None)
