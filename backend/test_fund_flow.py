"""
Test Fund Agent Flow
Tests: USDC → Vault → Subaccount + ETH Gas + Gas Refill
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

async def test_fund_agent_flow():
    print("=" * 60)
    print("🧪 TEST: Fund Agent Flow")
    print("=" * 60)
    
    test_user = "0xa30A689ec0F9D717C5bA1098455B031b868B720f"
    
    # Test 1: Contract monitor exists and can check balance
    print("\n📦 Test 1: Contract Monitor - Check User Balance...")
    try:
        from agents.contract_monitor import contract_monitor
        from web3 import Web3
        
        # Check balance on vault
        w3 = contract_monitor._get_web3()
        balance = contract_monitor.contract.functions.balances(
            Web3.to_checksum_address(test_user)
        ).call()
        
        print(f"   ✅ Vault balance: {balance / 1e6:.2f} USDC")
        
    except Exception as e:
        print(f"   ❌ Contract monitor test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Gas Manager check
    print("\n📦 Test 2: Gas Manager - Check ETH for gas...")
    try:
        from services.gas_manager import get_gas_manager
        
        gas_mgr = get_gas_manager()
        eth_balance = await gas_mgr.get_eth_balance(test_user)
        
        print(f"   ✅ ETH balance: {eth_balance:.6f} ETH")
        
        # Check refill logic
        remaining_tx = gas_mgr.predict_remaining_tx(test_user, eth_balance)
        needs_refill = gas_mgr.should_refill(remaining_tx)
        
        print(f"   ✅ Remaining TX capacity: {remaining_tx}")
        print(f"   ✅ Needs refill: {needs_refill}")
        
    except Exception as e:
        print(f"   ❌ Gas manager test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Full check_and_refill (dry run)
    print("\n📦 Test 3: Gas Manager - Dry Run Refill Check...")
    try:
        result = await gas_mgr.check_and_refill(
            agent_address=test_user,
            eth_price_usd=2900,
            dry_run=True  # Don't actually swap
        )
        
        print(f"   ✅ Check result:")
        print(f"      - Balance: {result.get('current_balance_eth', 0):.6f} ETH")
        print(f"      - Remaining TX: {result.get('remaining_tx', 0)}")
        print(f"      - Needs refill: {result.get('needs_refill', False)}")
        
    except Exception as e:
        print(f"   ❌ Dry run test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Smart Account + Vault integration check
    print("\n📦 Test 4: Smart Account Service...")
    try:
        from services.smart_account_service import get_smart_account_service
        
        svc = get_smart_account_service()
        
        # Get predicted address
        predicted = svc.get_account_address(test_user)
        has_account = svc.has_account(test_user)
        
        print(f"   ✅ Predicted Smart Account: {predicted[:20]}...")
        print(f"   ✅ Has deployed account: {has_account}")
        
    except Exception as e:
        print(f"   ❌ Smart account test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎉 Fund Agent Flow Tests Complete!")
    print("=" * 60)
    print("\n📋 Summary of Fund Flow:")
    print("   1. User deposits USDC to Vault → Deposited event")
    print("   2. ContractMonitor detects event → allocate_funds()")
    print("   3. After allocation → check_and_refill() for ETH gas")
    print("   4. If ETH low → auto swap USDC → ETH via Aerodrome")
    print("   5. Agent executes strategy with adequate gas")


if __name__ == "__main__":
    asyncio.run(test_fund_agent_flow())
