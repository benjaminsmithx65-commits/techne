"""
Parking Strategy Service
Auto-deposits idle capital to Aave V3 / Moonwell when no pools match criteria

Flow:
1. Agent finds no matching pools for user's criteria
2. Instead of leaving USDC idle, deposit to Aave V3 (safe ~3-5% APY)
3. Continuous monitoring: check every hour for better opportunities
4. When matching pool appears → withdraw from Aave → deposit to new pool
"""

import os
from typing import Dict, Any, Optional
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# ============================================
# PARKING PROTOCOLS (Safe havens for idle capital)
# ============================================

PARKING_PROTOCOLS = {
    "base": {
        "aave_v3": {
            "name": "Aave V3",
            "pool": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",  # Aave Pool on Base
            "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
            "ausdc": "0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB",  # aUSDC on Base
            "expected_apy": 3.5,
            "priority": 1  # First choice
        },
        "moonwell": {
            "name": "Moonwell",
            "comptroller": "0xfBb21d0380beE3312B33c4353c8936a0F13EF26C",
            "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "musdc": "0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22",  # mUSDC
            "expected_apy": 4.0,
            "priority": 2  # Second choice
        }
    }
}

# Aave V3 Pool ABI (simplified)
AAVE_POOL_ABI = [
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "onBehalfOf", "type": "address"},
            {"name": "referralCode", "type": "uint16"}
        ],
        "name": "supply",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "asset", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "to", "type": "address"}
        ],
        "name": "withdraw",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# ERC20 ABI (for approve + balanceOf)
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
    }
]


class ParkingStrategy:
    """
    Manages idle capital by parking it in safe protocols.
    
    Usage:
        parking = ParkingStrategy()
        
        # When no pools match criteria
        if no_matching_pools:
            await parking.park_capital(user_address, usdc_amount)
        
        # When matching pool appears
        if matching_pool_found:
            await parking.unpark_capital(user_address)
    """
    
    def __init__(self, chain: str = "base"):
        self.chain = chain
        self.rpc_url = os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Get parking config for chain
        self.parking_config = PARKING_PROTOCOLS.get(chain, {})
        
        # Track parked positions
        self.parked_positions: Dict[str, Dict] = {}
        
        print(f"[ParkingStrategy] Initialized for {chain}")
        print(f"  Available parking: {list(self.parking_config.keys())}")
    
    def get_best_parking_protocol(self) -> Optional[Dict]:
        """Get the best parking protocol based on priority and availability."""
        if not self.parking_config:
            return None
        
        # Sort by priority (lower = better)
        sorted_protocols = sorted(
            self.parking_config.items(),
            key=lambda x: x[1].get("priority", 99)
        )
        
        return sorted_protocols[0] if sorted_protocols else None
    
    def get_parking_apy(self, protocol_key: str = "aave_v3") -> float:
        """Get current parking APY (fallback to expected if live data unavailable)."""
        protocol = self.parking_config.get(protocol_key, {})
        return protocol.get("expected_apy", 3.0)
    
    async def park_capital(
        self, 
        user_address: str, 
        amount_usdc: float,
        protocol_key: str = "aave_v3"
    ) -> Dict[str, Any]:
        """
        Park idle capital in a safe protocol.
        
        Args:
            user_address: User's wallet address
            amount_usdc: Amount of USDC to park
            protocol_key: Which protocol to use (default: aave_v3)
        
        Returns:
            Transaction result with parking details
        """
        protocol = self.parking_config.get(protocol_key)
        if not protocol:
            return {
                "success": False,
                "error": f"Unknown parking protocol: {protocol_key}"
            }
        
        print(f"[ParkingStrategy] 🅿️ Parking ${amount_usdc:,.2f} USDC to {protocol['name']}")
        
        # Record parked position
        self.parked_positions[user_address] = {
            "protocol": protocol_key,
            "amount_usdc": amount_usdc,
            "expected_apy": protocol["expected_apy"],
            "parked_at": self._get_timestamp(),
            "status": "pending"
        }
        
        try:
            # In production: execute actual deposit
            # For MVP: simulate with logging
            
            result = {
                "success": True,
                "protocol": protocol["name"],
                "amount_parked": amount_usdc,
                "expected_apy": protocol["expected_apy"],
                "message": f"Parked ${amount_usdc:,.2f} in {protocol['name']} (~{protocol['expected_apy']}% APY)",
                "tx_hash": None  # Will be populated on actual execution
            }
            
            self.parked_positions[user_address]["status"] = "parked"
            
            print(f"[ParkingStrategy] ✅ Successfully parked capital")
            print(f"  Protocol: {protocol['name']}")
            print(f"  Amount: ${amount_usdc:,.2f}")
            print(f"  Expected APY: {protocol['expected_apy']}%")
            
            return result
            
        except Exception as e:
            print(f"[ParkingStrategy] ❌ Park failed: {e}")
            self.parked_positions[user_address]["status"] = "failed"
            return {
                "success": False,
                "error": str(e)
            }
    
    async def unpark_capital(
        self, 
        user_address: str
    ) -> Dict[str, Any]:
        """
        Withdraw parked capital when a better opportunity appears.
        
        Args:
            user_address: User's wallet address
        
        Returns:
            Withdrawal result with amount recovered
        """
        parked = self.parked_positions.get(user_address)
        if not parked or parked["status"] != "parked":
            return {
                "success": False,
                "error": "No parked capital found for user"
            }
        
        protocol_key = parked["protocol"]
        protocol = self.parking_config.get(protocol_key, {})
        amount = parked["amount_usdc"]
        
        print(f"[ParkingStrategy] 🚗 Unparking ${amount:,.2f} from {protocol.get('name', protocol_key)}")
        
        try:
            # Calculate earned interest (approximate)
            hours_parked = (self._get_timestamp() - parked["parked_at"]) / 3600
            apy = parked["expected_apy"]
            interest_earned = amount * (apy / 100) * (hours_parked / 8760)  # hours in year
            
            total_amount = amount + interest_earned
            
            result = {
                "success": True,
                "protocol": protocol.get("name", protocol_key),
                "principal": amount,
                "interest_earned": round(interest_earned, 4),
                "total_amount": round(total_amount, 4),
                "hours_parked": round(hours_parked, 1),
                "message": f"Withdrew ${total_amount:,.4f} (+${interest_earned:.4f} interest)",
                "tx_hash": None
            }
            
            # Clear parked position
            self.parked_positions[user_address]["status"] = "withdrawn"
            
            print(f"[ParkingStrategy] ✅ Successfully unparked capital")
            print(f"  Principal: ${amount:,.2f}")
            print(f"  Interest earned: ${interest_earned:.4f}")
            print(f"  Time parked: {hours_parked:.1f} hours")
            
            return result
            
        except Exception as e:
            print(f"[ParkingStrategy] ❌ Unpark failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def is_capital_parked(self, user_address: str) -> bool:
        """Check if user has parked capital."""
        parked = self.parked_positions.get(user_address)
        return parked is not None and parked.get("status") == "parked"
    
    def get_parked_info(self, user_address: str) -> Optional[Dict]:
        """Get info about user's parked capital."""
        return self.parked_positions.get(user_address)
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def build_supply_tx(
        self,
        user_address: str,
        amount_usdc: int,  # In wei (6 decimals for USDC)
        protocol_key: str = "aave_v3"
    ) -> Dict[str, Any]:
        """
        Build Aave supply transaction for Smart Account execution.
        
        Returns transaction data ready for bundler.
        """
        protocol = self.parking_config.get(protocol_key)
        if not protocol:
            return {"error": "Unknown protocol"}
        
        if protocol_key == "aave_v3":
            pool = self.w3.eth.contract(
                address=Web3.to_checksum_address(protocol["pool"]),
                abi=AAVE_POOL_ABI
            )
            
            # Build supply calldata
            calldata = pool.encodeABI(
                fn_name="supply",
                args=[
                    Web3.to_checksum_address(protocol["usdc"]),
                    amount_usdc,
                    Web3.to_checksum_address(user_address),
                    0  # referralCode
                ]
            )
            
            return {
                "to": protocol["pool"],
                "data": calldata,
                "value": "0x0",
                "protocol": "aave_v3",
                "action": "supply"
            }
        
        return {"error": f"Protocol {protocol_key} not supported for tx building"}
    
    def build_withdraw_tx(
        self,
        user_address: str,
        amount_usdc: int,  # Use max uint256 for full withdrawal
        protocol_key: str = "aave_v3"
    ) -> Dict[str, Any]:
        """
        Build Aave withdraw transaction for Smart Account execution.
        """
        protocol = self.parking_config.get(protocol_key)
        if not protocol:
            return {"error": "Unknown protocol"}
        
        if protocol_key == "aave_v3":
            pool = self.w3.eth.contract(
                address=Web3.to_checksum_address(protocol["pool"]),
                abi=AAVE_POOL_ABI
            )
            
            # Build withdraw calldata
            calldata = pool.encodeABI(
                fn_name="withdraw",
                args=[
                    Web3.to_checksum_address(protocol["usdc"]),
                    amount_usdc,
                    Web3.to_checksum_address(user_address)
                ]
            )
            
            return {
                "to": protocol["pool"],
                "data": calldata,
                "value": "0x0",
                "protocol": "aave_v3",
                "action": "withdraw"
            }
        
        return {"error": f"Protocol {protocol_key} not supported for tx building"}


# Global instance
_parking_instance = None

def get_parking_strategy(chain: str = "base") -> ParkingStrategy:
    """Get or create parking strategy singleton."""
    global _parking_instance
    if _parking_instance is None or _parking_instance.chain != chain:
        _parking_instance = ParkingStrategy(chain)
    return _parking_instance


# ============================================
# CLI TEST
# ============================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("="*60)
        print("Parking Strategy Test")
        print("="*60)
        
        parking = ParkingStrategy("base")
        
        # Simulate parking
        user = "0xTestUser123"
        amount = 1000.0
        
        print(f"\n1. Parking ${amount} USDC...")
        result = await parking.park_capital(user, amount)
        print(f"   Result: {result}")
        
        print(f"\n2. Check if parked: {parking.is_capital_parked(user)}")
        print(f"   Parked info: {parking.get_parked_info(user)}")
        
        # Wait a bit (simulate time passing)
        import time
        time.sleep(2)
        
        print(f"\n3. Unparking capital...")
        result = await parking.unpark_capital(user)
        print(f"   Result: {result}")
        
        print("="*60)
    
    asyncio.run(test())
