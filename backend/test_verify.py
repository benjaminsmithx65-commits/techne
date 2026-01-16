"""Backend Quick Verification"""
print("=== BACKEND VERIFICATION ===\n")

# Test 1: Scout Agent
print("1. Scout Agent:")
import asyncio
from artisan.scout_agent import get_scout_pools
result = asyncio.run(get_scout_pools(chain="Base"))
pools = result.get("pools", [])
print(f"   Found {len(pools)} pools")
if pools:
    print(f"   Sample: {pools[0]['symbol']}")
    print(f"   IL Risk: {pools[0].get('il_risk', 'N/A')}")
print("   OK\n")

# Test 2: Risk Manager  
print("2. Risk Manager:")
from agents.risk_manager import risk_manager
limits = risk_manager.parse_pro_config({"stopLossPercent": 20, "volatilityGuard": True})
print(f"   Stop-Loss: {limits.stop_loss_percent}%")
print(f"   Volatility Guard: {limits.volatility_guard_enabled}")
print("   OK\n")

# Test 3: Strategy Executor
print("3. Strategy Executor:")
from agents.strategy_executor import strategy_executor
print("   Loaded successfully")
print("   OK\n")

# Test 4: On-chain Executor
print("4. On-chain Executor:")
from integrations.onchain_executor import TOKENS
print(f"   USDC: {TOKENS['USDC']}")
print(f"   WETH: {TOKENS['WETH']}")
print("   OK\n")

print("=== ALL BACKEND TESTS PASSED ===")
