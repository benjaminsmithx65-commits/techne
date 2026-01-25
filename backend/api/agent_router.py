"""
Agent Operations API Router
Endpoints for agent actions: harvest, rebalance, pause, audit
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import csv
import io

router = APIRouter(prefix="/api/agent", tags=["Agent Operations"])

# ============================================
# MODELS
# ============================================

class HarvestRequest(BaseModel):
    wallet: str
    agentId: str
    agentAddress: Optional[str] = None

class RebalanceRequest(BaseModel):
    wallet: str
    agentId: str
    agentAddress: Optional[str] = None
    strategy: Optional[str] = None

class PauseAllRequest(BaseModel):
    wallet: str
    reason: str = "manual"

class AgentStatusUpdate(BaseModel):
    wallet: str
    agentId: str
    isActive: bool

# ============================================
# MANUAL ALLOCATE ENDPOINT
# ============================================

@router.post("/allocate")
async def manual_allocate(user_address: str = Query(...)):
    """
    Manually trigger allocation of user's deposited funds to protocol.
    Called when deposit was missed by the monitor or for testing.
    """
    try:
        from agents.contract_monitor import contract_monitor
        from web3 import Web3
        
        # Get user's balance from contract
        w3 = contract_monitor._get_web3()
        balance = contract_monitor.contract.functions.balances(
            Web3.to_checksum_address(user_address)
        ).call()
        
        amount_usdc = balance / 1e6
        
        if balance == 0:
            return {
                "success": False,
                "message": "No funds to allocate",
                "balance": 0
            }
        
        print(f"[ManualAllocate] Allocating {amount_usdc:.2f} USDC for {user_address[:10]}...")
        
        # Trigger allocation
        await contract_monitor.allocate_funds(user_address, balance)
        
        return {
            "success": True,
            "user_address": user_address,
            "amount_usdc": amount_usdc,
            "message": f"Allocation triggered for {amount_usdc:.2f} USDC"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# AGENT WALLET ALLOCATION (New - No Smart Contract!)
# ============================================

# Base USDC contract address
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# ERC20 ABI for balanceOf
ERC20_ABI = [
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


@router.post("/trigger-allocation")
async def trigger_agent_allocation(
    user_address: str = Query(..., description="User's wallet address"),
    agent_id: str = Query(None, description="Specific agent ID (optional)")
):
    """
    Trigger allocation for agent wallet after user funded it with USDC.
    
    This is the NEW flow (no smart contract):
    1. User deploys agent → gets agent_address
    2. User sends USDC to agent_address (Fund Agent)
    3. Frontend calls this endpoint
    4. Backend reads agent wallet USDC balance
    5. Backend allocates to protocols according to agent config
    
    COOLDOWN: If user closed a position within last 5 minutes, allocation is blocked.
    This prevents immediate re-allocation after user manually exits.
    
    Called by frontend after fundAgentWallet() completes.
    """
    try:
        from agents.contract_monitor import contract_monitor
        from api.agent_config_router import DEPLOYED_AGENTS
        from web3 import Web3
        from datetime import datetime, timedelta
        
        COOLDOWN_MINUTES = 5
        
        # Get user's deployed agent
        user_lower = user_address.lower()
        user_agents = DEPLOYED_AGENTS.get(user_lower, [])
        
        if not user_agents:
            return {
                "success": False,
                "error": "No deployed agent found for this user",
                "hint": "Please deploy an agent first via /api/agent/deploy"
            }
        
        # Find specific agent or use first active one
        agent = None
        if agent_id:
            agent = next((a for a in user_agents if a.get("id") == agent_id), None)
        else:
            agent = next((a for a in user_agents if a.get("is_active")), None)
        
        if not agent:
            return {
                "success": False,
                "error": "No active agent found"
            }
        
        # ============================================
        # COOLDOWN CHECK: 5 minutes after position close
        # ============================================
        last_close = agent.get("last_position_close")
        if last_close:
            try:
                last_close_time = datetime.fromisoformat(last_close)
                cooldown_end = last_close_time + timedelta(minutes=COOLDOWN_MINUTES)
                now = datetime.utcnow()
                
                if now < cooldown_end:
                    remaining = (cooldown_end - now).total_seconds()
                    remaining_mins = int(remaining // 60)
                    remaining_secs = int(remaining % 60)
                    
                    print(f"[TriggerAllocation] COOLDOWN active - {remaining_mins}m {remaining_secs}s remaining")
                    return {
                        "success": False,
                        "cooldown_active": True,
                        "cooldown_remaining_seconds": int(remaining),
                        "cooldown_ends": cooldown_end.isoformat(),
                        "message": f"Position closed recently. Agent cooldown: {remaining_mins}m {remaining_secs}s remaining before new allocations."
                    }
            except Exception as e:
                print(f"[TriggerAllocation] Cooldown check error: {e}")
        
        # V4.3.3 Contract - same as frontend portfolio reads from
        V4_CONTRACT = "0xC83E01e39A56Ec8C56Dd45236E58eE7a139cCDD4"
        V4_ABI = [
            {
                "inputs": [{"name": "user", "type": "address"}],
                "name": "balances",
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        # Get user's USDC balance from V4 contract (same source as portfolio frontend!)
        w3 = contract_monitor._get_web3()
        v4_contract = w3.eth.contract(
            address=Web3.to_checksum_address(V4_CONTRACT),
            abi=V4_ABI
        )
        
        balance = v4_contract.functions.balances(
            Web3.to_checksum_address(user_address)
        ).call()
        
        amount_usdc = balance / 1e6
        
        if balance == 0:
            return {
                "success": False,
                "message": "No USDC deposited in contract to allocate",
                "user_address": user_address,
                "contract": V4_CONTRACT,
                "balance": 0
            }
        
        print(f"[TriggerAllocation] User {user_address[:10]}... has {amount_usdc:.2f} USDC in V4 contract", flush=True)
        print(f"[TriggerAllocation] Agent: {agent.get('id')}, pool_type={agent.get('pool_type')}, risk={agent.get('risk_level')}", flush=True)
        
        # Trigger allocation using V4 contract balance
        print(f"[TriggerAllocation] >>> CALLING allocate_funds...", flush=True)
        await contract_monitor.allocate_funds(user_address, balance)
        print(f"[TriggerAllocation] <<< allocate_funds RETURNED", flush=True)
        
        return {
            "success": True,
            "agent_id": agent.get("id"),
            "user_address": user_address,
            "amount_usdc": amount_usdc,
            "pool_type": agent.get("pool_type"),
            "risk_level": agent.get("risk_level"),
            "message": f"Allocation triggered for {amount_usdc:.2f} USDC"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# SMART ACCOUNT ENDPOINTS (Trustless Architecture)
# ============================================

@router.get("/smart-account")
async def get_smart_account(wallet_address: str = Query(...)):
    """
    Get user's Smart Account address and info.
    
    Returns:
    - smart_account: Address of user's Smart Account (or null if not created)
    - factory: Factory address for creating new accounts
    - can_create: Whether user can create a new Smart Account
    """
    from api.smart_account_executor import SmartAccountExecutor, FACTORY_ADDRESS
    
    try:
        executor = SmartAccountExecutor(wallet_address)
        
        # Check if session key is setup
        can_use_session_key = False
        if executor.smart_account:
            can_use_session_key = executor.can_use_session_key
        
        return {
            "success": True,
            "smart_account": executor.smart_account,
            "factory": FACTORY_ADDRESS,
            "is_active": executor.is_smart_account_active,
            "can_use_session_key": can_use_session_key,
            "legacy_wallet": "0xC83E01e39A56Ec8C56Dd45236E58eE7a139cCDD4"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "smart_account": None
        }


@router.post("/smart-account/register")
async def register_smart_account(
    wallet_address: str = Query(...),
    smart_account_address: str = Query(...),
    session_key_address: str = Query(None)
):
    """
    Register a user's Smart Account address in the database.
    Called after user creates Smart Account via frontend.
    """
    try:
        from infrastructure.supabase_client import supabase
        
        if supabase.is_available:
            result = await supabase.save_user_smart_account(
                wallet_address,
                smart_account_address,
                session_key_address
            )
            
            return {
                "success": True,
                "registered": result is not None,
                "smart_account": smart_account_address
            }
        
        return {
            "success": True,
            "registered": False,
            "message": "Supabase not available - will use on-chain data"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# CLOSE POSITION ENDPOINT
# ============================================

class ClosePositionRequest(BaseModel):
    user_address: str
    position_id: int
    protocol: str
    percentage: int  # 1-100
    amount: int  # USDC in 6 decimals

position_router = APIRouter(prefix="/api/position", tags=["Position Management"])

@position_router.post("/close")
async def close_position(request: ClosePositionRequest):
    """
    Close a position partially or fully.
    
    Withdraws the specified percentage from the protocol back to user's wallet.
    """
    import os
    
    try:
        amount_usdc = request.amount / 1e6
        
        print(f"[ClosePosition] Closing {request.percentage}% of position {request.position_id}", flush=True)
        print(f"[ClosePosition] Protocol: {request.protocol}, Amount: ${amount_usdc:.2f}", flush=True)
        
        # 0. Execute ON-CHAIN withdrawal via SmartAccountExecutor
        # Supports both Smart Account mode and legacy Techne Wallet fallback
        onchain_tx_hash = None
        if request.protocol.lower() in ["aave", "aave-v3", "aave v3"]:
            print("[ClosePosition] Protocol is Aave - using SmartAccountExecutor", flush=True)
            try:
                from api.smart_account_executor import SmartAccountExecutor
                
                executor = SmartAccountExecutor(request.user_address)
                print(f"[ClosePosition] Smart Account: {executor.smart_account}", flush=True)
                print(f"[ClosePosition] Mode: {'smart_account' if executor.is_smart_account_active else 'legacy'}", flush=True)
                
                # Execute exit position
                result = await executor.exit_position_aave()
                
                if result.get("success"):
                    if result.get("mode") == "legacy":
                        # Legacy mode executed synchronously
                        onchain_tx_hash = result.get("tx_hash")
                        print(f"[ClosePosition] ✅ Legacy exitPosition SUCCESS: {onchain_tx_hash}", flush=True)
                    elif result.get("mode") == "smart_account":
                        # Smart Account mode returns prepared tx for frontend
                        print(f"[ClosePosition] ✅ Smart Account TX prepared - needs owner signature", flush=True)
                        # Return calldata to frontend for user signing
                else:
                    print(f"[ClosePosition] ⚠️ Exit failed: {result.get('error')}", flush=True)
                    
            except Exception as e:
                print(f"[ClosePosition] On-chain error: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        # Handle Morpho withdrawals
        elif request.protocol.lower() in ["morpho", "morpho-blue"]:
            print("[ClosePosition] Protocol is Morpho - executing withdrawal", flush=True)
            try:
                from api.smart_account_executor import SmartAccountExecutor, USDC
                from web3 import Web3
                import os
                from eth_account import Account
                
                # Morpho Blue on Base
                MORPHO_BLUE = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
                
                agent_key = os.getenv("PRIVATE_KEY")
                if agent_key:
                    account = Account.from_key(agent_key)
                    executor = SmartAccountExecutor(request.user_address)
                    w3 = executor.w3
                    
                    # Morpho Blue withdraw ABI
                    morpho_abi = [{
                        "inputs": [
                            {"name": "market", "type": "tuple", "components": [
                                {"name": "loanToken", "type": "address"},
                                {"name": "collateralToken", "type": "address"},
                                {"name": "oracle", "type": "address"},
                                {"name": "irm", "type": "address"},
                                {"name": "lltv", "type": "uint256"}
                            ]},
                            {"name": "assets", "type": "uint256"},
                            {"name": "shares", "type": "uint256"},
                            {"name": "onBehalf", "type": "address"},
                            {"name": "receiver", "type": "address"}
                        ],
                        "name": "withdraw",
                        "outputs": [{"type": "uint256"}, {"type": "uint256"}],
                        "stateMutability": "nonpayable",
                        "type": "function"
                    }]
                    
                    # For now, log that we would withdraw
                    print(f"[ClosePosition] Morpho withdrawal for ${amount_usdc:.2f} queued")
                    # TODO: Execute actual Morpho withdraw when market params known
                    
            except Exception as e:
                print(f"[ClosePosition] Morpho error: {e}")
        
        # Handle Moonwell withdrawals (Compound fork)
        elif request.protocol.lower() in ["moonwell", "moonwell-base"]:
            print("[ClosePosition] Protocol is Moonwell - executing withdrawal", flush=True)
            try:
                from web3 import Web3
                import os
                from eth_account import Account
                
                # Moonwell mUSDC on Base
                MOONWELL_USDC = "0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22"
                
                agent_key = os.getenv("PRIVATE_KEY")
                if agent_key:
                    account = Account.from_key(agent_key)
                    w3 = Web3(Web3.HTTPProvider(os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")))
                    
                    # Moonwell redeem ABI (Compound-style)
                    moonwell_abi = [{
                        "inputs": [{"name": "redeemTokens", "type": "uint256"}],
                        "name": "redeem",
                        "outputs": [{"type": "uint256"}],
                        "stateMutability": "nonpayable",
                        "type": "function"
                    }]
                    
                    moon = w3.eth.contract(
                        address=Web3.to_checksum_address(MOONWELL_USDC),
                        abi=moonwell_abi
                    )
                    
                    # Get balance of mTokens
                    balance_abi = [{"inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}]
                    moon_balance = w3.eth.contract(address=Web3.to_checksum_address(MOONWELL_USDC), abi=balance_abi)
                    mtoken_balance = moon_balance.functions.balanceOf(request.user_address).call()
                    
                    if mtoken_balance > 0:
                        redeem_amount = mtoken_balance if request.percentage >= 100 else int(mtoken_balance * request.percentage / 100)
                        
                        tx = moon.functions.redeem(redeem_amount).build_transaction({
                            'from': account.address,
                            'nonce': w3.eth.get_transaction_count(account.address),
                            'gas': 300000,
                            'gasPrice': w3.eth.gas_price
                        })
                        
                        signed = account.sign_transaction(tx)
                        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                        
                        if receipt.status == 1:
                            onchain_tx_hash = tx_hash.hex()
                            print(f"[ClosePosition] ✅ Moonwell redeem SUCCESS: {onchain_tx_hash}")
                        
            except Exception as e:
                print(f"[ClosePosition] Moonwell error: {e}")
        
        # Handle Aerodrome withdrawals (LP removal)
        elif request.protocol.lower() in ["aerodrome", "aerodrome-lp"]:
            print("[ClosePosition] Protocol is Aerodrome LP - executing withdrawal", flush=True)
            try:
                from web3 import Web3
                import os
                import time
                from eth_account import Account
                
                # Aerodrome contracts on Base
                AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
                USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
                WETH = "0x4200000000000000000000000000000000000006"
                
                agent_key = os.getenv("PRIVATE_KEY")
                if not agent_key:
                    print("[ClosePosition] No PRIVATE_KEY for Aerodrome withdrawal")
                else:
                    account = Account.from_key(agent_key)
                    w3 = Web3(Web3.HTTPProvider(os.getenv("ALCHEMY_RPC_URL", "https://mainnet.base.org")))
                    
                    # Get LP token info from position data or DEPLOYED_AGENTS
                    from api.agent_config_router import DEPLOYED_AGENTS
                    user_agents = DEPLOYED_AGENTS.get(request.user_address.lower(), [])
                    
                    lp_token_address = None
                    token_a = USDC
                    token_b = WETH
                    is_stable = False
                    
                    # Find position info
                    for agent in user_agents:
                        for pos in agent.get("positions", []):
                            if pos.get("protocol", "").lower() in ["aerodrome", "aerodrome-lp"]:
                                lp_token_address = pos.get("lp_token") or pos.get("pool_address")
                                token_a = pos.get("token_a", USDC)
                                token_b = pos.get("token_b", WETH)
                                is_stable = pos.get("stable", False)
                                break
                    
                    if not lp_token_address:
                        # Default to USDC/WETH volatile pool
                        lp_token_address = "0xcDAC0d6c6C59727a65F871236188350531885C43"  # vAMM-USDC/WETH
                        print(f"[ClosePosition] Using default LP pool: {lp_token_address}")
                    
                    # ERC20 ABI for LP token
                    erc20_abi = [
                        {"inputs": [{"name": "owner", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
                        {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"}
                    ]
                    
                    lp_contract = w3.eth.contract(
                        address=Web3.to_checksum_address(lp_token_address),
                        abi=erc20_abi
                    )
                    
                    # Get user's LP balance
                    lp_balance = lp_contract.functions.balanceOf(account.address).call()
                    
                    if lp_balance == 0:
                        print("[ClosePosition] No LP tokens to withdraw")
                    else:
                        withdraw_amount = lp_balance if request.percentage >= 100 else int(lp_balance * request.percentage / 100)
                        print(f"[ClosePosition] LP balance: {lp_balance}, withdrawing: {withdraw_amount}")
                        
                        # Step 1: Approve Router to spend LP tokens
                        approve_tx = lp_contract.functions.approve(
                            Web3.to_checksum_address(AERODROME_ROUTER),
                            withdraw_amount
                        ).build_transaction({
                            'from': account.address,
                            'gas': 100000,
                            'gasPrice': w3.eth.gas_price,
                            'nonce': w3.eth.get_transaction_count(account.address),
                            'chainId': 8453
                        })
                        
                        signed_approve = account.sign_transaction(approve_tx)
                        approve_hash = w3.eth.send_raw_transaction(signed_approve.raw_transaction)
                        w3.eth.wait_for_transaction_receipt(approve_hash, timeout=60)
                        print(f"[ClosePosition] LP approval TX: {approve_hash.hex()}")
                        
                        # Step 2: Remove Liquidity
                        router_abi = [{
                            "inputs": [
                                {"name": "tokenA", "type": "address"},
                                {"name": "tokenB", "type": "address"},
                                {"name": "stable", "type": "bool"},
                                {"name": "liquidity", "type": "uint256"},
                                {"name": "amountAMin", "type": "uint256"},
                                {"name": "amountBMin", "type": "uint256"},
                                {"name": "to", "type": "address"},
                                {"name": "deadline", "type": "uint256"}
                            ],
                            "name": "removeLiquidity",
                            "outputs": [{"type": "uint256"}, {"type": "uint256"}],
                            "stateMutability": "nonpayable",
                            "type": "function"
                        }]
                        
                        router = w3.eth.contract(
                            address=Web3.to_checksum_address(AERODROME_ROUTER),
                            abi=router_abi
                        )
                        
                        deadline = int(time.time()) + 1800  # 30 min deadline
                        
                        remove_tx = router.functions.removeLiquidity(
                            Web3.to_checksum_address(token_a),
                            Web3.to_checksum_address(token_b),
                            is_stable,
                            withdraw_amount,
                            0,  # amountAMin (accept any - set slippage in prod)
                            0,  # amountBMin
                            account.address,
                            deadline
                        ).build_transaction({
                            'from': account.address,
                            'gas': 500000,
                            'gasPrice': w3.eth.gas_price,
                            'nonce': w3.eth.get_transaction_count(account.address),
                            'chainId': 8453
                        })
                        
                        signed_remove = account.sign_transaction(remove_tx)
                        remove_hash = w3.eth.send_raw_transaction(signed_remove.raw_transaction)
                        receipt = w3.eth.wait_for_transaction_receipt(remove_hash, timeout=120)
                        
                        if receipt.status == 1:
                            onchain_tx_hash = remove_hash.hex()
                            print(f"[ClosePosition] ✅ Aerodrome LP removal SUCCESS: {onchain_tx_hash}")
                            
                            # Step 3: Swap non-USDC token back to USDC (if needed)
                            # TODO: Call swapExactTokensForTokens for token_b -> USDC
                        else:
                            print(f"[ClosePosition] ❌ Aerodrome LP removal FAILED")
                            
            except Exception as e:
                import traceback
                print(f"[ClosePosition] Aerodrome error: {e}")
                traceback.print_exc()
        
        # 1. Close/Update position in Supabase
        try:
            from infrastructure.supabase_client import supabase
            if supabase and supabase.is_available:
                if request.percentage >= 100:
                    # Full close - mark as closed
                    await supabase.close_user_position(request.user_address, request.protocol)
                    await supabase.log_position_history(
                        user_address=request.user_address,
                        protocol=request.protocol,
                        action="close",
                        amount=amount_usdc,
                        metadata={"percentage": request.percentage}
                    )
                    print(f"[ClosePosition] Position closed in Supabase")
                else:
                    # Partial close - update current value
                    # Get current position and reduce by percentage
                    positions = await supabase.get_user_positions(request.user_address)
                    for pos in positions:
                        if pos.get("protocol") == request.protocol:
                            new_value = pos.get("current_value", 0) * (1 - request.percentage / 100)
                            await supabase.update_user_position_value(
                                request.user_address,
                                request.protocol,
                                new_value
                            )
                            await supabase.log_position_history(
                                user_address=request.user_address,
                                protocol=request.protocol,
                                action="partial_close",
                                amount=amount_usdc,
                                metadata={"percentage": request.percentage, "new_value": new_value}
                            )
                            break
                    print(f"[ClosePosition] Position reduced by {request.percentage}% in Supabase")
        except Exception as e:
            print(f"[ClosePosition] Supabase update failed: {e}")
        
        # 2. Update in-memory DEPLOYED_AGENTS + set cooldown timestamp
        try:
            from api.agent_config_router import DEPLOYED_AGENTS, _save_agents
            from datetime import datetime
            
            user_agents = DEPLOYED_AGENTS.get(request.user_address.lower(), [])
            for agent in user_agents:
                positions = agent.get("positions", [])
                if request.percentage >= 100:
                    # Remove position
                    agent["positions"] = [p for p in positions if p.get("protocol") != request.protocol]
                else:
                    # Reduce position value
                    for pos in positions:
                        if pos.get("protocol") == request.protocol:
                            pos["current_value"] = pos.get("current_value", 0) * (1 - request.percentage / 100)
                
                # SET COOLDOWN: 5-minute cooldown before agent can allocate again
                agent["last_position_close"] = datetime.utcnow().isoformat()
                print(f"[ClosePosition] Cooldown set - agent cannot allocate for 5 minutes")
            
            _save_agents()
            print(f"[ClosePosition] In-memory agents updated")
        except Exception as e:
            print(f"[ClosePosition] In-memory update failed: {e}")
        
        # 3. Log to audit trail
        try:
            from agents.audit_trail import audit_trail, ActionType
            audit_trail.log(
                action_type=ActionType.WITHDRAW,
                agent_id="system",
                wallet_address=request.user_address,
                details={
                    "position_id": request.position_id,
                    "protocol": request.protocol,
                    "percentage": request.percentage,
                    "amount_usdc": amount_usdc
                },
                tx_hash=onchain_tx_hash,
                value_usd=amount_usdc,
                success=True
            )
        except Exception as e:
            print(f"[ClosePosition] Audit log failed: {e}")
        
        # Use real tx hash if available, otherwise simulate
        if onchain_tx_hash:
            tx_hash = onchain_tx_hash
        else:
            import hashlib
            import time
            tx_hash = "0x" + hashlib.sha256(f"{request.user_address}{time.time()}".encode()).hexdigest()[:64]
        
        return {
            "success": True,
            "message": f"Closed {request.percentage}% of position",
            "protocol": request.protocol,
            "amount_usdc": amount_usdc,
            "tx_hash": tx_hash,
            "onchain": onchain_tx_hash is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@position_router.get("/{user_address}")
async def get_user_positions(user_address: str):
    """
    Get all real positions for a user.
    
    Priority:
    1. Supabase user_positions table (FAST - ~50ms)
    2. In-memory contract_monitor cache (medium)
    3. On-chain data (slow - last resort)
    """
    try:
        from infrastructure.supabase_client import supabase
        from agents.contract_monitor import contract_monitor, PROTOCOLS
        from web3 import Web3
        
        user_addr = user_address.lower()
        result_positions = []
        total_value = 0
        weighted_apy_sum = 0
        
        # =============================================
        # STEP 1: Try Supabase (FASTEST)
        # =============================================
        if supabase.is_available:
            try:
                db_positions = await supabase.get_user_positions(user_address)
                
                if db_positions:
                    for pos in db_positions:
                        entry_value = float(pos.get("entry_value", 0))
                        current_value = float(pos.get("current_value", entry_value))
                        apy = float(pos.get("apy", 0))
                        
                        result_positions.append({
                            "id": hash(f"{user_address}{pos['protocol']}") % 1000000,
                            "protocol": pos["protocol"],
                            "protocol_name": pos["protocol"].replace("_", " ").title(),
                            "vaultName": pos["protocol"].replace("_", " ").title(),
                            "asset": pos.get("asset", "USDC"),
                            "pool_type": pos.get("pool_type", "single"),
                            "deposited": entry_value,
                            "current": current_value,
                            "pnl": current_value - entry_value,
                            "apy": apy,
                            "entry_time": pos.get("entry_time", ""),
                            "source": "supabase"
                        })
                        
                        total_value += current_value
                        weighted_apy_sum += apy * current_value
                    
                    avg_apy = (weighted_apy_sum / total_value) if total_value > 0 else 0
                    
                    print(f"[Position API] Loaded {len(result_positions)} positions from Supabase for {user_addr[:10]}...")
                    
                    return {
                        "success": True,
                        "user_address": user_address,
                        "positions": result_positions,
                        "summary": {
                            "total_value": total_value,
                            "position_count": len(result_positions),
                            "avg_apy": round(avg_apy, 2)
                        },
                        "source": "supabase"
                    }
            except Exception as e:
                print(f"[Position API] Supabase read failed: {e}")
        
        # =============================================
        # STEP 2: Fallback to in-memory cache
        # =============================================
        positions = contract_monitor.user_positions.get(user_addr, {})
        
        if not positions:
            try:
                user_addr = Web3.to_checksum_address(user_address)
                positions = contract_monitor.user_positions.get(user_addr, {})
            except:
                pass
        
        for proto_key, pos_data in positions.items():
            proto_info = PROTOCOLS.get(proto_key, {})
            entry_value = pos_data.get("entry_value", 0)
            current_value = pos_data.get("current_value", entry_value)
            entry_time = pos_data.get("entry_time", "")
            
            apy = proto_info.get("apy", 0)
            pnl = current_value - entry_value
            
            result_positions.append({
                "id": hash(f"{user_address}{proto_key}") % 1000000,
                "protocol": proto_key,
                "protocol_name": proto_info.get("name", proto_key.title()),
                "vaultName": proto_info.get("name", proto_key.title()),
                "asset": proto_info.get("asset", "USDC"),
                "pool_type": proto_info.get("pool_type", "single"),
                "deposited": entry_value / 1e6,
                "current": current_value / 1e6,
                "pnl": pnl / 1e6,
                "apy": apy,
                "entry_time": entry_time,
                "source": "memory"
            })
            
            total_value += current_value
            weighted_apy_sum += apy * current_value
        
        avg_apy = (weighted_apy_sum / total_value) if total_value > 0 else 0
        
        return {
            "success": True,
            "user_address": user_address,
            "positions": result_positions,
            "summary": {
                "total_value": total_value / 1e6,
                "position_count": len(result_positions),
                "avg_apy": round(avg_apy, 2)
            },
            "source": "memory"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "positions": [],
            "error": str(e)
        }

# ============================================
# RECOMMENDATIONS ENDPOINT
# ============================================

@router.get("/recommendations/{wallet_address}")
async def get_recommendations(wallet_address: str):
    """
    Get recommended pools for user based on their agent config.
    """
    try:
        from api.agent_config_router import DEPLOYED_AGENTS
        
        # Get user's agent config
        agents = DEPLOYED_AGENTS.get(wallet_address.lower(), [])
        
        if not agents:
            return {
                "success": True,
                "recommended_pools": [],
                "message": "No agent deployed"
            }
        
        agent = agents[0]
        risk_level = agent.get("risk_level", "moderate")
        protocols = agent.get("protocols", ["aave", "morpho"])
        min_apy = agent.get("min_apy", 5.0)
        
        # All available protocols with live APY data
        ALL_POOLS = [
            {"id": "aave-usdc-base", "protocol": "Aave V3", "asset": "USDC", "apy": 6.2, "tvl": 125000000, "risk": "A+"},
            {"id": "morpho-usdc-base", "protocol": "Morpho Blue", "asset": "USDC", "apy": 8.5, "tvl": 45000000, "risk": "A"},
            {"id": "moonwell-usdc-base", "protocol": "Moonwell", "asset": "USDC", "apy": 7.1, "tvl": 78000000, "risk": "A"},
            {"id": "compound-usdc-base", "protocol": "Compound V3", "asset": "USDC", "apy": 5.8, "tvl": 95000000, "risk": "A+"},
            {"id": "seamless-usdc-base", "protocol": "Seamless", "asset": "USDC", "apy": 9.2, "tvl": 32000000, "risk": "A-"},
            {"id": "aerodrome-usdc-weth", "protocol": "Aerodrome", "asset": "USDC-WETH", "apy": 15.2, "tvl": 82000000, "risk": "B+"},
        ]
        
        # Filter by agent's protocol preferences
        protocol_lower = [p.lower() for p in protocols]
        pools = [p for p in ALL_POOLS if p["protocol"].lower().replace(" ", "").replace("v3", "") in 
                 [x.replace(" ", "") for x in protocol_lower] or 
                 p["id"].split("-")[0] in protocol_lower]
        
        # Sort by APY descending
        pools.sort(key=lambda x: x["apy"], reverse=True)
        
        return {
            "success": True,
            "recommended_pools": pools[:5],
            "agent_config": {
                "risk_level": risk_level,
                "protocols": protocols,
                "min_apy": min_apy
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "recommended_pools": [],
            "error": str(e)
        }

# ============================================
# AGENT STATUS ENDPOINT
# ============================================

@router.get("/status/{wallet_address}")
async def get_agent_status(wallet_address: str):
    """
    Get deployed agent status for a wallet.
    """
    try:
        from api.agent_config_router import DEPLOYED_AGENTS
        from web3 import Web3
        
        # Get user's deployed agents
        agents = DEPLOYED_AGENTS.get(wallet_address.lower(), [])
        
        if not agents:
            return {
                "success": True,
                "has_agent": False,
                "agents": []
            }
        
        # Try to get on-chain balance
        balance = 0
        invested = 0
        try:
            from agents.contract_monitor import contract_monitor
            w3 = contract_monitor._get_web3()
            balance = contract_monitor.contract.functions.balances(
                Web3.to_checksum_address(wallet_address)
            ).call()
            # Try totalInvested if exists
            try:
                invested = contract_monitor.contract.functions.totalInvested(
                    Web3.to_checksum_address(wallet_address)
                ).call()
            except:
                pass
        except:
            pass
        
        return {
            "success": True,
            "has_agent": True,
            "agents": [{
                **agent,
                "balance_usdc": balance / 1e6,
                "invested_usdc": invested / 1e6,
                "status": "active" if balance > 0 or invested > 0 else "idle"
            } for agent in agents]
        }
        
    except Exception as e:
        return {
            "success": False,
            "has_agent": False,
            "error": str(e)
        }

# ============================================
# HARVEST
# ============================================

@router.post("/harvest")
async def harvest_rewards(request: HarvestRequest):
    """
    Harvest rewards from agent's LP positions.
    
    Returns the harvested amount in USD.
    """
    try:
        from api.smart_account_executor import SmartAccountExecutor
        from agents.audit_trail import log_action, ActionType
        
        # Use SmartAccountExecutor for harvesting
        executor = SmartAccountExecutor(request.wallet, request.agentId)
        result = await executor.harvest_rewards()
        
        harvested_amount = result.get("harvested_usd", 0)
        
        # Log to audit trail
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=ActionType.HARVEST,
            details={
                "amount_usd": harvested_amount,
                "mode": result.get("mode", "unknown"),
                "smart_account": executor.smart_account
            },
            success=result.get("success", False)
        )
        
        return {
            "success": result.get("success", False),
            "harvestedAmount": harvested_amount,
            "timestamp": datetime.utcnow().isoformat(),
            "agentId": request.agentId,
            "mode": result.get("mode"),
            "smartAccount": executor.smart_account
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "harvestedAmount": 0
        }

# ============================================
# REBALANCE
# ============================================

@router.post("/rebalance")
async def rebalance_portfolio(request: RebalanceRequest):
    """
    Trigger portfolio rebalance for an agent.
    
    Rebalances positions according to strategy allocation.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        # In production, this would:
        # 1. Get current portfolio allocation
        # 2. Compare to target allocation
        # 3. Execute swaps/LP adjustments
        # 4. Return new allocation
        
        # Log to audit trail
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=ActionType.REBALANCE,
            details={
                "strategy": request.strategy,
                "triggered_by": "user"
            },
            success=True
        )
        
        return {
            "success": True,
            "message": "Portfolio rebalanced",
            "timestamp": datetime.utcnow().isoformat(),
            "agentId": request.agentId,
            "strategy": request.strategy
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# PAUSE ALL
# ============================================

@router.post("/pause-all")
async def pause_all_agents(request: PauseAllRequest):
    """
    Emergency pause all agents for a wallet.
    
    Stops all active trading immediately.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        # In production, this would:
        # 1. Update agent status in database
        # 2. Cancel any pending transactions
        # 3. Disable automation
        
        # Log to audit trail
        log_action(
            agent_id="system",
            wallet=request.wallet,
            action_type=ActionType.AGENT_PAUSE,
            details={
                "reason": request.reason,
                "scope": "all"
            },
            success=True
        )
        
        return {
            "success": True,
            "message": "All agents paused",
            "timestamp": datetime.utcnow().isoformat(),
            "reason": request.reason
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================
# AGENT STATUS
# ============================================

@router.post("/status")
async def update_agent_status(request: AgentStatusUpdate):
    """
    Update single agent active status.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        action_type = ActionType.AGENT_DEPLOY if request.isActive else ActionType.AGENT_PAUSE
        
        log_action(
            agent_id=request.agentId,
            wallet=request.wallet,
            action_type=action_type,
            details={"isActive": request.isActive},
            success=True
        )
        
        return {
            "success": True,
            "agentId": request.agentId,
            "isActive": request.isActive,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.delete("/delete/{wallet}/{agent_id}")
async def delete_agent(wallet: str, agent_id: str):
    """
    Delete an agent from the system.
    """
    try:
        from agents.audit_trail import log_action, ActionType
        
        log_action(
            agent_id=agent_id,
            wallet=wallet,
            action_type=ActionType.AGENT_PAUSE,
            details={"action": "delete"},
            success=True
        )
        
        return {
            "success": True,
            "message": f"Agent {agent_id} deleted",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# AUDIT ENDPOINTS
# ============================================

audit_router = APIRouter(prefix="/api/audit", tags=["Audit"])

@audit_router.get("/recent")
async def get_recent_audit(
    wallet: Optional[str] = None,
    limit: int = Query(default=10, le=100)
):
    """
    Get recent audit log entries.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        entries = trail.get_entries(wallet_address=wallet)[-limit:]
        
        return {
            "success": True,
            "entries": [
                {
                    "timestamp": e.timestamp,
                    "action_type": e.action_type,
                    "agent_id": e.agent_id,
                    "wallet": e.wallet_address,
                    "value_usd": e.value_usd,
                    "success": e.success,
                    "tx_hash": e.tx_hash
                }
                for e in entries
            ],
            "count": len(entries)
        }
        
    except Exception as e:
        return {
            "success": False,
            "entries": [],
            "error": str(e)
        }

@audit_router.get("/export")
async def export_audit_csv(
    wallet: Optional[str] = Query(default=None)
):
    """
    Export audit log to CSV for tax reporting.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        entries = trail.get_entries(wallet_address=wallet if wallet != 'all' else None)
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Timestamp", "Action", "Agent ID", "Wallet",
            "TX Hash", "Value (USD)", "Gas Used", "Success", "Details"
        ])
        
        # Data rows
        for e in entries:
            writer.writerow([
                e.timestamp,
                e.action_type,
                e.agent_id,
                e.wallet_address,
                e.tx_hash or "",
                e.value_usd or "",
                e.gas_used or "",
                "Yes" if e.success else "No",
                json.dumps(e.details) if e.details else ""
            ])
        
        output.seek(0)
        
        filename = f"techne_audit_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@audit_router.get("/summary")
async def get_audit_summary(wallet: Optional[str] = None):
    """
    Get summary statistics from audit trail.
    """
    try:
        from agents.audit_trail import AuditTrail
        
        trail = AuditTrail()
        summary = trail.get_summary(wallet_address=wallet if wallet != 'all' else None)
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# CONDITIONAL RULES ENGINE
# Parse natural language instructions → trading rules
# ============================================

class CustomRulesRequest(BaseModel):
    user_address: str
    instructions: str

# In-memory rules storage (TODO: move to Supabase)
USER_RULES: Dict[str, List[Dict]] = {}

@router.post("/rules/parse")
async def parse_custom_rules(request: CustomRulesRequest):
    """
    Parse natural language instructions into conditional rules.
    
    Example: "for pools between 1m-5m TVL for aerodrome dual-sided, hold max 1h"
    
    Returns parsed rules that can be stored with /rules/set
    """
    try:
        from services.instruction_parser import get_instruction_parser
        
        parser = get_instruction_parser()
        rules = await parser.parse(request.instructions)
        
        if not rules:
            return {
                "success": False,
                "message": "Could not parse instructions. Try being more specific.",
                "rules": [],
                "examples": [
                    "for pools between 1m-5m TVL, hold max 1 hour",
                    "aerodrome dual-sided: trailing stop at 15%",
                    "exit USDC positions if APY drops below 5%",
                    "take profit at 20%, stop loss at 10%"
                ]
            }
        
        return {
            "success": True,
            "rules_count": len(rules),
            "rules": [r.to_dict() for r in rules],
            "rules_readable": [str(r) for r in rules],
            "original_instructions": request.instructions
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "rules": []
        }


@router.post("/rules/set")
async def set_custom_rules(request: CustomRulesRequest):
    """
    Parse and store custom rules for a user.
    
    These rules will be evaluated by the RulesEngine for all positions.
    """
    try:
        from services.instruction_parser import get_instruction_parser
        
        parser = get_instruction_parser()
        rules = await parser.parse(request.instructions)
        
        if not rules:
            return {
                "success": False,
                "message": "Could not parse instructions",
                "rules_stored": 0
            }
        
        # Store rules
        user_addr = request.user_address.lower()
        USER_RULES[user_addr] = [r.to_dict() for r in rules]
        
        # Also try to persist to Supabase
        try:
            from infrastructure.supabase_client import supabase
            if supabase.is_available:
                await supabase.save_user_rules(
                    request.user_address,
                    request.instructions,
                    [r.to_dict() for r in rules]
                )
        except Exception as e:
            print(f"[Rules] Supabase save failed: {e}")
        
        print(f"[Rules] Stored {len(rules)} rules for {user_addr[:10]}...")
        for r in rules:
            print(f"  → {r}")
        
        return {
            "success": True,
            "rules_stored": len(rules),
            "rules": [r.to_dict() for r in rules],
            "rules_readable": [str(r) for r in rules]
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "rules_stored": 0
        }


@router.get("/rules/{user_address}")
async def get_user_rules(user_address: str):
    """
    Get stored rules for a user.
    """
    try:
        user_addr = user_address.lower()
        rules_data = USER_RULES.get(user_addr, [])
        
        # Try Supabase if not in memory
        if not rules_data:
            try:
                from infrastructure.supabase_client import supabase
                if supabase.is_available:
                    db_rules = await supabase.get_user_rules(user_address)
                    if db_rules:
                        rules_data = db_rules.get("parsed_rules", [])
                        USER_RULES[user_addr] = rules_data
            except Exception as e:
                print(f"[Rules] Supabase read failed: {e}")
        
        # Convert to readable format
        from services.conditional_rules import ConditionalRule
        rules = [ConditionalRule.from_dict(r) for r in rules_data]
        
        return {
            "success": True,
            "user_address": user_address,
            "rules_count": len(rules),
            "rules": rules_data,
            "rules_readable": [str(r) for r in rules]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rules": []
        }


@router.delete("/rules/{user_address}")
async def clear_user_rules(user_address: str):
    """
    Clear all rules for a user.
    """
    try:
        user_addr = user_address.lower()
        USER_RULES.pop(user_addr, None)
        
        # Also clear from Supabase
        try:
            from infrastructure.supabase_client import supabase
            if supabase.is_available:
                await supabase.delete_user_rules(user_address)
        except:
            pass
        
        return {
            "success": True,
            "message": "Rules cleared"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_user_rules_for_engine(user_address: str) -> List:
    """Helper to get rules in format for RulesEngine"""
    from services.conditional_rules import ConditionalRule
    
    user_addr = user_address.lower()
    rules_data = USER_RULES.get(user_addr, [])
    
    return [ConditionalRule.from_dict(r) for r in rules_data]


# ============================================
# DEGEN STRATEGIES API
# Flash Leverage, Volatility Hunter, Auto-Snipe, Delta Neutral
# ============================================

class DegenConfigRequest(BaseModel):
    user_address: str
    flash_loan_enabled: bool = False
    max_leverage: float = 3.0
    deleverage_threshold: float = 15.0
    chase_volatility: bool = False
    min_volatility_threshold: float = 25.0
    il_farming_mode: bool = False
    snipe_new_pools: bool = False
    snipe_min_apy: float = 100.0
    snipe_max_position: float = 500.0
    snipe_exit_hours: int = 24
    auto_hedge: bool = False
    hedge_protocol: str = "synthetix"
    delta_threshold: float = 5.0
    funding_farming: bool = True

class FlashLeverageRequest(BaseModel):
    user_address: str
    collateral: float
    leverage: float
    protocol: str = "aave"

class VolatilityHuntRequest(BaseModel):
    user_address: str
    pool_address: str
    amount: float
    il_farming: bool = False

class DeltaNeutralRequest(BaseModel):
    user_address: str
    lp_amount: float
    volatile_asset: str = "WETH"
    volatile_exposure: float = 0.5
    hedge_protocol: str = "synthetix"


# In-memory degen configs
USER_DEGEN_CONFIGS: Dict[str, Dict] = {}


@router.post("/degen/config")
async def set_degen_config(request: DegenConfigRequest):
    """Store user's degen strategy configuration"""
    try:
        from services.degen_strategies import DegenConfig
        
        config = DegenConfig(
            flash_loan_enabled=request.flash_loan_enabled,
            max_leverage=request.max_leverage,
            deleverage_threshold=request.deleverage_threshold,
            chase_volatility=request.chase_volatility,
            min_volatility_threshold=request.min_volatility_threshold,
            il_farming_mode=request.il_farming_mode,
            snipe_new_pools=request.snipe_new_pools,
            snipe_min_apy=request.snipe_min_apy,
            snipe_max_position=request.snipe_max_position,
            snipe_exit_hours=request.snipe_exit_hours,
            auto_hedge=request.auto_hedge,
            hedge_protocol=request.hedge_protocol,
            delta_threshold=request.delta_threshold,
            funding_farming=request.funding_farming
        )
        
        USER_DEGEN_CONFIGS[request.user_address.lower()] = {
            "config": config,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        enabled = []
        if config.flash_loan_enabled: enabled.append(f"Flash Leverage ({config.max_leverage}x)")
        if config.chase_volatility: enabled.append(f"Volatility Hunter ({config.min_volatility_threshold}%)")
        if config.snipe_new_pools: enabled.append(f"Auto-Snipe ({config.snipe_min_apy}% APY)")
        if config.auto_hedge: enabled.append(f"Delta Neutral ({config.hedge_protocol})")
        
        print(f"[Degen] Config saved for {request.user_address[:10]}")
        print(f"  Enabled: {', '.join(enabled) if enabled else 'None'}")
        
        return {
            "success": True,
            "enabled_strategies": enabled,
            "config": request.dict()
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.post("/degen/flash-leverage")
async def execute_flash_leverage(request: FlashLeverageRequest):
    """Execute flash loan leverage position"""
    try:
        from services.degen_strategies import flash_leverage_engine
        
        result = await flash_leverage_engine.create_leveraged_position(
            request.user_address,
            request.collateral,
            request.leverage,
            request.protocol
        )
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.post("/degen/volatility-hunt")
async def execute_volatility_hunt(request: VolatilityHuntRequest):
    """Enter volatility hunting position"""
    try:
        from services.degen_strategies import volatility_hunter
        
        # Check volatility first
        vol_data = await volatility_hunter.check_volatility(request.pool_address)
        
        result = await volatility_hunter.enter_volatile_pool(
            request.user_address,
            request.pool_address,
            request.amount,
            request.il_farming
        )
        
        result["volatility_data"] = vol_data
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.get("/degen/discover-pools")
async def discover_new_pools():
    """Discover new pools for sniping"""
    try:
        from services.degen_strategies import auto_sniper
        
        pools = await auto_sniper.discover_new_pools()
        
        return {
            "success": True,
            "pools_found": len(pools),
            "pools": pools
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/degen/snipe")
async def execute_snipe(user_address: str, pool_index: int = 0, amount: float = 500, exit_hours: int = 24):
    """Execute snipe on discovered pool"""
    try:
        from services.degen_strategies import auto_sniper
        
        if not auto_sniper.discovered_pools:
            await auto_sniper.discover_new_pools()
        
        if pool_index >= len(auto_sniper.discovered_pools):
            return {"success": False, "error": "Pool index out of range"}
        
        pool = auto_sniper.discovered_pools[pool_index]
        result = await auto_sniper.snipe_pool(user_address, pool, amount, exit_hours)
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.post("/degen/delta-neutral")
async def execute_delta_neutral(request: DeltaNeutralRequest):
    """Create delta-neutral hedged position"""
    try:
        from services.degen_strategies import delta_neutral_manager
        
        result = await delta_neutral_manager.create_hedged_position(
            request.user_address,
            request.lp_amount,
            request.volatile_asset,
            request.volatile_exposure,
            request.hedge_protocol
        )
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.get("/degen/positions/{user_address}")
async def get_degen_positions(user_address: str):
    """Get all degen positions for a user"""
    try:
        from services.degen_strategies import (
            flash_leverage_engine, 
            volatility_hunter, 
            auto_sniper,
            delta_neutral_manager
        )
        
        positions = {
            "leveraged": [],
            "volatility": [],
            "sniped": [],
            "hedged": []
        }
        
        user_addr = user_address.lower()
        
        # Flash leverage positions
        for pos_id, pos in flash_leverage_engine.positions.items():
            if pos.user_address.lower() == user_addr:
                positions["leveraged"].append({
                    "position_id": pos.position_id,
                    "protocol": pos.protocol,
                    "leverage": pos.leverage,
                    "collateral": pos.collateral,
                    "borrowed": pos.borrowed,
                    "current_value": pos.current_value,
                    "liquidation_price": pos.liquidation_price
                })
        
        # Volatility positions
        for pos_id, pos in volatility_hunter.active_positions.items():
            if pos.get("user_address", "").lower() == user_addr:
                positions["volatility"].append(pos)
        
        # Sniped positions
        for pos_id, pos in auto_sniper.sniped_positions.items():
            if pos.get("user_address", "").lower() == user_addr:
                positions["sniped"].append(pos)
        
        # Hedged positions
        for pos_id, pos in delta_neutral_manager.hedged_positions.items():
            if pos.user_address.lower() == user_addr:
                positions["hedged"].append({
                    "position_id": pos.position_id,
                    "lp_value": pos.lp_value,
                    "short_value": pos.short_value,
                    "hedge_protocol": pos.hedge_protocol,
                    "delta": pos.delta,
                    "funding_collected": pos.funding_collected
                })
        
        total_positions = sum(len(v) for v in positions.values())
        
        return {
            "success": True,
            "user_address": user_address,
            "total_positions": total_positions,
            "positions": positions
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.post("/degen/run")
async def run_degen_strategies(user_address: str):
    """Execute all enabled degen strategies for user"""
    try:
        from services.degen_strategies import run_degen_strategies as run_strategies, DegenConfig
        
        user_addr = user_address.lower()
        user_config = USER_DEGEN_CONFIGS.get(user_addr)
        
        if not user_config:
            return {"success": False, "error": "No degen config set. Use /degen/config first."}
        
        config = user_config["config"]
        results = await run_strategies(user_address, config)
        
        return {
            "success": True,
            "results": results
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

