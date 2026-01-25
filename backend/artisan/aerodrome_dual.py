"""
Aerodrome Dual-Sided LP Calldata Builder

Builds calldata for atomic dual LP deposits using WETH-first strategy:
1. swap(USDC → WETH) - deep liquidity
2. swap(50% WETH → target token)
3. addLiquidity(WETH + target)

This module generates calldata for TechneAgentWallet.executeRebalance()
"""

import os
from typing import Dict, List, Tuple, Any, Optional
from web3 import Web3
from datetime import datetime

# ============================================
# CONSTANTS
# ============================================

# Aerodrome on Base mainnet
AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
AERODROME_FACTORY = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"

# Common tokens on Base
TOKENS = {
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH": "0x4200000000000000000000000000000000000006",
    "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    "cbETH": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
    "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
    "VIRTUALS": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
}

# Function selectors (must match setup_smart_account.py)
SELECTORS = {
    "approve": "0x095ea7b3",
    "swapExactTokensForTokens": "0xcac88ea9",  # Aerodrome uses Route[] struct
    "addLiquidity": "0x5a47ddc3",
    "removeLiquidity": "0xbaa2abde",
}

# Router ABI for encoding
ROUTER_ABI = [
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"components": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "stable", "type": "bool"},
                {"name": "factory", "type": "address"}
            ], "name": "routes", "type": "tuple[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "tokenA", "type": "address"},
            {"name": "tokenB", "type": "address"},
            {"name": "stable", "type": "bool"},
            {"name": "amountADesired", "type": "uint256"},
            {"name": "amountBDesired", "type": "uint256"},
            {"name": "amountAMin", "type": "uint256"},
            {"name": "amountBMin", "type": "uint256"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "addLiquidity",
        "outputs": [
            {"name": "amountA", "type": "uint256"},
            {"name": "amountB", "type": "uint256"},
            {"name": "liquidity", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"components": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "stable", "type": "bool"},
                {"name": "factory", "type": "address"}
            ], "name": "routes", "type": "tuple[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 ABI for approve
ERC20_ABI = [
    {
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


class AerodromeDualLPBuilder:
    """
    Build calldata for dual-sided LP deposits on Aerodrome.
    
    Usage:
        builder = AerodromeDualLPBuilder(rpc_url)
        steps = await builder.build_dual_lp_flow(
            usdc_amount=1000 * 10**6,
            target_pair="WETH/VIRTUALS",
            recipient="0x...",
            slippage=0.5
        )
        
        # steps contains list of {protocol, calldata, description} dicts
        for step in steps:
            await agent.execute_rebalance(step['protocol'], step['calldata'])
    """
    
    def __init__(self, rpc_url: str = None):
        rpc = rpc_url or os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(rpc))
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(AERODROME_ROUTER),
            abi=ROUTER_ABI
        )
        
    def _get_token_address(self, symbol: str) -> str:
        """Get token address from symbol"""
        symbol = symbol.upper().strip()
        if symbol not in TOKENS:
            # Assume it's already an address
            if symbol.startswith("0x") and len(symbol) == 42:
                return Web3.to_checksum_address(symbol)
            raise ValueError(f"Unknown token: {symbol}")
        return Web3.to_checksum_address(TOKENS[symbol])
    
    def get_swap_quote(self, from_token: str, to_token: str, amount: int) -> int:
        """Get swap quote from Aerodrome router"""
        try:
            from_addr = self._get_token_address(from_token)
            to_addr = self._get_token_address(to_token)
            
            # Routes as tuple format for web3.py: (from, to, stable, factory)
            route = [(
                from_addr,
                to_addr,
                False,  # Volatile by default
                Web3.to_checksum_address(AERODROME_FACTORY)
            )]
            
            amounts = self.router.functions.getAmountsOut(amount, route).call()
            return amounts[-1]
        except Exception as e:
            print(f"[AerodromeDualLP] Quote error: {e}")
            return 0
    
    def build_approve_calldata(self, token: str, spender: str, amount: int) -> bytes:
        """Build ERC20 approve calldata"""
        token_addr = self._get_token_address(token)
        token_contract = self.w3.eth.contract(
            address=token_addr,
            abi=ERC20_ABI
        )
        return token_contract.functions.approve(
            Web3.to_checksum_address(spender),
            amount
        )._encode_transaction_data()
    
    def build_swap_calldata(
        self,
        token_in: str,
        token_out: str,
        amount_in: int,
        amount_out_min: int,
        recipient: str,
        deadline: int = None,
        stable: bool = False
    ) -> bytes:
        """Build swapExactTokensForTokens calldata"""
        if deadline is None:
            deadline = int(datetime.utcnow().timestamp()) + 1200  # 20 min
            
        from_addr = self._get_token_address(token_in)
        to_addr = self._get_token_address(token_out)
        
        # Routes as tuple format: (from, to, stable, factory)
        routes = [(
            from_addr,
            to_addr,
            stable,
            Web3.to_checksum_address(AERODROME_FACTORY)
        )]
        
        return self.router.functions.swapExactTokensForTokens(
            amount_in,
            amount_out_min,
            routes,
            Web3.to_checksum_address(recipient),
            deadline
        )._encode_transaction_data()
    
    def build_add_liquidity_calldata(
        self,
        token_a: str,
        token_b: str,
        amount_a: int,
        amount_b: int,
        recipient: str,
        slippage: float = 0.5,  # 0.5%
        deadline: int = None,
        stable: bool = False
    ) -> bytes:
        """Build addLiquidity calldata"""
        if deadline is None:
            deadline = int(datetime.utcnow().timestamp()) + 1200
            
        token_a_addr = self._get_token_address(token_a)
        token_b_addr = self._get_token_address(token_b)
        
        slippage_mult = (100 - slippage) / 100
        min_a = int(amount_a * slippage_mult)
        min_b = int(amount_b * slippage_mult)
        
        return self.router.functions.addLiquidity(
            token_a_addr,
            token_b_addr,
            stable,
            amount_a,
            amount_b,
            min_a,
            min_b,
            Web3.to_checksum_address(recipient),
            deadline
        )._encode_transaction_data()
    
    async def build_dual_lp_flow(
        self,
        usdc_amount: int,
        target_pair: str,
        recipient: str,
        slippage: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Build complete 3-step LP flow with WETH-first strategy.
        
        Args:
            usdc_amount: Amount of USDC (6 decimals)
            target_pair: LP pair like "WETH/VIRTUALS" or "WETH/AERO"
            recipient: Address to receive LP tokens
            slippage: Slippage tolerance in % (default 0.5%)
            
        Returns:
            List of step dicts with {protocol, calldata, description, token}
        """
        # Parse target pair
        tokens = [t.strip().upper() for t in target_pair.replace(" ", "").split("/")]
        if len(tokens) != 2:
            raise ValueError(f"Invalid pair format: {target_pair}")
        
        # Ensure WETH is token A
        if "WETH" not in tokens:
            raise ValueError(f"WETH-first strategy requires WETH in pair. Got: {target_pair}")
        
        target_token = tokens[1] if tokens[0] == "WETH" else tokens[0]
        
        deadline = int(datetime.utcnow().timestamp()) + 1200
        slippage_mult = (100 - slippage) / 100
        
        steps = []
        
        # ==========================================
        # Step 0: Approve USDC for Router
        # ==========================================
        approve_usdc = self.build_approve_calldata("USDC", AERODROME_ROUTER, usdc_amount)
        steps.append({
            "step": 0,
            "protocol": TOKENS["USDC"],
            "calldata": approve_usdc,
            "description": f"Approve {usdc_amount / 1e6:.2f} USDC for Aerodrome Router",
            "token": "USDC"
        })
        
        # ==========================================
        # Step 1: Swap 100% USDC → WETH (deep liquidity)
        # ==========================================
        weth_quote = self.get_swap_quote("USDC", "WETH", usdc_amount)
        if weth_quote == 0:
            raise ValueError("Failed to get USDC→WETH quote")
        
        weth_min = int(weth_quote * slippage_mult)
        
        swap1 = self.build_swap_calldata(
            "USDC", "WETH", usdc_amount, weth_min, recipient, deadline
        )
        steps.append({
            "step": 1,
            "protocol": AERODROME_ROUTER,
            "calldata": swap1,
            "description": f"Swap {usdc_amount / 1e6:.2f} USDC → {weth_quote / 1e18:.6f} WETH",
            "token": "USDC→WETH",
            "amount_in": usdc_amount,
            "amount_out": weth_quote
        })
        
        # ==========================================
        # Step 2: Swap 50% WETH → target token
        # ==========================================
        weth_to_swap = weth_quote // 2
        weth_to_keep = weth_quote - weth_to_swap
        
        target_quote = self.get_swap_quote("WETH", target_token, weth_to_swap)
        if target_quote == 0:
            raise ValueError(f"Failed to get WETH→{target_token} quote")
        
        target_min = int(target_quote * slippage_mult)
        
        # Approve WETH
        approve_weth = self.build_approve_calldata("WETH", AERODROME_ROUTER, weth_to_swap)
        steps.append({
            "step": 2,
            "protocol": TOKENS["WETH"],
            "calldata": approve_weth,
            "description": f"Approve {weth_to_swap / 1e18:.6f} WETH for swap",
            "token": "WETH"
        })
        
        swap2 = self.build_swap_calldata(
            "WETH", target_token, weth_to_swap, target_min, recipient, deadline
        )
        steps.append({
            "step": 3,
            "protocol": AERODROME_ROUTER,
            "calldata": swap2,
            "description": f"Swap {weth_to_swap / 1e18:.6f} WETH → {target_quote / 1e18:.4f} {target_token}",
            "token": f"WETH→{target_token}",
            "amount_in": weth_to_swap,
            "amount_out": target_quote
        })
        
        # ==========================================
        # Step 3: Add Liquidity
        # ==========================================
        # Approve remaining WETH for LP
        approve_weth_lp = self.build_approve_calldata("WETH", AERODROME_ROUTER, weth_to_keep)
        steps.append({
            "step": 4,
            "protocol": TOKENS["WETH"],
            "calldata": approve_weth_lp,
            "description": f"Approve {weth_to_keep / 1e18:.6f} WETH for LP",
            "token": "WETH"
        })
        
        # Approve target token for LP
        target_addr = self._get_token_address(target_token)
        approve_target = self.build_approve_calldata(target_token, AERODROME_ROUTER, target_quote)
        steps.append({
            "step": 5,
            "protocol": target_addr,
            "calldata": approve_target,
            "description": f"Approve {target_quote / 1e18:.4f} {target_token} for LP",
            "token": target_token
        })
        
        add_liq = self.build_add_liquidity_calldata(
            "WETH", target_token, weth_to_keep, target_quote, 
            recipient, slippage, deadline, stable=False
        )
        steps.append({
            "step": 6,
            "protocol": AERODROME_ROUTER,
            "calldata": add_liq,
            "description": f"addLiquidity({weth_to_keep / 1e18:.6f} WETH + {target_quote / 1e18:.4f} {target_token})",
            "token": f"WETH/{target_token} LP",
            "weth_amount": weth_to_keep,
            "target_amount": target_quote
        })
        
        return steps
    
    def print_flow_summary(self, steps: List[Dict]) -> None:
        """Print human-readable summary of LP flow"""
        print("\n" + "=" * 60)
        print("🌊 DUAL LP FLOW - WETH-First Strategy")
        print("=" * 60)
        
        for step in steps:
            print(f"\n📍 Step {step['step']}: {step['description']}")
            print(f"   Protocol: {step['protocol'][:16]}...")
            calldata = step['calldata']
            # Handle both bytes and HexBytes
            if hasattr(calldata, 'hex'):
                calldata_hex = calldata.hex()[:40]
            else:
                calldata_hex = calldata[:40] if isinstance(calldata, str) else str(calldata)[:40]
            print(f"   Calldata: {calldata_hex}...")
        
        print("\n" + "=" * 60)


# ============================================
# CLI for testing
# ============================================
if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("🚀 Testing AerodromeDualLPBuilder")
        
        builder = AerodromeDualLPBuilder()
        
        # Test with $100 USDC → WETH/VIRTUALS LP
        try:
            steps = await builder.build_dual_lp_flow(
                usdc_amount=100 * 10**6,  # $100
                target_pair="WETH/VIRTUALS",
                recipient="0x0000000000000000000000000000000000000001",  # Placeholder
                slippage=0.5
            )
            
            builder.print_flow_summary(steps)
            
            print("\n✅ All steps generated successfully!")
            print(f"   Total steps: {len(steps)}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    asyncio.run(main())
