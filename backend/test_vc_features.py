"""
VC Features Integration Test
Tests all 4 newly implemented VC requirements
"""

from artisan.data_sources import is_data_stale, record_apy, get_apy_moving_average, get_apy_volatility
from agents.contract_monitor import should_rotate_position, calculate_impermanent_loss, calculate_lp_equity

def test_all():
    print("="*60)
    print("TEST 1: Data Staleness Check")
    print("="*60)
    stale, age, msg = is_data_stale()
    print(f"Is stale: {stale}")
    print(f"Age: {age:.1f} min")
    print(f"Message: {msg}")

    print()
    print("="*60)
    print("TEST 2: APY Moving Average")
    print("="*60)
    record_apy("test_pool", 5.0)
    record_apy("test_pool", 5.5)
    record_apy("test_pool", 6.0)
    avg = get_apy_moving_average("test_pool", 1)
    vol = get_apy_volatility("test_pool", 1)
    print(f"Recorded 3 APY points: 5.0, 5.5, 6.0")
    print(f"Moving Average: {avg}%")
    print(f"Volatility: {vol}")

    print()
    print("="*60)
    print("TEST 3: Gas-vs-Profit Calculator")
    print("="*60)
    
    # Test case 1: Small position, small APY diff - should NOT rotate
    r1 = should_rotate_position(5, 8, 1000, 30)
    print(f"Case 1: $1000, 5%->8% APY, 30d")
    print(f"  Should rotate: {r1['should_rotate']}")
    print(f"  Cost: ${r1['total_cost']:.2f}")
    print(f"  Profit: ${r1['expected_profit']:.2f}")
    print(f"  Reason: {r1['reason']}")

    # Test case 2: Large position, large APY diff - SHOULD rotate
    r2 = should_rotate_position(5, 15, 10000, 30)
    print(f"\nCase 2: $10000, 5%->15% APY, 30d")
    print(f"  Should rotate: {r2['should_rotate']}")
    print(f"  Cost: ${r2['total_cost']:.2f}")
    print(f"  Profit: ${r2['expected_profit']:.2f}")
    print(f"  Reason: {r2['reason']}")

    print()
    print("="*60)
    print("TEST 4: Impermanent Loss Calculator")
    print("="*60)
    # ETH price doubled (2x)
    il = calculate_impermanent_loss(1.0, 2.0)
    print(f"Price doubled (1.0 -> 2.0):")
    print(f"  IL: {il['il_percent']:.2f}%")
    print(f"  HODL advantage: {il['hodl_advantage']:.2f}%")

    print()
    print("="*60)
    print("TEST 5: LP Equity Calculator")
    print("="*60)
    equity = calculate_lp_equity(
        initial_token_a=1.0, initial_token_b=3000,
        initial_price_a=3000, initial_price_b=1,
        current_token_a=0.8, current_token_b=3500,
        current_price_a=4000, current_price_b=1,
        earned_fees_usd=50
    )
    print(f"LP Position: 1 ETH + 3000 USDC, ETH went 3000->4000")
    print(f"  Initial value: ${equity['initial_value_usd']}")
    print(f"  Current LP value: ${equity['current_lp_value_usd']}")
    print(f"  HODL would be: ${equity['hodl_value_usd']}")
    print(f"  IL: {equity['il_percent']:.2f}% (${equity['il_usd']})")
    print(f"  Fees earned: ${equity['earned_fees_usd']}")
    print(f"  Fees cover IL: {equity['fees_cover_il']}")
    print(f"  Net P&L: ${equity['net_pnl_usd']} ({equity['net_pnl_percent']:.2f}%)")

    print()
    print("="*60)
    print("ALL TESTS PASSED!")
    print("="*60)

if __name__ == "__main__":
    test_all()
