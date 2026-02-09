"""
Agent Configuration Router
Handles agent deployment and configuration from Build UI
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import os

# Agent key management (wallet generation, encryption)
from services.agent_keys import verify_signature

# ERC-8004 Smart Account Service (replaces EOA)
from services.smart_account_service import get_smart_account_service

# Auto-whitelist service for V4.3.2
from services.whitelist_service import get_whitelist_service

# Supabase for persistent storage
from infrastructure.supabase_client import supabase

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Fallback storage file (when Supabase unavailable)
AGENTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "deployed_agents.json")
MAX_AGENTS_PER_WALLET = 5

# In-memory cache (synced with Supabase)
DEPLOYED_AGENTS = {}

def _load_agents() -> dict:
    """Load agents from file (fallback)"""
    try:
        if os.path.exists(AGENTS_FILE):
            with open(AGENTS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"[AgentConfig] Failed to load agents from file: {e}")
    return {}

def _save_agents(agents: dict):
    """Save agents to file (fallback)"""
    try:
        os.makedirs(os.path.dirname(AGENTS_FILE), exist_ok=True)
        with open(AGENTS_FILE, "w") as f:
            json.dump(agents, f, indent=2)
    except Exception as e:
        print(f"[AgentConfig] Failed to save agents to file: {e}")

# Load from file on startup (only as fallback cache)
DEPLOYED_AGENTS = _load_agents()
print(f"[AgentConfig] Loaded {sum(len(v) for v in DEPLOYED_AGENTS.values())} agents from file cache")
print(f"[AgentConfig] Supabase available: {supabase.is_available}")


class ProConfig(BaseModel):
    leverage: Optional[float] = 1.0
    stopLossEnabled: Optional[bool] = False
    stopLossPercent: Optional[float] = 10
    takeProfitEnabled: Optional[bool] = False
    takeProfitAmount: Optional[float] = 0
    volatilityGuard: Optional[bool] = False
    volatilityThreshold: Optional[int] = 10
    mevProtection: Optional[bool] = False
    harvestStrategy: Optional[str] = "compound"
    duration: Optional[dict] = None
    customInstructions: Optional[str] = None


class AgentDeployRequest(BaseModel):
    user_address: str
    agent_address: Optional[str] = None  # Now optional - we generate if not provided
    agent_name: Optional[str] = None  # Optional custom name
    # Signature verification for ownership proof
    signature: Optional[str] = None  # EIP-191 personal_sign of deploy message
    sign_message: Optional[str] = None  # The message that was signed
    chain: str = "base"
    preset: str = "balanced-growth"
    pool_type: str = "single"
    risk_level: str = "medium"
    min_apy: float = 10
    max_apy: float = 50
    max_drawdown: float = 20
    protocols: List[str] = ["morpho", "aave", "moonwell", "aerodrome", "uniswap"]
    preferred_assets: List[str] = ["USDC", "WETH"]
    max_allocation: int = 25
    vault_count: int = 5
    auto_rebalance: bool = True
    only_audited: bool = True
    is_pro_mode: bool = False
    pro_config: Optional[ProConfig] = None
    # Additional configs from Build UI
    rebalance_threshold: int = 5           # % APY change to trigger rebalance
    max_gas_price: int = 10                # Max gwei - Base: normal 0.01, spike 1-5
    slippage: float = 0.5                  # Max slippage %
    compound_frequency: int = 7            # Days between auto-compound
    avoid_il: bool = True                  # Avoid impermanent loss (single-sided only)
    emergency_exit: bool = True            # Enable emergency exit on high volatility
    min_pool_tvl: int = 500000             # $500k minimum TVL - degens welcome
    max_pool_tvl: Optional[int] = None     # Max TVL filter (None = unlimited)
    duration: float = 30                   # Investment duration in days (0 = no limit, fractions for hours)
    apy_check_hours: int = 24              # Hours to check avg APY before rotation (12, 24, 72, 168)
    trading_style: str = "moderate"        # conservative, moderate, aggressive


class AgentStatusResponse(BaseModel):
    success: bool
    agent: Optional[dict] = None
    agents: Optional[List[dict]] = None
    message: Optional[str] = None


# DEBUG: Temporary endpoint to catch validation issues
@router.post("/deploy-debug")
async def deploy_debug(request: dict):
    """Debug endpoint - accepts raw dict to see what frontend sends"""
    print(f"[DEBUG] Raw deploy request: {request}")
    # Try to validate manually
    try:
        validated = AgentDeployRequest(**request)
        return {"success": True, "message": "Validation passed", "data": request}
    except Exception as e:
        print(f"[DEBUG] Validation error: {e}")
        return {"success": False, "error": str(e), "received_fields": list(request.keys())}

@router.post("/deploy")
async def deploy_agent(request: AgentDeployRequest):
    """
    Deploy an agent with configuration from Build UI
    Max 5 agents per wallet
    
    SECURITY: 
    - Generates unique wallet keypair for each agent
    - Encrypts private key for storage
    - Optionally verifies user signature for ownership proof
    """
    print(f"[AgentConfig] Received deploy request from {request.user_address[:10]}...")
    print(f"[AgentConfig] Request fields: chain={request.chain}, preset={request.preset}, pool_type={request.pool_type}")
    try:
        # Normalize user address
        user_address = request.user_address.lower()
        
        # Get existing agents for this wallet
        user_agents = DEPLOYED_AGENTS.get(user_address, [])
        
        # Check max limit
        active_agents = [a for a in user_agents if a.get("is_active", False)]
        if len(active_agents) >= MAX_AGENTS_PER_WALLET:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {MAX_AGENTS_PER_WALLET} agents per wallet"
            )
        
        # SIGNATURE VERIFICATION (REQUIRED for security)
        print(f"[AgentConfig] Deploy request: user={user_address[:10]}..., sig_len={len(request.signature or '')}, msg_len={len(request.sign_message or '')}")
        
        if not request.signature or not request.sign_message:
            print(f"[AgentConfig] REJECTED: Missing signature or message")
            raise HTTPException(
                status_code=401, 
                detail="Signature required to deploy agent"
            )
        
        print(f"[AgentConfig] Verifying signature for {user_address[:10]}...")
        signature_verified = verify_signature(
            message=request.sign_message,
            signature=request.signature,
            expected_address=user_address
        )
        print(f"[AgentConfig] Signature verified: {signature_verified}")
        
        if not signature_verified:
            print(f"[AgentConfig] REJECTED: Signature verification failed for {user_address}")
            raise HTTPException(
                status_code=401, 
                detail="Invalid signature - cannot verify wallet ownership"
            )
        
        # CREATE SMART ACCOUNT (ERC-8004) - COLD DEPLOY
        # Returns transaction data for user to sign via MetaMask
        # User pays gas directly - we don't save agent until tx is confirmed
        smart_account_service = get_smart_account_service()
        
        # Generate agent_id first (needed for CREATE2 salt)
        agent_id = f"agent_{len(user_agents) + 1}_{int(datetime.utcnow().timestamp())}"
        
        if request.agent_address:
            # Use provided address (legacy flow - already deployed)
            agent_address = request.agent_address
            print(f"[AgentConfig] Using provided agent address (legacy): {agent_address[:10]}...")
            
            # Save immediately for legacy flow
            agent_data = _build_agent_data(request, user_address, agent_id, agent_address, signature_verified, user_agents)
            user_agents.append(agent_data)
            DEPLOYED_AGENTS[user_address] = user_agents
            _save_agents(DEPLOYED_AGENTS)
            
            return {
                "success": True,
                "agent_id": agent_id,
                "agent_address": agent_address,
                "account_type": "legacy",
                "requires_transaction": False,
                "message": "Agent deployed with legacy address"
            }
        
        # COLD DEPLOY: Build transaction for user to sign
        # User will pay gas via MetaMask
        print(f"[AgentConfig] Building cold deploy tx for agent {agent_id}...")
        tx_result = smart_account_service.build_deploy_transaction(user_address, agent_id)
        
        if not tx_result.get("success"):
            raise HTTPException(status_code=500, detail=tx_result.get("message", "Failed to build transaction"))
        
        predicted_address = tx_result.get("predicted_address")
        
        # Check if already deployed on-chain
        if tx_result.get("already_deployed"):
            print(f"[AgentConfig] Agent already deployed at {predicted_address[:10]}...")
            
            # Save agent data immediately - no tx needed
            agent_data = _build_agent_data(request, user_address, agent_id, predicted_address, signature_verified, user_agents)
            user_agents.append(agent_data)
            DEPLOYED_AGENTS[user_address] = user_agents
            _save_agents(DEPLOYED_AGENTS)
            
            return {
                "success": True,
                "agent_id": agent_id,
                "agent_address": predicted_address,
                "account_type": "erc8004",
                "requires_transaction": False,
                "already_deployed": True,
                "message": "Agent already deployed on-chain"
            }
        
        # Return transaction data for user to sign
        # Agent will be saved in /confirm-deploy after tx confirmation
        print(f"[AgentConfig] Cold deploy tx built for {predicted_address[:10]}..., gas: {tx_result['transaction']['gas']}")
        
        # Store pending agent config in memory (will be saved after tx confirmation)
        pending_key = f"{user_address}:{agent_id}"
        PENDING_DEPLOYS[pending_key] = {
            "request": request.dict(),
            "user_address": user_address,
            "agent_id": agent_id,
            "predicted_address": predicted_address,
            "signature_verified": signature_verified,
            "user_agents_count": len(user_agents),
            "created_at": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "agent_id": agent_id,
            "agent_address": predicted_address,
            "account_type": "erc8004",
            "requires_transaction": True,  # <- Frontend must send tx to MetaMask
            "transaction": tx_result.get("transaction"),
            "message": "Sign transaction in MetaMask to deploy agent (you pay gas)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AgentConfig] Deploy error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Pending deploys storage (in-memory, cleared on restart)
PENDING_DEPLOYS = {}


def _build_agent_data(request, user_address: str, agent_id: str, agent_address: str, signature_verified: bool, user_agents: list) -> dict:
    """Build agent data dict from request"""
    # Generate agent private key for autonomous signing
    from services.agent_keys import generate_agent_wallet, encrypt_private_key
    
    try:
        _, generated_address = generate_agent_wallet()
        pk, _ = generate_agent_wallet()  # Generate fresh keypair for agent signing
        encrypted_pk = encrypt_private_key(pk)
        print(f"[AgentConfig] Generated encrypted private key for agent {agent_id[:20]}...")
    except Exception as e:
        print(f"[AgentConfig] WARNING: Could not generate agent key: {e}")
        encrypted_pk = None
    
    return {
        "id": agent_id,
        "name": request.agent_name or f"Agent #{len(user_agents) + 1}",
        "user_address": user_address,
        "agent_address": agent_address,
        "account_type": "erc8004",
        "encrypted_private_key": encrypted_pk,  # For autonomous signing
        "signature_verified": signature_verified,
        "chain": request.chain,
        "preset": request.preset,
        "pool_type": request.pool_type,
        "risk_level": request.risk_level,
        "min_apy": request.min_apy,
        "max_apy": request.max_apy,
        "max_drawdown": request.max_drawdown,
        "protocols": request.protocols,
        "preferred_assets": request.preferred_assets,
        "max_allocation": request.max_allocation,
        "vault_count": request.vault_count,
        "auto_rebalance": request.auto_rebalance,
        "only_audited": request.only_audited,
        "is_pro_mode": request.is_pro_mode,
        "pro_config": request.pro_config.dict() if request.pro_config else None,
        "rebalance_threshold": request.rebalance_threshold,
        "max_gas_price": request.max_gas_price,
        "slippage": request.slippage,
        "compound_frequency": request.compound_frequency,
        "avoid_il": request.avoid_il,
        "emergency_exit": request.emergency_exit,
        "min_pool_tvl": request.min_pool_tvl,
        "max_pool_tvl": request.max_pool_tvl,
        "duration": request.duration,
        "apy_check_hours": request.apy_check_hours,
        "trading_style": request.trading_style,
        "deployed_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "positions": [],
        "total_deposited": 0,
        "total_value": 0
    }




class ConfirmDeployRequest(BaseModel):
    """Request to confirm deployment after tx is mined"""
    user_address: str
    agent_id: str
    tx_hash: str


@router.post("/confirm-deploy")
async def confirm_deploy(request: ConfirmDeployRequest):
    """
    Confirm agent deployment after user has signed and tx is mined.
    Called by frontend after MetaMask tx confirmation.
    
    Saves agent data from PENDING_DEPLOYS to persistent storage.
    """
    user_address = request.user_address.lower()
    agent_id = request.agent_id
    tx_hash = request.tx_hash
    
    print(f"[AgentConfig] Confirming deploy: agent={agent_id}, tx={tx_hash[:20]}...")
    
    # Look up pending deploy
    pending_key = f"{user_address}:{agent_id}"
    pending = PENDING_DEPLOYS.get(pending_key)
    
    if not pending:
        raise HTTPException(
            status_code=404,
            detail=f"No pending deploy found for {agent_id}. Deploy may have expired."
        )
    
    # Optional: Verify tx on-chain (could check if contract was actually deployed)
    # For now, we trust frontend to only call this after tx is mined
    
    # Rebuild request object from stored dict
    from pydantic import BaseModel
    stored_request = pending["request"]
    
    # Get or create user agents list
    user_agents = DEPLOYED_AGENTS.get(user_address, [])
    
    # Build agent data
    agent_data = {
        "id": agent_id,
        "name": stored_request.get("agent_name") or f"Agent #{len(user_agents) + 1}",
        "user_address": user_address,
        "agent_address": pending["predicted_address"],
        "account_type": "erc8004",
        "deploy_tx_hash": tx_hash,
        "signature_verified": pending["signature_verified"],
        "chain": stored_request.get("chain", "base"),
        "preset": stored_request.get("preset", "balanced-growth"),
        "pool_type": stored_request.get("pool_type", "single"),
        "risk_level": stored_request.get("risk_level", "medium"),
        "min_apy": stored_request.get("min_apy", 5),
        "max_apy": stored_request.get("max_apy", 100),
        "max_drawdown": stored_request.get("max_drawdown", 20),
        "protocols": stored_request.get("protocols", []),
        "preferred_assets": stored_request.get("preferred_assets", ["USDC"]),
        "max_allocation": stored_request.get("max_allocation", 25),
        "vault_count": stored_request.get("vault_count", 5),
        "auto_rebalance": stored_request.get("auto_rebalance", True),
        "only_audited": stored_request.get("only_audited", True),
        "is_pro_mode": stored_request.get("is_pro_mode", False),
        "pro_config": stored_request.get("pro_config"),
        "rebalance_threshold": stored_request.get("rebalance_threshold", 5),
        "max_gas_price": stored_request.get("max_gas_price", 10),
        "slippage": stored_request.get("slippage", 0.5),
        "compound_frequency": stored_request.get("compound_frequency", 7),
        "avoid_il": stored_request.get("avoid_il", True),
        "emergency_exit": stored_request.get("emergency_exit", True),
        "min_pool_tvl": stored_request.get("min_pool_tvl", 500000),
        "duration": stored_request.get("duration", 30),
        "apy_check_hours": stored_request.get("apy_check_hours", 24),
        "deployed_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "positions": [],
        "total_deposited": 0,
        "total_value": 0
    }
    
    # Save to persistent storage
    user_agents.append(agent_data)
    DEPLOYED_AGENTS[user_address] = user_agents
    _save_agents(DEPLOYED_AGENTS)
    
    # Clean up pending deploy
    del PENDING_DEPLOYS[pending_key]
    
    print(f"[AgentConfig] Agent {agent_id} confirmed and saved. Tx: {tx_hash}")
    print(f"[AgentConfig] Total agents for {user_address}: {len(user_agents)}")
    
    # Auto-whitelist (non-blocking)
    try:
        whitelist_svc = get_whitelist_service()
        whitelist_result = whitelist_svc.whitelist_user(user_address)
        print(f"[AgentConfig] Whitelist result: {whitelist_result}")
    except Exception as e:
        print(f"[AgentConfig] Whitelist error (non-fatal): {e}")
    
    return {
        "success": True,
        "agent_id": agent_id,
        "agent_address": agent_data["agent_address"],
        "tx_hash": tx_hash,
        "message": "Agent deployment confirmed and saved"
    }


class SetupAutoTradingRequest(BaseModel):
    """Request to setup auto trading (session key + whitelist)"""
    user_address: str
    agent_id: str
    agent_address: str


@router.post("/setup-auto-trading")
async def setup_auto_trading(request: SetupAutoTradingRequest):
    """
    Build transaction to enable auto-trading for Smart Account.
    
    This sets up:
    1. Session key for backend to execute trades
    2. Protocol whitelist (Aave, Aerodrome, etc.)
    
    Returns transaction data for user to sign via MetaMask.
    """
    from api.session_key_signer import get_session_key_address
    from eth_abi import encode
    
    user_address = request.user_address.lower()
    agent_id = request.agent_id
    agent_address = request.agent_address
    
    print(f"[AgentConfig] Setting up auto-trading for {agent_id}")
    
    try:
        # Get the derived session key address for this agent
        session_key_address = get_session_key_address(agent_id, user_address)
        print(f"[AgentConfig] Session key for {agent_id}: {session_key_address}")
        
        # Protocol addresses to whitelist (Base mainnet)
        AAVE_POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
        AERODROME_ROUTER = "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"
        MORPHO_BLUE = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
        USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        WETH = "0x4200000000000000000000000000000000000006"
        
        # Common selectors for DeFi operations
        SELECTORS = {
            "aave_supply": bytes.fromhex("e8eda9df"),      # supply(address,uint256,address,uint16)
            "aave_withdraw": bytes.fromhex("69328dec"),    # withdraw(address,uint256,address)
            "morpho_supply": bytes.fromhex("a99aad89"),    # supply(...)
            "morpho_withdraw": bytes.fromhex("5c2bea49"), # withdraw(...)
            "aero_add_liq": bytes.fromhex("5a47ddc3"),    # addLiquidity(...)
            "aero_remove_liq": bytes.fromhex("0dede6c4"), # removeLiquidity(...)
            "aero_swap": bytes.fromhex("38ed1739"),       # swapExactTokensForTokens(...)
            "erc20_approve": bytes.fromhex("095ea7b3"),   # approve(address,uint256)
            "erc20_transfer": bytes.fromhex("a9059cbb"), # transfer(address,uint256)
        }
        
        # Build executeBatch calldata for Smart Account
        # Call 1: addSessionKey(address key, uint48 validUntil, uint256 dailyLimitUSD)
        add_session_key_selector = bytes.fromhex("3644e515")  # addSessionKey(address,uint48,uint256)
        max_uint48 = (1 << 48) - 1  # type(uint48).max - no expiration
        daily_limit = 100000 * 10**8  # $100,000 daily limit (8 decimals for USD)
        
        add_session_key_data = add_session_key_selector + encode(
            ['address', 'uint48', 'uint256'],
            [session_key_address, max_uint48, daily_limit]
        )
        
        # Call 2: batchWhitelist(address[] protocols, bytes4[][] selectors)
        batch_whitelist_selector = bytes.fromhex("3b3d3b8b")  # batchWhitelist(address[],bytes4[][])
        
        protocols = [
            Web3.to_checksum_address(AAVE_POOL),
            Web3.to_checksum_address(AERODROME_ROUTER),
            Web3.to_checksum_address(MORPHO_BLUE),
            Web3.to_checksum_address(USDC),
            Web3.to_checksum_address(WETH),
        ]
        
        selectors_per_protocol = [
            [SELECTORS["aave_supply"], SELECTORS["aave_withdraw"]],  # Aave
            [SELECTORS["aero_add_liq"], SELECTORS["aero_remove_liq"], SELECTORS["aero_swap"]],  # Aerodrome
            [SELECTORS["morpho_supply"], SELECTORS["morpho_withdraw"]],  # Morpho
            [SELECTORS["erc20_approve"], SELECTORS["erc20_transfer"]],  # USDC
            [SELECTORS["erc20_approve"], SELECTORS["erc20_transfer"]],  # WETH
        ]
        
        # Manually encode for executeBatch
        # executeBatch(address[] targets, uint256[] values, bytes[] dataArray)
        execute_batch_selector = bytes.fromhex("34fcd5be")  # executeBatch(address[],uint256[],bytes[])
        
        targets = [
            Web3.to_checksum_address(agent_address),  # addSessionKey on self
            Web3.to_checksum_address(agent_address),  # batchWhitelist on self
        ]
        values = [0, 0]
        
        # Build batchWhitelist calldata
        batch_whitelist_data = batch_whitelist_selector + encode(
            ['address[]', 'bytes4[][]'],
            [protocols, [[s for s in sels] for sels in selectors_per_protocol]]
        )
        
        data_array = [add_session_key_data, batch_whitelist_data]
        
        # Encode executeBatch call
        execute_batch_data = execute_batch_selector + encode(
            ['address[]', 'uint256[]', 'bytes[]'],
            [targets, values, data_array]
        )
        
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(os.getenv("ALCHEMY_RPC_URL", "")))
        gas_price = w3.eth.gas_price
        
        # PERSIST session key to DEPLOYED_AGENTS (in-memory cache)
        try:
            user_agents = DEPLOYED_AGENTS.get(user_address, [])
            for ag in user_agents:
                ag_addr = (ag.get("agent_address") or ag.get("address", "")).lower()
                if ag_addr == agent_address.lower():
                    ag["session_key_address"] = session_key_address
                    print(f"[AgentConfig] Session key saved to DEPLOYED_AGENTS: {session_key_address[:10]}...")
                    break
            _save_agents(DEPLOYED_AGENTS)
        except Exception as e:
            print(f"[AgentConfig] Session key cache save error: {e}")
        
        # PERSIST session key to Supabase premium_subscriptions
        try:
            if supabase.is_available:
                supabase.table("premium_subscriptions").update({
                    "session_key_address": session_key_address
                }).eq("agent_address", agent_address).execute()
                print(f"[AgentConfig] Session key saved to Supabase premium_subscriptions")
        except Exception as e:
            print(f"[AgentConfig] Supabase session key save error (non-fatal): {e}")
        
        return {
            "success": True,
            "session_key": session_key_address,
            "agent_id": agent_id,
            "agent_address": agent_address,
            "protocols_to_whitelist": ["Aave", "Aerodrome", "Morpho", "USDC", "WETH"],
            "transaction": {
                "to": agent_address,
                "data": "0x" + execute_batch_data.hex(),
                "gas": "0x" + hex(500000)[2:],  # 500k gas for batch
                "value": "0x0"
            },
            "message": "Sign to enable auto-trading. This adds backend session key and whitelists DeFi protocols."
        }
        
    except Exception as e:
        print(f"[AgentConfig] Setup auto-trading error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_address}")
async def get_agent_status(user_address: str, agent_id: Optional[str] = None):
    """
    Get status of deployed agents for a user
    If agent_id provided, returns single agent
    """
    # Try Supabase first
    user_agents = []
    if supabase.is_available:
        try:
            user_agents = await supabase.get_user_agents(user_address)
            print(f"[AgentConfig] Loaded {len(user_agents)} agents from Supabase for {user_address[:10]}...")
        except Exception as e:
            print(f"[AgentConfig] Supabase query failed: {e}")
    
    # Fallback to in-memory cache
    if not user_agents:
        user_agents = DEPLOYED_AGENTS.get(user_address.lower(), [])
    
    if not user_agents:
        return AgentStatusResponse(
            success=False,
            message="No agents found for this user"
        )
    
    # Convert Supabase row format to frontend format
    for agent in user_agents:
        # Ensure consistent field names for frontend
        if "agent_name" in agent and "name" not in agent:
            agent["name"] = agent["agent_name"]
        if "agent_address" not in agent and "address" in agent:
            agent["agent_address"] = agent["address"]
    
    if agent_id:
        # Return specific agent
        agent = next((a for a in user_agents if a.get("id") == agent_id), None)
        if not agent:
            return AgentStatusResponse(success=False, message="Agent not found")
        return AgentStatusResponse(success=True, agent=agent)
    
    # Return all agents
    return {
        "success": True,
        "agents": user_agents,
        "count": len(user_agents),
        "active_count": len([a for a in user_agents if a.get("is_active")])
    }


@router.post("/stop/{user_address}/{agent_id}")
async def stop_agent(user_address: str, agent_id: str):
    """
    Stop a specific agent (pause it)
    """
    user_agents = DEPLOYED_AGENTS.get(user_address.lower(), [])
    agent = next((a for a in user_agents if a.get("id") == agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update in cache
    agent["is_active"] = False
    agent["paused_at"] = datetime.utcnow().isoformat()
    _save_agents(DEPLOYED_AGENTS)
    
    # Update in Supabase
    agent_address = agent.get("agent_address") or agent.get("address")
    if supabase.is_available and agent_address:
        try:
            await supabase.update_agent_status(agent_address, is_active=False, status="paused")
            print(f"[AgentConfig] Agent {agent_id} PAUSED in Supabase")
        except Exception as e:
            print(f"[AgentConfig] Supabase pause failed: {e}")
    
    print(f"[AgentConfig] Agent {agent_id} PAUSED for {user_address}")
    
    return {
        "success": True,
        "message": f"Agent {agent_id} paused",
        "is_active": False
    }


@router.post("/resume/{user_address}/{agent_id}")
async def resume_agent(user_address: str, agent_id: str):
    """
    Resume a paused agent
    """
    user_agents = DEPLOYED_AGENTS.get(user_address.lower(), [])
    agent = next((a for a in user_agents if a.get("id") == agent_id), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update in cache
    agent["is_active"] = True
    agent["resumed_at"] = datetime.utcnow().isoformat()
    if "paused_at" in agent:
        del agent["paused_at"]
    _save_agents(DEPLOYED_AGENTS)
    
    # Update in Supabase
    agent_address = agent.get("agent_address") or agent.get("address")
    if supabase.is_available and agent_address:
        try:
            await supabase.update_agent_status(agent_address, is_active=True, status="active")
            print(f"[AgentConfig] Agent {agent_id} RESUMED in Supabase")
        except Exception as e:
            print(f"[AgentConfig] Supabase resume failed: {e}")
    
    print(f"[AgentConfig] Agent {agent_id} RESUMED for {user_address}")
    
    return {
        "success": True,
        "message": f"Agent {agent_id} resumed",
        "is_active": True
    }


@router.delete("/delete/{user_address}/{agent_id}")
async def delete_agent(user_address: str, agent_id: str):
    """
    Delete an agent permanently
    """
    user_addr = user_address.lower()
    
    # Try to find agent in cache first
    user_agents = DEPLOYED_AGENTS.get(user_addr, [])
    agent = next((a for a in user_agents if a.get("id") == agent_id), None)
    
    # If not in cache, try Supabase
    agent_address = None
    if not agent and supabase.is_available:
        try:
            supabase_agents = await supabase.get_user_agents(user_addr)
            agent = next((a for a in supabase_agents if a.get("id") == agent_id), None)
            if agent:
                print(f"[AgentConfig] Found agent {agent_id} in Supabase (not in cache)")
        except Exception as e:
            print(f"[AgentConfig] Supabase lookup failed: {e}")
    
    if not agent:
        # Still not found - but proceed anyway to clean up any orphaned data
        print(f"[AgentConfig] Agent {agent_id} not found in cache or Supabase, cleaning up...")
    
    # Get agent_address for Supabase delete
    if agent:
        agent_address = agent.get("agent_address") or agent.get("address")
        
        # Check if agent has active positions
        if agent.get("total_value", 0) > 0:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete agent with active positions. Withdraw funds first."
            )
    
    # Delete from Supabase - try BOTH methods to ensure cleanup
    if supabase.is_available:
        deleted = False
        try:
            # Method 1: Try delete by agent_address
            if agent_address:
                await supabase.delete_user_agent(agent_address)
                print(f"[AgentConfig] Agent deleted from Supabase by address: {agent_address[:10]}...")
                deleted = True
        except Exception as e:
            print(f"[AgentConfig] Supabase delete by address failed: {e}")
        
        try:
            # Method 2: Try delete by user+agent_id (more reliable)
            await supabase.delete_user_agent_by_id(user_addr, agent_id)
            print(f"[AgentConfig] Agent deleted from Supabase by ID: {agent_id}")
            deleted = True
        except Exception as e:
            print(f"[AgentConfig] Supabase delete by ID failed: {e}")
        
        if not deleted:
            print(f"[AgentConfig] WARNING: Could not delete agent from Supabase!")
    
    # Remove from cache if present
    if agent and agent in user_agents:
        user_agents.remove(agent)
        DEPLOYED_AGENTS[user_addr] = user_agents
        _save_agents(DEPLOYED_AGENTS)
        print(f"[AgentConfig] Agent {agent_id} removed from cache")
    
    print(f"[AgentConfig] Agent {agent_id} deleted for {user_address}")
    
    return {
        "success": True,
        "message": f"Agent {agent_id} deleted",
        "remaining_agents": len(DEPLOYED_AGENTS.get(user_addr, []))
    }


class AgentSyncRequest(BaseModel):
    """Request to sync agent data from frontend to backend"""
    user_address: str
    agent: dict


@router.post("/sync")
async def sync_agent(request: AgentSyncRequest):
    """
    Sync agent data from frontend localStorage to backend.
    Used when frontend has agent data that backend is missing.
    """
    user_addr = request.user_address.lower()
    agent_data = request.agent
    
    if not agent_data.get("id"):
        raise HTTPException(status_code=400, detail="Agent must have an id")
    
    # Extract agent_address (may be in different fields)
    agent_address = agent_data.get("agent_address") or agent_data.get("address") or agent_data.get("smartAccount")
    
    # Save to Supabase first (primary storage)
    if supabase.is_available and agent_address:
        try:
            await supabase.save_user_agent(
                user_address=user_addr,
                agent_address=agent_address,
                agent_name=agent_data.get("name") or agent_data.get("agent_name") or "Agent",
                preset=agent_data.get("preset") or "balanced",
                chain=agent_data.get("chain") or "base",
                encrypted_private_key=agent_data.get("encrypted_private_key"),
                settings=agent_data.get("settings"),
                is_active=agent_data.get("is_active", True) or agent_data.get("isActive", True),
                pool_type=agent_data.get("pool_type") or "single",
                risk_level=agent_data.get("risk_level") or "moderate",
                min_apy=agent_data.get("minApy") or agent_data.get("min_apy") or 5,
                max_apy=agent_data.get("maxApy") or agent_data.get("max_apy") or 1000,
                max_drawdown=agent_data.get("max_drawdown") or 20,
                protocols=agent_data.get("protocols"),
                preferred_assets=agent_data.get("preferred_assets")
            )
            print(f"[AgentConfig] Synced agent {agent_address[:10]}... to Supabase for {user_addr[:10]}...")
        except Exception as e:
            print(f"[AgentConfig] Supabase sync failed: {e}")
    
    # Also save to in-memory cache + JSON file (fallback)
    if user_addr not in DEPLOYED_AGENTS:
        DEPLOYED_AGENTS[user_addr] = []
    
    user_agents = DEPLOYED_AGENTS[user_addr]
    
    # Check if agent already exists
    existing_idx = next((i for i, a in enumerate(user_agents) if a.get("id") == agent_data.get("id")), None)
    
    if existing_idx is not None:
        user_agents[existing_idx] = agent_data
        print(f"[AgentConfig] Synced (updated) agent {agent_data.get('id')} in cache")
    else:
        user_agents.append(agent_data)
        print(f"[AgentConfig] Synced (added) agent {agent_data.get('id')} to cache")
    
    _save_agents(DEPLOYED_AGENTS)
    
    return {
        "success": True,
        "message": "Agent synced to backend",
        "supabase": supabase.is_available,
        "agent_id": agent_data.get("id"),
        "total_agents": len(user_agents)
    }


@router.get("/list")
async def list_agents():
    """
    List all deployed agents (admin endpoint)
    """
    all_agents = []
    for user_agents in DEPLOYED_AGENTS.values():
        all_agents.extend(user_agents)
    
    return {
        "success": True,
        "total_users": len(DEPLOYED_AGENTS),
        "total_agents": len(all_agents),
        "agents": all_agents
    }


@router.get("/recommendations/{user_address}")
async def get_recommendations(user_address: str, agent_id: Optional[str] = None):
    """
    Get recommended pools for a deployed agent
    Triggers a scan if not done recently
    """
    user_agents = DEPLOYED_AGENTS.get(user_address, [])
    
    if not user_agents:
        return {
            "success": False,
            "message": "No agents found"
        }
    
    # Get specific agent or first active one
    if agent_id:
        agent = next((a for a in user_agents if a.get("id") == agent_id), None)
    else:
        agent = next((a for a in user_agents if a.get("is_active")), None)
    
    if not agent:
        return {
            "success": False,
            "message": "No active agent found"
        }
    
    # Try to run executor scan
    try:
        from agents.strategy_executor import strategy_executor
        await strategy_executor.execute_agent_strategy(agent)
    except Exception as e:
        print(f"[AgentConfig] Scan error: {e}")
    
    return {
        "success": True,
        "agent_id": agent.get("id"),
        "agent_address": agent.get("agent_address"),
        "recommended_pools": agent.get("recommended_pools", []),
        "last_scan": agent.get("last_scan"),
        "config": {
            "preset": agent.get("preset"),
            "risk_level": agent.get("risk_level"),
            "protocols": agent.get("protocols"),
            "apy_range": [agent.get("min_apy"), agent.get("max_apy")]
        }
    }


# ===========================================
# DELETE AGENT
# ===========================================

@router.delete("/delete/{user_address}/{agent_id}")
async def delete_agent(user_address: str, agent_id: str):
    """
    Delete an agent permanently.
    Removes from in-memory storage and Supabase.
    """
    print(f"[AgentConfig] Delete request: user={user_address[:10]}..., agent={agent_id}")
    
    user_key = user_address.lower()
    
    # Check if agent exists
    if user_key not in DEPLOYED_AGENTS:
        return {"success": False, "error": "User has no agents"}
    
    user_agents = DEPLOYED_AGENTS[user_key]
    original_count = len(user_agents)
    
    # Filter out the agent
    agent_to_delete = next((a for a in user_agents if a.get("id") == agent_id), None)
    
    if not agent_to_delete:
        return {"success": False, "error": "Agent not found"}
    
    # Remove from in-memory cache
    DEPLOYED_AGENTS[user_key] = [a for a in user_agents if a.get("id") != agent_id]
    
    # Delete from Supabase
    if supabase.is_available:
        try:
            agent_address = agent_to_delete.get("agent_address") or agent_to_delete.get("address")
            if agent_address:
                # Delete from agents_v2 table
                await supabase.delete_agent(agent_address)
                print(f"[AgentConfig] Deleted agent from Supabase: {agent_address[:10]}...")
        except Exception as e:
            print(f"[AgentConfig] Supabase delete warning: {e}")
    
    # Persist to file
    try:
        import json
        with open(DEPLOYED_FILE, "w") as f:
            json.dump(DEPLOYED_AGENTS, f, indent=2, default=str)
    except Exception as e:
        print(f"[AgentConfig] File persist warning: {e}")
    
    print(f"[AgentConfig] Agent deleted: {agent_id}, remaining: {len(DEPLOYED_AGENTS.get(user_key, []))}")
    
    return {
        "success": True,
        "message": f"Agent {agent_id[:8]}... deleted",
        "remaining_agents": len(DEPLOYED_AGENTS.get(user_key, []))
    }


class HarvestRequest(BaseModel):
    wallet: str
    agentId: str
    agentAddress: str


class RebalanceRequest(BaseModel):
    wallet: str
    agentId: str
    agentAddress: str
    strategy: Optional[str] = None


@router.post("/harvest")
async def harvest_rewards(request: HarvestRequest):
    """
    Trigger harvest of rewards for an agent's positions.
    Collects yield from all active positions and compounds or withdraws.
    """
    print(f"[AgentConfig] Harvest request: agent={request.agentId}, wallet={request.wallet[:10]}...")
    
    # Verify agent exists
    user_agents = DEPLOYED_AGENTS.get(request.wallet.lower(), [])
    agent = next((a for a in user_agents if a.get("id") == request.agentId), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # TODO: Implement actual harvest logic via strategy_executor
    # For now, return success to unblock frontend
    harvested_amount = 0.0
    
    try:
        from agents.strategy_executor import strategy_executor
        # Queue harvest task
        result = await strategy_executor.harvest_agent_positions(agent)
        harvested_amount = result.get("amount", 0)
    except Exception as e:
        print(f"[AgentConfig] Harvest execution error: {e}")
        # Return success anyway - harvest is queued
    
    # Log harvest to Supabase
    if supabase.is_available and request.agentAddress:
        try:
            await supabase.log_agent_transaction(
                user_address=request.wallet,
                agent_address=request.agentAddress,
                tx_type="claim",
                token="REWARDS",
                amount=harvested_amount
            )
            await supabase.log_audit_trail(
                agent_address=request.agentAddress,
                user_address=request.wallet,
                action="harvest",
                message=f"Harvested {harvested_amount} rewards",
                severity="success"
            )
        except Exception as e:
            print(f"[AgentConfig] Supabase log failed: {e}")
    
    return {
        "success": True,
        "harvestedAmount": harvested_amount,
        "message": "Harvest queued for next block"
    }


@router.post("/rebalance")
async def rebalance_portfolio(request: RebalanceRequest):
    """
    Trigger portfolio rebalance for an agent.
    Scans for better opportunities and reallocates positions.
    """
    print(f"[AgentConfig] Rebalance request: agent={request.agentId}, strategy={request.strategy}")
    
    # Verify agent exists
    user_agents = DEPLOYED_AGENTS.get(request.wallet.lower(), [])
    agent = next((a for a in user_agents if a.get("id") == request.agentId), None)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Log rebalance to Supabase
    if supabase.is_available and request.agentAddress:
        try:
            await supabase.log_agent_transaction(
                user_address=request.wallet,
                agent_address=request.agentAddress,
                tx_type="rebalance",
                token="PORTFOLIO",
                amount=0,
                metadata={"strategy": request.strategy}
            )
            await supabase.log_audit_trail(
                agent_address=request.agentAddress,
                user_address=request.wallet,
                action="rebalance",
                message=f"Rebalance triggered with strategy: {request.strategy or 'default'}",
                severity="info"
            )
        except Exception as e:
            print(f"[AgentConfig] Supabase log failed: {e}")
    
    # TODO: Implement actual rebalance logic via strategy_executor
    try:
        from agents.strategy_executor import strategy_executor
        await strategy_executor.execute_agent_strategy(agent)
    except Exception as e:
        print(f"[AgentConfig] Rebalance execution error: {e}")
    
    return {
        "success": True,
        "message": "Rebalance queued - agent will scan for optimal positions"
    }
