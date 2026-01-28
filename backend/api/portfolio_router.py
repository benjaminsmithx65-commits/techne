"""
Portfolio Router - Aggregated Portfolio Data API
Returns all holdings, positions, and LP data in a single call for fast frontend loading.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from web3 import Web3
import asyncio
import os
from datetime import datetime

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# Base RPC
RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Token addresses on Base
USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
WETH_ADDRESS = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")
CBBTC_ADDRESS = Web3.to_checksum_address("0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf")
AERO_ADDRESS = Web3.to_checksum_address("0x940181a94A35A4569E4529A3CDfB74e38FD98631")
WSOL_ADDRESS = Web3.to_checksum_address("0x1c61629598e4a901136a81bc138e5828dc150d67")  # wSOL on Base

# ERC20 ABI (just balanceOf)
ERC20_ABI = [{"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]

# Approximate prices (could be fetched from oracle later)
TOKEN_PRICES = {
    "USDC": 1.0,
    "ETH": 3300,
    "WETH": 3300,
    "cbBTC": 100000,
    "AERO": 1.5,
    "wSOL": 180
}

class Holding(BaseModel):
    asset: str
    balance: float
    value_usd: float
    label: Optional[str] = None

class Position(BaseModel):
    id: str
    protocol: str
    pool_name: Optional[str] = None
    value_usd: float
    apy: float = 25.0
    deposited: Optional[float] = None

class PortfolioResponse(BaseModel):
    success: bool
    holdings: List[Holding]
    positions: List[Position]
    total_value_usd: float
    agent_address: Optional[str] = None
    cached_at: str
    load_time_ms: float


def get_token_balance_sync(token_address: str, wallet_address: str, decimals: int = 18) -> float:
    """Get ERC20 token balance synchronously"""
    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        balance = contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
        return balance / (10 ** decimals)
    except Exception as e:
        print(f"[Portfolio] Balance fetch error for {token_address}: {e}")
        return 0.0


def get_eth_balance_sync(wallet_address: str) -> float:
    """Get ETH balance synchronously"""
    try:
        balance = w3.eth.get_balance(Web3.to_checksum_address(wallet_address))
        return balance / 1e18
    except Exception as e:
        print(f"[Portfolio] ETH balance error: {e}")
        return 0.0


async def fetch_all_balances(agent_address: str) -> List[Holding]:
    """Fetch all token balances in parallel using thread pool"""
    loop = asyncio.get_event_loop()
    
    # Define all balance fetches
    tasks = [
        loop.run_in_executor(None, get_token_balance_sync, USDC_ADDRESS, agent_address, 6),
        loop.run_in_executor(None, get_eth_balance_sync, agent_address),
        loop.run_in_executor(None, get_token_balance_sync, WETH_ADDRESS, agent_address, 18),
        loop.run_in_executor(None, get_token_balance_sync, CBBTC_ADDRESS, agent_address, 8),
        loop.run_in_executor(None, get_token_balance_sync, AERO_ADDRESS, agent_address, 18),
        loop.run_in_executor(None, get_token_balance_sync, WSOL_ADDRESS, agent_address, 9),  # wSOL has 9 decimals
    ]
    
    # Execute all in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    holdings = []
    tokens = [
        ("USDC", results[0] if not isinstance(results[0], Exception) else 0),
        ("ETH", results[1] if not isinstance(results[1], Exception) else 0),
        ("WETH", results[2] if not isinstance(results[2], Exception) else 0),
        ("cbBTC", results[3] if not isinstance(results[3], Exception) else 0),
        ("AERO", results[4] if not isinstance(results[4], Exception) else 0),
        ("wSOL", results[5] if not isinstance(results[5], Exception) else 0),
    ]
    
    for symbol, balance in tokens:
        if balance > 0.0001:  # Only include if has meaningful balance
            price = TOKEN_PRICES.get(symbol, 1.0)
            value = balance * price
            if value > 0.01:  # Only show if worth > $0.01
                holdings.append(Holding(
                    asset=symbol,
                    balance=round(balance, 8),
                    value_usd=round(value, 2),
                    label=f"Agent {symbol} balance"
                ))
    
    return holdings


async def fetch_lp_positions(user_address: str, agent_address: str) -> List[Position]:
    """Fetch LP positions directly from known Aerodrome pools"""
    try:
        if not agent_address:
            return []
        
        # Known Aerodrome LP tokens on Base
        LP_TOKENS = [
            {"name": "cbBTC/USDC", "address": "0x9c38b55f9a9aba91bbcedeb12bf4428f47a6a0b8", "protocol": "Aerodrome"},
            {"name": "WETH/USDC", "address": "0xb4cb800910B228ED3d0834cF79D697127BBB00e5", "protocol": "Aerodrome"},
            {"name": "AERO/USDC", "address": "0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d", "protocol": "Aerodrome"},
        ]
        
        positions = []
        agent_checksummed = Web3.to_checksum_address(agent_address)
        
        for lp in LP_TOKENS:
            try:
                # balanceOf(agent)
                balance_call = w3.eth.call({
                    'to': Web3.to_checksum_address(lp["address"]),
                    'data': '0x70a08231' + agent_address[2:].lower().zfill(64)
                })
                balance = int(balance_call.hex(), 16)
                
                if balance > 0:
                    lp_tokens = balance / 1e18
                    
                    # Get reserves and calculate USD value
                    try:
                        reserves_call = w3.eth.call({
                            'to': Web3.to_checksum_address(lp["address"]),
                            'data': '0x0902f1ac'  # getReserves()
                        })
                        reserve1 = int(reserves_call.hex()[66:130], 16)
                        
                        supply_call = w3.eth.call({
                            'to': Web3.to_checksum_address(lp["address"]),
                            'data': '0x18160ddd'  # totalSupply()
                        })
                        total_supply = int(supply_call.hex(), 16)
                        
                        if total_supply > 0:
                            share = balance / total_supply
                            usdc_value = (reserve1 / 1e6) * share * 2  # Both sides
                            estimated_value = usdc_value if usdc_value > 0.001 else lp_tokens
                        else:
                            estimated_value = lp_tokens
                    except:
                        estimated_value = lp_tokens * 1.0
                    
                    if estimated_value > 0.10:  # Only show if > $0.10
                        positions.append(Position(
                            id=f"lp_{len(positions)}",
                            protocol=lp["protocol"],
                            pool_name=lp["name"],
                            value_usd=round(estimated_value, 2),
                            apy=25.0,  # Default Aerodrome APY
                            deposited=round(estimated_value, 2)
                        ))
            except Exception as e:
                print(f"[Portfolio] LP check error for {lp['name']}: {e}")
                continue
        
        return positions
    except Exception as e:
        print(f"[Portfolio] LP positions error: {e}")
        return []


@router.get("/{user_address}", response_model=PortfolioResponse)
async def get_portfolio(user_address: str):
    """
    Get complete portfolio data in a single call.
    Fetches all balances and positions in parallel for fast loading.
    """
    import time
    start = time.time()
    
    # Get agent address from stored agents
    agent_address = None
    try:
        agents = []
        user_lower = user_address.lower()
        
        # Try agent_config_router DEPLOYED_AGENTS first (main source)
        try:
            from api.agent_config_router import DEPLOYED_AGENTS
            agents = DEPLOYED_AGENTS.get(user_lower, [])
            if agents:
                print(f"[Portfolio] Found {len(agents)} agents in DEPLOYED_AGENTS")
        except Exception as e:
            print(f"[Portfolio] DEPLOYED_AGENTS lookup error: {e}")
        
        # Fallback to Supabase
        if not agents:
            try:
                from infrastructure.supabase_client import SupabaseClient
                supabase = SupabaseClient()
                if supabase.is_available:
                    agents = await supabase.get_user_agents(user_address)
            except:
                pass
        
        # Fallback to agent_router deployed_agents
        if not agents:
            try:
                from api.agent_router import deployed_agents
                agents = deployed_agents.get(user_lower, [])
            except:
                pass
        
        if agents and len(agents) > 0:
            agent_address = agents[0].get("agent_address") or agents[0].get("address")
            print(f"[Portfolio] Using agent: {agent_address}")
    except Exception as e:
        print(f"[Portfolio] Agent lookup error: {e}")
    
    holdings = []
    positions = []
    
    if agent_address:
        # Fetch holdings and positions in parallel
        holdings_task = fetch_all_balances(agent_address)
        positions_task = fetch_lp_positions(user_address, agent_address)
        
        holdings, positions = await asyncio.gather(holdings_task, positions_task)
    
    # Calculate total
    total = sum(h.value_usd for h in holdings) + sum(p.value_usd for p in positions)
    
    load_time = (time.time() - start) * 1000
    print(f"[Portfolio] Loaded in {load_time:.0f}ms - {len(holdings)} holdings, {len(positions)} positions")
    
    return PortfolioResponse(
        success=True,
        holdings=holdings,
        positions=positions,
        total_value_usd=round(total, 2),
        agent_address=agent_address,
        cached_at=datetime.utcnow().isoformat() + "Z",
        load_time_ms=round(load_time, 1)
    )
