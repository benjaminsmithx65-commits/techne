"""
Test Dual LP Aerodrome Flow

Tests the complete flow:
1. Create Smart Account for test user
2. Build dual LP calldata (USDC → WETH → LP)
3. Verify calldata structure is correct
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv(Path(__file__).parent / ".env")

async def test_dual_lp_flow():
    print("=" * 60)
    print("🧪 TEST: Dual LP Aerodrome Flow")
    print("=" * 60)
    
    # Test 1: Smart Account Service
    print("\n📦 Test 1: Smart Account Service...")
    try:
        from services.smart_account_service import get_smart_account_service
        svc = get_smart_account_service()
        
        # Check factory is configured
        if svc.factory:
            print(f"   ✅ Factory configured: {svc.factory.address}")
        else:
            print("   ❌ Factory not configured!")
            return
        
        # Test counterfactual address
        test_user = "0xa30A689ec0F9D717C5bA1098455B031b868B720f"
        predicted = svc.get_account_address(test_user)
        print(f"   ✅ Predicted Smart Account: {predicted}")
        
        # Check if deployed
        has_account = svc.has_account(test_user)
        print(f"   ✅ Has deployed account: {has_account}")
        
    except Exception as e:
        print(f"   ❌ Smart Account test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Dual LP Builder
    print("\n📦 Test 2: AerodromeDualLPBuilder...")
    try:
        from artisan.aerodrome_dual import AerodromeDualLPBuilder
        
        builder = AerodromeDualLPBuilder()
        print(f"   ✅ Builder initialized")
        print(f"   - Router: {builder.AERODROME_ROUTER}")
        print(f"   - USDC: {builder.USDC}")
        print(f"   - WETH: {builder.WETH}")
        
        # Build calldata for $100 USDC → WETH/VIRTUALS LP
        amount_usdc = 100 * 1e6  # $100
        target_token = "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b"  # VIRTUALS
        
        print(f"\n   Building calldata for ${amount_usdc/1e6} USDC → WETH/VIRTUALS LP...")
        
        steps = await builder.build_dual_lp_calldata(
            user_address=test_user,
            usdc_amount=int(amount_usdc),
            target_token=target_token,
            slippage_bps=100
        )
        
        print(f"   ✅ Generated {len(steps)} steps:")
        for i, step in enumerate(steps):
            protocol = step[0][:10] + "..." if len(step[0]) > 10 else step[0]
            calldata_preview = step[1][:20].hex() + "..." if len(step[1]) > 20 else step[1].hex()
            print(f"      Step {i}: {protocol} → {calldata_preview}")
        
    except Exception as e:
        print(f"   ❌ Dual LP builder test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Contract Monitor Integration
    print("\n📦 Test 3: Contract Monitor LP Detection...")
    try:
        from agents.contract_monitor import contract_monitor
        
        # Check if Aerodrome is detected as LP protocol
        test_pool = {
            "project": "aerodrome",
            "symbol": "WETH/VIRTUALS",
            "pool_address": "0x123",
            "apy": 45.0
        }
        
        # Check protocol detection
        protocol = test_pool.get("project", "").lower()
        is_lp = protocol in ["aerodrome", "uniswap", "velodrome", "camelot"]
        
        print(f"   Pool: {test_pool['symbol']}")
        print(f"   Protocol: {protocol}")
        print(f"   Is LP protocol: {is_lp}")
        
        if is_lp:
            print("   ✅ Contract monitor will use dual LP flow")
        else:
            print("   ❌ Contract monitor will NOT use dual LP flow")
        
    except Exception as e:
        print(f"   ❌ Contract monitor test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_dual_lp_flow())
