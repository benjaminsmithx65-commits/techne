"""
Morpho Blue Protocol Integration for Base Network
Handles deposits (supply), withdrawals, and partial withdrawals for Techne Finance.

Morpho Blue is a trustless lending primitive with isolated markets.
Each market has: loanToken, collateralToken, oracle, irm, lltv
"""
import logging
import requests
from typing import Optional, Dict, Any, List
from web3 import Web3
from eth_account import Account
import os

logger = logging.getLogger(__name__)

# ==========================================
# MORPHO BLUE ADDRESSES ON BASE
# ==========================================
MORPHO_BLUE = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"  # Main Morpho contract
USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"

# Morpho API for market discovery
MORPHO_API_URL = "https://blue-api.morpho.org/graphql"

# ==========================================
# MORPHO BLUE ABI (minimal for supply/withdraw)
# ==========================================
MORPHO_ABI = [
    # supply(MarketParams memory marketParams, uint256 assets, uint256 shares, address onBehalf, bytes memory data)
    {
        "inputs": [
            {
                "components": [
                    {"name": "loanToken", "type": "address"},
                    {"name": "collateralToken", "type": "address"},
                    {"name": "oracle", "type": "address"},
                    {"name": "irm", "type": "address"},
                    {"name": "lltv", "type": "uint256"}
                ],
                "name": "marketParams",
                "type": "tuple"
            },
            {"name": "assets", "type": "uint256"},
            {"name": "shares", "type": "uint256"},
            {"name": "onBehalf", "type": "address"},
            {"name": "data", "type": "bytes"}
        ],
        "name": "supply",
        "outputs": [
            {"name": "assetsSupplied", "type": "uint256"},
            {"name": "sharesSupplied", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # withdraw(MarketParams memory marketParams, uint256 assets, uint256 shares, address onBehalf, address receiver)
    {
        "inputs": [
            {
                "components": [
                    {"name": "loanToken", "type": "address"},
                    {"name": "collateralToken", "type": "address"},
                    {"name": "oracle", "type": "address"},
                    {"name": "irm", "type": "address"},
                    {"name": "lltv", "type": "uint256"}
                ],
                "name": "marketParams",
                "type": "tuple"
            },
            {"name": "assets", "type": "uint256"},
            {"name": "shares", "type": "uint256"},
            {"name": "onBehalf", "type": "address"},
            {"name": "receiver", "type": "address"}
        ],
        "name": "withdraw",
        "outputs": [
            {"name": "assetsWithdrawn", "type": "uint256"},
            {"name": "sharesWithdrawn", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    # position(bytes32 id, address user) -> (uint256 supplyShares, uint128 borrowShares, uint128 collateral)
    {
        "inputs": [
            {"name": "id", "type": "bytes32"},
            {"name": "user", "type": "address"}
        ],
        "name": "position",
        "outputs": [
            {"name": "supplyShares", "type": "uint256"},
            {"name": "borrowShares", "type": "uint128"},
            {"name": "collateral", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    # market(bytes32 id) -> Market struct
    {
        "inputs": [{"name": "id", "type": "bytes32"}],
        "name": "market",
        "outputs": [
            {"name": "totalSupplyAssets", "type": "uint128"},
            {"name": "totalSupplyShares", "type": "uint128"},
            {"name": "totalBorrowAssets", "type": "uint128"},
            {"name": "totalBorrowShares", "type": "uint128"},
            {"name": "lastUpdate", "type": "uint128"},
            {"name": "fee", "type": "uint128"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    # idToMarketParams(bytes32 id) -> MarketParams
    {
        "inputs": [{"name": "id", "type": "bytes32"}],
        "name": "idToMarketParams",
        "outputs": [
            {
                "components": [
                    {"name": "loanToken", "type": "address"},
                    {"name": "collateralToken", "type": "address"},
                    {"name": "oracle", "type": "address"},
                    {"name": "irm", "type": "address"},
                    {"name": "lltv", "type": "uint256"}
                ],
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI for approvals and balance checks
ERC20_ABI = [
    {
        "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class MorphoBlueProtocol:
    """
    Morpho Blue Protocol handler for Base network.
    Supports supply, withdraw, and partial withdraw operations.
    """
    
    def __init__(self, rpc_url: Optional[str] = None):
        """Initialize with RPC connection."""
        self.rpc_url = rpc_url or os.getenv("ALCHEMY_RPC_URL") or os.getenv("BASE_RPC_URL") or "https://mainnet.base.org"
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        if not self.w3.is_connected():
            logger.warning(f"[MorphoBlue] Failed to connect to RPC: {self.rpc_url}")
        else:
            logger.info(f"[MorphoBlue] Connected to Base via {self.rpc_url[:30]}...")
        
        # Contract instances
        self.morpho = self.w3.eth.contract(
            address=Web3.to_checksum_address(MORPHO_BLUE),
            abi=MORPHO_ABI
        )
        self.usdc = self.w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI
        )
        
        # Cache for market data
        self._markets_cache = None
        self._cache_timestamp = 0
    
    def get_markets_from_api(self) -> List[Dict]:
        """
        Fetch Morpho Blue markets from the API.
        Returns list of markets with APY, TVL, and market params.
        """
        query = """
        query {
            markets(where: { chainId_in: [8453] }) {
                items {
                    id
                    uniqueKey
                    loanAsset {
                        address
                        symbol
                        decimals
                    }
                    collateralAsset {
                        address
                        symbol
                    }
                    state {
                        supplyAssets
                        borrowAssets
                        supplyApy
                        borrowApy
                        utilization
                    }
                    oracle {
                        address
                    }
                    irmAddress
                    lltv
                }
            }
        }
        """
        
        try:
            response = requests.post(
                MORPHO_API_URL,
                json={"query": query},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                markets = data.get("data", {}).get("markets", {}).get("items", [])
                logger.info(f"[MorphoBlue] Fetched {len(markets)} markets from API")
                return markets
            else:
                logger.warning(f"[MorphoBlue] API returned status {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"[MorphoBlue] API error: {e}")
            return []
    
    def get_usdc_markets(self) -> List[Dict]:
        """
        Get all USDC lending markets on Base.
        Returns formatted market data suitable for pool discovery.
        """
        markets = self.get_markets_from_api()
        usdc_markets = []
        
        for m in markets:
            loan_asset = m.get("loanAsset", {})
            if loan_asset.get("symbol") == "USDC":
                state = m.get("state", {})
                collateral = m.get("collateralAsset", {})
                
                # Calculate APY (API returns as decimal, convert to %)
                supply_apy = float(state.get("supplyApy", 0)) * 100
                
                # Calculate TVL from supply assets
                supply_assets = int(state.get("supplyAssets", 0))
                decimals = loan_asset.get("decimals", 6)
                tvl = supply_assets / (10 ** decimals)
                
                usdc_markets.append({
                    "id": m.get("uniqueKey"),
                    "market_id": m.get("id"),
                    "asset": "USDC",
                    "collateral": collateral.get("symbol", "Unknown"),
                    "apy": round(supply_apy, 2),
                    "tvl": tvl,
                    "utilization": float(state.get("utilization", 0)) * 100,
                    "borrow_apy": float(state.get("borrowApy", 0)) * 100,
                    "oracle": m.get("oracle", {}).get("address"),
                    "irm": m.get("irmAddress"),
                    "lltv": int(m.get("lltv", 0)) / 1e18 * 100,  # Convert to %
                    "project": "morpho-blue",
                    "chain": "Base",
                    "pool_type": "single",
                    "risk_level": "medium"
                })
        
        # Sort by APY descending
        usdc_markets.sort(key=lambda x: x["apy"], reverse=True)
        logger.info(f"[MorphoBlue] Found {len(usdc_markets)} USDC markets")
        return usdc_markets
    
    def get_best_usdc_market(self) -> Optional[Dict]:
        """Get the best (highest APY) USDC market."""
        markets = self.get_usdc_markets()
        if markets:
            return markets[0]
        return None
    
    def get_market_params_by_id(self, market_id: bytes) -> Dict:
        """Get market params from on-chain by market ID."""
        try:
            params = self.morpho.functions.idToMarketParams(market_id).call()
            return {
                "loanToken": params[0],
                "collateralToken": params[1],
                "oracle": params[2],
                "irm": params[3],
                "lltv": params[4]
            }
        except Exception as e:
            logger.error(f"[MorphoBlue] Failed to get market params: {e}")
            return {}
    
    def get_position(self, user_address: str, market_id: bytes) -> Dict:
        """Get user's position in a specific market."""
        try:
            user = Web3.to_checksum_address(user_address)
            position = self.morpho.functions.position(market_id, user).call()
            
            return {
                "supply_shares": position[0],
                "borrow_shares": position[1],
                "collateral": position[2]
            }
        except Exception as e:
            logger.error(f"[MorphoBlue] Failed to get position: {e}")
            return {"supply_shares": 0, "borrow_shares": 0, "collateral": 0}
    
    def get_market_state(self, market_id: bytes) -> Dict:
        """Get market state (totals) from on-chain."""
        try:
            state = self.morpho.functions.market(market_id).call()
            return {
                "total_supply_assets": state[0],
                "total_supply_shares": state[1],
                "total_borrow_assets": state[2],
                "total_borrow_shares": state[3],
                "last_update": state[4],
                "fee": state[5]
            }
        except Exception as e:
            logger.error(f"[MorphoBlue] Failed to get market state: {e}")
            return {}
    
    def shares_to_assets(self, shares: int, market_id: bytes) -> int:
        """Convert supply shares to asset amount."""
        state = self.get_market_state(market_id)
        if not state or state.get("total_supply_shares", 0) == 0:
            return shares
        
        total_assets = state["total_supply_assets"]
        total_shares = state["total_supply_shares"]
        
        return (shares * total_assets) // total_shares
    
    def get_usdc_balance(self, user_address: str) -> int:
        """Get USDC balance in wei (6 decimals)."""
        user = Web3.to_checksum_address(user_address)
        return self.usdc.functions.balanceOf(user).call()
    
    def build_approve_tx(
        self,
        user_address: str,
        amount: int,
        nonce: Optional[int] = None
    ) -> Dict:
        """Build USDC approval transaction for Morpho."""
        user = Web3.to_checksum_address(user_address)
        
        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(user)
        
        tx = self.usdc.functions.approve(
            MORPHO_BLUE,
            amount
        ).build_transaction({
            "from": user,
            "nonce": nonce,
            "gas": 60000,
            "maxFeePerGas": self.w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei"),
            "chainId": 8453
        })
        
        return tx
    
    def build_supply_tx(
        self,
        user_address: str,
        amount: int,
        market_params: Dict,
        nonce: Optional[int] = None
    ) -> Dict:
        """
        Build supply transaction for Morpho Blue.
        
        Args:
            user_address: User wallet address
            amount: Amount of USDC to supply (6 decimals)
            market_params: Dict with loanToken, collateralToken, oracle, irm, lltv
            nonce: Optional nonce override
        """
        user = Web3.to_checksum_address(user_address)
        
        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(user)
        
        # MarketParams tuple
        params_tuple = (
            Web3.to_checksum_address(market_params["loanToken"]),
            Web3.to_checksum_address(market_params["collateralToken"]),
            Web3.to_checksum_address(market_params["oracle"]),
            Web3.to_checksum_address(market_params["irm"]),
            int(market_params["lltv"])
        )
        
        tx = self.morpho.functions.supply(
            params_tuple,
            amount,      # assets
            0,           # shares (0 = use assets)
            user,        # onBehalf
            b""          # data
        ).build_transaction({
            "from": user,
            "nonce": nonce,
            "gas": 250000,
            "maxFeePerGas": self.w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei"),
            "chainId": 8453
        })
        
        return tx
    
    def build_withdraw_tx(
        self,
        user_address: str,
        amount: int,
        market_params: Dict,
        nonce: Optional[int] = None
    ) -> Dict:
        """
        Build withdraw transaction for Morpho Blue.
        
        Args:
            user_address: User wallet address  
            amount: Amount of USDC to withdraw (6 decimals), use 0 + shares for full
            market_params: Dict with loanToken, collateralToken, oracle, irm, lltv
            nonce: Optional nonce override
        """
        user = Web3.to_checksum_address(user_address)
        
        if nonce is None:
            nonce = self.w3.eth.get_transaction_count(user)
        
        params_tuple = (
            Web3.to_checksum_address(market_params["loanToken"]),
            Web3.to_checksum_address(market_params["collateralToken"]),
            Web3.to_checksum_address(market_params["oracle"]),
            Web3.to_checksum_address(market_params["irm"]),
            int(market_params["lltv"])
        )
        
        tx = self.morpho.functions.withdraw(
            params_tuple,
            amount,      # assets
            0,           # shares (0 = use assets)
            user,        # onBehalf
            user         # receiver
        ).build_transaction({
            "from": user,
            "nonce": nonce,
            "gas": 250000,
            "maxFeePerGas": self.w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": self.w3.to_wei(0.001, "gwei"),
            "chainId": 8453
        })
        
        return tx
    
    def supply(
        self,
        user_address: str,
        amount: int,
        market_params: Dict,
        private_key: str
    ) -> Dict:
        """
        Execute supply to Morpho Blue market.
        
        Args:
            user_address: User wallet address
            amount: Amount of USDC to supply (6 decimals)
            market_params: Market parameters
            private_key: Private key for signing
            
        Returns:
            Dict with tx_hash and status
        """
        try:
            user = Web3.to_checksum_address(user_address)
            nonce = self.w3.eth.get_transaction_count(user)
            
            # Check allowance
            allowance = self.usdc.functions.allowance(user, MORPHO_BLUE).call()
            
            if allowance < amount:
                logger.info(f"[MorphoBlue] Approving USDC for Morpho...")
                approve_tx = self.build_approve_tx(user, amount * 10, nonce)
                signed_approve = self.w3.eth.account.sign_transaction(approve_tx, private_key)
                approve_hash = self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
                self.w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
                logger.info(f"[MorphoBlue] Approval tx: {approve_hash.hex()}")
                nonce += 1
            
            # Supply
            supply_tx = self.build_supply_tx(user, amount, market_params, nonce)
            signed_supply = self.w3.eth.account.sign_transaction(supply_tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_supply.raw_transaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt.gasUsed,
                "amount": amount,
                "protocol": "morpho-blue"
            }
            
        except Exception as e:
            logger.error(f"[MorphoBlue] Supply failed: {e}")
            return {"success": False, "error": str(e)}
    
    def withdraw(
        self,
        user_address: str,
        amount: int,
        market_params: Dict,
        private_key: str
    ) -> Dict:
        """
        Execute withdraw from Morpho Blue market.
        
        Args:
            user_address: User wallet address
            amount: Amount of USDC to withdraw (6 decimals)
            market_params: Market parameters
            private_key: Private key for signing
            
        Returns:
            Dict with tx_hash and status
        """
        try:
            user = Web3.to_checksum_address(user_address)
            
            withdraw_tx = self.build_withdraw_tx(user, amount, market_params)
            signed_tx = self.w3.eth.account.sign_transaction(withdraw_tx, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            return {
                "success": receipt.status == 1,
                "tx_hash": tx_hash.hex(),
                "gas_used": receipt.gasUsed,
                "amount": amount,
                "protocol": "morpho-blue"
            }
            
        except Exception as e:
            logger.error(f"[MorphoBlue] Withdraw failed: {e}")
            return {"success": False, "error": str(e)}
    
    def withdraw_percent(
        self,
        user_address: str,
        percent: int,
        market_id: bytes,
        market_params: Dict,
        private_key: str
    ) -> Dict:
        """
        Withdraw a percentage of the user's position.
        
        Args:
            user_address: User wallet address
            percent: Percentage to withdraw (1-100)
            market_id: Market ID bytes32
            market_params: Market parameters
            private_key: Private key for signing
            
        Returns:
            Dict with tx_hash and status
        """
        try:
            position = self.get_position(user_address, market_id)
            supply_shares = position.get("supply_shares", 0)
            
            if supply_shares == 0:
                return {"success": False, "error": "No position to withdraw"}
            
            # Calculate asset amount from shares
            total_assets = self.shares_to_assets(supply_shares, market_id)
            withdraw_amount = (total_assets * percent) // 100
            
            if withdraw_amount == 0:
                return {"success": False, "error": "Amount too small"}
            
            logger.info(f"[MorphoBlue] Withdrawing {percent}%: {withdraw_amount / 1e6:.2f} USDC")
            
            return self.withdraw(user_address, withdraw_amount, market_params, private_key)
            
        except Exception as e:
            logger.error(f"[MorphoBlue] Partial withdraw failed: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_morpho_instance = None

def get_morpho_protocol() -> MorphoBlueProtocol:
    """Get singleton Morpho Blue protocol instance."""
    global _morpho_instance
    if _morpho_instance is None:
        _morpho_instance = MorphoBlueProtocol()
    return _morpho_instance


# CLI testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    morpho = get_morpho_protocol()
    
    print("\n=== Morpho Blue Markets (Base) ===")
    markets = morpho.get_usdc_markets()
    
    for m in markets[:5]:
        print(f"  {m['collateral']:10} | APY: {m['apy']:6.2f}% | TVL: ${m['tvl']:,.0f} | Util: {m['utilization']:.1f}%")
    
    print(f"\nTotal USDC markets: {len(markets)}")
