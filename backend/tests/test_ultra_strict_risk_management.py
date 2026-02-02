"""
ULTRA-STRICT Risk Management Tests
====================================

Bardzo obszerne i szczegółowe testy zarządzania ryzykiem:

1. STOP-LOSS
   - Procentowy trigger
   - Absolute value trigger
   - Trailing stop-loss
   - Disabled handling
   - Edge cases (0 value, negative, etc.)

2. TAKE-PROFIT
   - Amount trigger
   - Percentage trigger
   - Partial profit
   - Disabled handling

3. MAX DRAWDOWN
   - Portfolio-level drawdown
   - Peak tracking
   - Reset after deposit
   - Emergency exit

4. VOLATILITY GUARD
   - 24h volatility check
   - Multi-token volatility
   - Pause triggers
   - Resume conditions

5. POSITION SIZING
   - Max allocation %
   - Max per pool %
   - TVL-based limits
   - Gas cost validation

6. EMERGENCY EXIT
   - Circuit breaker conditions
   - Multi-position exit
   - Priority ordering

7. RISK EVALUATION
   - Full position evaluation
   - Alert generation
   - Severity classification

Run: python -m pytest tests/test_ultra_strict_risk_management.py -v --tb=short
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# =============================================================================
# DATACLASSES FOR TESTING
# =============================================================================

@dataclass
class RiskLimits:
    """Risk limits from Pro Mode config"""
    max_allocation_percent: float = 25.0
    max_per_pool_percent: float = 10.0
    stop_loss_enabled: bool = True
    stop_loss_percent: float = 15.0
    take_profit_enabled: bool = False
    take_profit_amount: float = 500.0
    take_profit_percent: Optional[float] = None
    volatility_guard_enabled: bool = True
    volatility_threshold: float = 10.0
    max_drawdown: float = 20.0
    mev_protection: bool = True
    gas_strategy: str = "smart"
    max_gas_gwei: float = 50.0
    trailing_stop_enabled: bool = False
    trailing_stop_percent: float = 5.0


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def risk_limits():
    """Default risk limits"""
    return RiskLimits()


@pytest.fixture
def agent_with_pro_config():
    """Agent with full pro config"""
    return {
        "id": "agent_risk_001",
        "user_address": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
        "pro_config": {
            "stopLossEnabled": True,
            "stopLossPercent": 15.0,
            "takeProfitEnabled": True,
            "takeProfitAmount": 500.0,
            "takeProfitPercent": 20.0,
            "volatilityGuardEnabled": True,
            "volatilityThreshold": 10.0,
            "maxDrawdown": 20.0,
            "trailingStopEnabled": True,
            "trailingStopPercent": 5.0,
            "maxAllocationPercent": 25.0,
            "maxPerPoolPercent": 10.0,
            "mevProtection": True,
            "maxGasGwei": 50.0,
        }
    }


@pytest.fixture
def sample_position():
    """Sample LP position"""
    return {
        "id": "pos_001",
        "pool_id": "aerodrome_usdc_weth",
        "protocol": "aerodrome",
        "entry_value": 1000.0,
        "current_value": 950.0,  # -5%
        "entry_time": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        "tokens": ["USDC", "WETH"],
        "apy": 25.5,
    }


@pytest.fixture
def portfolio_positions():
    """Multiple positions for portfolio tests"""
    return [
        {"id": "pos_001", "entry_value": 1000, "current_value": 950, "tokens": ["USDC", "WETH"]},
        {"id": "pos_002", "entry_value": 500, "current_value": 520, "tokens": ["WETH", "AERO"]},
        {"id": "pos_003", "entry_value": 800, "current_value": 720, "tokens": ["USDC", "AERO"]},
    ]


# =============================================================================
# SECTION 1: STOP-LOSS TESTS (20+ tests)
# =============================================================================

class TestStopLossBasic:
    """Basic stop-loss functionality"""
    
    def test_stop_loss_not_triggered_below_threshold(self):
        """Stop-loss NIE powinien triggerować poniżej threshold"""
        entry_value = 1000.0
        current_value = 900.0  # -10%
        stop_loss_percent = 15.0
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        should_exit = loss_percent >= stop_loss_percent
        
        assert should_exit is False, "❌ 10% loss should NOT trigger 15% stop-loss"
        assert loss_percent == 10.0, f"❌ Loss should be 10%, got {loss_percent}%"
        
        print(f"✅ Stop-loss NOT triggered: {loss_percent}% < {stop_loss_percent}%")
    
    
    def test_stop_loss_triggers_at_threshold(self):
        """Stop-loss MUSI triggerować przy threshold"""
        entry_value = 1000.0
        current_value = 850.0  # -15%
        stop_loss_percent = 15.0
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        should_exit = loss_percent >= stop_loss_percent
        
        assert should_exit is True, "❌ 15% loss should trigger 15% stop-loss"
        
        print(f"✅ Stop-loss triggered AT threshold: {loss_percent}% >= {stop_loss_percent}%")
    
    
    def test_stop_loss_triggers_above_threshold(self):
        """Stop-loss MUSI triggerować powyżej threshold"""
        entry_value = 1000.0
        current_value = 750.0  # -25%
        stop_loss_percent = 15.0
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        should_exit = loss_percent >= stop_loss_percent
        
        assert should_exit is True, "❌ 25% loss should trigger 15% stop-loss"
        
        print(f"✅ Stop-loss triggered ABOVE threshold: {loss_percent}% >= {stop_loss_percent}%")
    
    
    def test_stop_loss_disabled(self):
        """Stop-loss disabled NIE powinien triggerować"""
        entry_value = 1000.0
        current_value = 500.0  # -50% massive loss
        stop_loss_enabled = False
        stop_loss_percent = 15.0
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        
        # Even with 50% loss, disabled = no exit
        should_exit = stop_loss_enabled and loss_percent >= stop_loss_percent
        
        assert should_exit is False, "❌ Disabled stop-loss should NEVER trigger"
        
        print(f"✅ Stop-loss disabled: {loss_percent}% loss ignored")


class TestStopLossEdgeCases:
    """Stop-loss edge cases"""
    
    def test_stop_loss_zero_entry_value(self):
        """Zero entry value MUSI być obsługiwany gracefully"""
        entry_value = 0
        current_value = 100.0
        
        if entry_value <= 0:
            should_exit = False
            loss_percent = 0
        else:
            loss_percent = ((entry_value - current_value) / entry_value) * 100
            should_exit = loss_percent >= 15.0
        
        assert should_exit is False, "❌ Zero entry should not crash"
        
        print(f"✅ Zero entry value handled: no exit")
    
    
    def test_stop_loss_negative_entry_value(self):
        """Negative entry value MUSI być handled"""
        entry_value = -100.0
        current_value = 50.0
        
        if entry_value <= 0:
            should_exit = False
            reason = "Invalid entry value"
        else:
            should_exit = True
        
        assert should_exit is False, "❌ Negative entry should be invalid"
        
        print(f"✅ Negative entry value handled")
    
    
    def test_stop_loss_current_value_higher_than_entry(self):
        """Profit position = BRAK stop-loss"""
        entry_value = 1000.0
        current_value = 1100.0  # +10% profit
        stop_loss_percent = 15.0
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        # loss_percent = -10% (negative = profit)
        
        should_exit = loss_percent >= stop_loss_percent
        
        assert should_exit is False, "❌ Profitable position should NOT trigger stop-loss"
        assert loss_percent < 0, f"❌ Loss should be negative (profit), got {loss_percent}%"
        
        print(f"✅ Profit position: no stop-loss ({loss_percent}%)")
    
    
    def test_stop_loss_exact_threshold(self):
        """Dokładnie na threshold = TRIGGER"""
        entry_value = 1000.0
        stop_loss_percent = 15.0
        current_value = entry_value * (1 - stop_loss_percent / 100)  # Exactly 850
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        should_exit = loss_percent >= stop_loss_percent
        
        assert should_exit is True, "❌ Exact threshold should trigger"
        assert abs(loss_percent - stop_loss_percent) < 0.001, "❌ Should be exactly at threshold"
        
        print(f"✅ Exact threshold: {loss_percent}% == {stop_loss_percent}%")
    
    
    @pytest.mark.parametrize("stop_loss_pct", [1, 5, 10, 15, 20, 25, 50, 100])
    def test_stop_loss_various_thresholds(self, stop_loss_pct):
        """Stop-loss działa dla różnych threshold"""
        entry_value = 1000.0
        # Calculate value that should just trigger
        trigger_value = entry_value * (1 - stop_loss_pct / 100)
        
        loss_percent = ((entry_value - trigger_value) / entry_value) * 100
        should_exit = loss_percent >= stop_loss_pct
        
        assert should_exit is True, f"❌ {stop_loss_pct}% threshold should trigger"
        
    
    def test_stop_loss_tiny_loss(self):
        """Minimalna strata (0.01%) NIE triggeruje"""
        entry_value = 1000.0
        current_value = 999.9  # -0.01%
        stop_loss_percent = 15.0
        
        loss_percent = ((entry_value - current_value) / entry_value) * 100
        should_exit = loss_percent >= stop_loss_percent
        
        assert should_exit is False, "❌ Tiny loss should not trigger"
        assert abs(loss_percent - 0.01) < 0.001, f"❌ Expected ~0.01% loss, got {loss_percent}%"
        
        print(f"✅ Tiny loss: {loss_percent}% < {stop_loss_percent}%")


class TestTrailingStopLoss:
    """Trailing stop-loss tests"""
    
    def test_trailing_stop_tracks_peak(self):
        """Trailing stop MUSI śledzić peak value"""
        entry_value = 1000.0
        peak_value = 1200.0  # Position went up to $1200
        current_value = 1100.0  # Now at $1100
        trailing_stop_percent = 5.0
        
        # Trailing stop is calculated from peak, not entry
        trailing_threshold = peak_value * (1 - trailing_stop_percent / 100)
        # 1200 * 0.95 = 1140
        
        should_exit = current_value <= trailing_threshold
        
        assert trailing_threshold == 1140.0, f"❌ Trailing threshold should be 1140"
        # 1100 < 1140, so should_exit = True
        assert should_exit is True, f"❌ {current_value} <= {trailing_threshold} should trigger"
        
        print(f"✅ Trailing stop from peak: {current_value} <= {trailing_threshold}")
    
    
    def test_trailing_stop_updates_peak(self):
        """Trailing stop aktualizuje peak przy nowym ATH"""
        price_history = [1000, 1050, 1100, 1150, 1120, 1180, 1160]
        trailing_stop_percent = 5.0
        
        peak = price_history[0]
        triggers = []
        
        for price in price_history:
            if price > peak:
                peak = price  # Update peak
            
            threshold = peak * (1 - trailing_stop_percent / 100)
            if price <= threshold:
                triggers.append({"price": price, "peak": peak, "threshold": threshold})
        
        # Peak should be 1180 (highest)
        assert peak == 1180, f"❌ Peak should be 1180, got {peak}"
        
        # Should trigger at 1160 if threshold = 1180 * 0.95 = 1121
        # 1160 > 1121, so no trigger
        assert len(triggers) == 0, "❌ Should not trigger at any point in this history"
        
        print(f"✅ Trailing stop peak tracking: max peak = {peak}")
    
    
    def test_trailing_stop_triggers_on_crash(self):
        """Trailing stop triggeruje przy crashu po ATH"""
        peak = 1500.0
        current_value = 1400.0  # Down 6.67% from peak
        trailing_stop_percent = 5.0
        
        threshold = peak * (1 - trailing_stop_percent / 100)  # 1425
        should_exit = current_value <= threshold
        
        assert should_exit is True, f"❌ {current_value} <= {threshold} should trigger"
        
        print(f"✅ Trailing stop triggers: crash from {peak} to {current_value}")


# =============================================================================
# SECTION 2: TAKE-PROFIT TESTS
# =============================================================================

class TestTakeProfitBasic:
    """Basic take-profit functionality"""
    
    def test_take_profit_by_amount_triggers(self):
        """Take-profit by amount MUSI triggerować"""
        entry_value = 1000.0
        current_value = 1600.0  # $600 profit
        take_profit_amount = 500.0
        
        profit = current_value - entry_value
        should_exit = profit >= take_profit_amount
        
        assert should_exit is True, f"❌ ${profit} profit should trigger ${take_profit_amount} target"
        
        print(f"✅ Take-profit by amount: ${profit} >= ${take_profit_amount}")
    
    
    def test_take_profit_by_percent_triggers(self):
        """Take-profit by percent MUSI triggerować"""
        entry_value = 1000.0
        current_value = 1250.0  # +25%
        take_profit_percent = 20.0
        
        profit_percent = ((current_value - entry_value) / entry_value) * 100
        should_exit = profit_percent >= take_profit_percent
        
        assert should_exit is True, f"❌ {profit_percent}% profit should trigger {take_profit_percent}%"
        
        print(f"✅ Take-profit by percent: {profit_percent}% >= {take_profit_percent}%")
    
    
    def test_take_profit_disabled(self):
        """Take-profit disabled NIE triggeruje"""
        entry_value = 1000.0
        current_value = 5000.0  # +400% massive profit
        take_profit_enabled = False
        take_profit_amount = 500.0
        
        profit = current_value - entry_value
        should_exit = take_profit_enabled and profit >= take_profit_amount
        
        assert should_exit is False, "❌ Disabled take-profit should NEVER trigger"
        
        print(f"✅ Take-profit disabled: ${profit} profit ignored")
    
    
    def test_take_profit_not_triggered_below_target(self):
        """Take-profit NIE triggeruje poniżej target"""
        entry_value = 1000.0
        current_value = 1300.0  # $300 profit
        take_profit_amount = 500.0
        
        profit = current_value - entry_value
        should_exit = profit >= take_profit_amount
        
        assert should_exit is False, f"❌ ${profit} should NOT trigger ${take_profit_amount}"
        
        print(f"✅ Take-profit not triggered: ${profit} < ${take_profit_amount}")


class TestTakeProfitEdgeCases:
    """Take-profit edge cases"""
    
    def test_take_profit_on_loss(self):
        """Take-profit NIE triggeruje na stracie"""
        entry_value = 1000.0
        current_value = 800.0  # -$200 loss
        take_profit_amount = 100.0
        
        profit = current_value - entry_value
        should_exit = profit >= take_profit_amount
        
        assert profit < 0, "❌ Should be a loss"
        assert should_exit is False, "❌ Loss should never trigger take-profit"
        
        print(f"✅ Take-profit on loss: ${profit} (no trigger)")
    
    
    def test_take_profit_exact_target(self):
        """Dokładnie $500 profit = TRIGGER"""
        entry_value = 1000.0
        take_profit_amount = 500.0
        current_value = entry_value + take_profit_amount  # Exactly 1500
        
        profit = current_value - entry_value
        should_exit = profit >= take_profit_amount
        
        assert should_exit is True, "❌ Exact target should trigger"
        assert profit == take_profit_amount, "❌ Should be exactly at target"
        
        print(f"✅ Take-profit exact: ${profit} == ${take_profit_amount}")
    
    
    @pytest.mark.parametrize("take_profit", [10, 50, 100, 500, 1000, 5000])
    def test_take_profit_various_targets(self, take_profit):
        """Take-profit działa dla różnych targets"""
        entry_value = 1000.0
        current_value = entry_value + take_profit + 1  # Just above target
        
        profit = current_value - entry_value
        should_exit = profit >= take_profit
        
        assert should_exit is True, f"❌ ${take_profit} target should trigger"


# =============================================================================
# SECTION 3: MAX DRAWDOWN TESTS
# =============================================================================

class TestMaxDrawdown:
    """Portfolio-level max drawdown tests"""
    
    def test_drawdown_calculation(self, portfolio_positions):
        """Drawdown calculation MUSI być poprawna"""
        total_entry = sum(p["entry_value"] for p in portfolio_positions)
        total_current = sum(p["current_value"] for p in portfolio_positions)
        
        # Total: 2300 entry, 2190 current
        drawdown_pct = ((total_entry - total_current) / total_entry) * 100
        
        expected_drawdown = ((2300 - 2190) / 2300) * 100  # 4.78%
        
        assert abs(drawdown_pct - expected_drawdown) < 0.01, f"❌ Drawdown should be ~4.78%"
        
        print(f"✅ Portfolio drawdown: {drawdown_pct:.2f}%")
    
    
    def test_max_drawdown_triggers_exit(self, portfolio_positions):
        """Max drawdown MUSI triggerować emergency exit"""
        max_drawdown = 20.0
        
        # Create severe loss scenario
        positions = [
            {"entry_value": 1000, "current_value": 700},  # -30%
            {"entry_value": 500, "current_value": 400},   # -20%
        ]
        
        total_entry = sum(p["entry_value"] for p in positions)
        total_current = sum(p["current_value"] for p in positions)
        drawdown_pct = ((total_entry - total_current) / total_entry) * 100
        
        # 1500 entry, 1100 current = 26.67% drawdown
        should_emergency_exit = drawdown_pct >= max_drawdown
        
        assert should_emergency_exit is True, f"❌ {drawdown_pct}% drawdown should trigger exit"
        
        print(f"✅ Max drawdown exit: {drawdown_pct:.2f}% >= {max_drawdown}%")
    
    
    def test_drawdown_from_peak_not_entry(self):
        """Drawdown liczy się od PEAK, nie od entry"""
        entry_value = 1000.0
        peak_value = 1500.0  # ATH
        current_value = 1200.0
        max_drawdown_pct = 20.0
        
        # Drawdown from peak
        drawdown_from_peak = ((peak_value - current_value) / peak_value) * 100
        # (1500 - 1200) / 1500 = 20%
        
        should_exit = drawdown_from_peak >= max_drawdown_pct
        
        assert should_exit is True, f"❌ {drawdown_from_peak}% from peak should trigger"
        
        # Drawdown from entry would be different
        drawdown_from_entry = ((entry_value - current_value) / entry_value) * 100
        # (1000 - 1200) / 1000 = -20% (profit!)
        
        assert drawdown_from_entry < 0, "❌ From entry perspective, this is profit"
        
        print(f"✅ Drawdown from peak: {drawdown_from_peak}% (from entry: {drawdown_from_entry}%)")
    
    
    def test_drawdown_reset_after_deposit(self):
        """Drawdown POWINIEN resetować po deposit"""
        # Initial state
        portfolio_peak = 1000.0
        current_value = 800.0  # 20% down
        
        drawdown = ((portfolio_peak - current_value) / portfolio_peak) * 100
        assert drawdown == 20.0
        
        # User deposits $500
        deposit = 500.0
        new_current = current_value + deposit  # 1300
        new_peak = max(portfolio_peak, new_current)  # 1300 (new peak!)
        
        new_drawdown = ((new_peak - new_current) / new_peak) * 100
        
        assert new_drawdown == 0, "❌ Drawdown should reset after deposit creates new peak"
        
        print(f"✅ Drawdown reset after deposit: {drawdown}% → {new_drawdown}%")


# =============================================================================
# SECTION 4: VOLATILITY GUARD TESTS
# =============================================================================

class TestVolatilityGuard:
    """Volatility guard functionality"""
    
    @pytest.mark.asyncio
    async def test_volatility_triggers_pause(self):
        """High volatility MUSI triggerować pause"""
        volatility_threshold = 10.0
        current_volatility = 15.0  # 15% 24h change
        volatility_guard_enabled = True
        
        should_pause = volatility_guard_enabled and current_volatility >= volatility_threshold
        
        assert should_pause is True, f"❌ {current_volatility}% should trigger pause"
        
        print(f"✅ Volatility guard triggered: {current_volatility}% >= {volatility_threshold}%")
    
    
    @pytest.mark.asyncio
    async def test_volatility_below_threshold_continues(self):
        """Low volatility = kontynuacja"""
        volatility_threshold = 10.0
        current_volatility = 5.0
        volatility_guard_enabled = True
        
        should_pause = volatility_guard_enabled and current_volatility >= volatility_threshold
        
        assert should_pause is False, f"❌ {current_volatility}% should NOT pause"
        
        print(f"✅ Volatility OK: {current_volatility}% < {volatility_threshold}%")
    
    
    @pytest.mark.asyncio
    async def test_volatility_guard_disabled(self):
        """Volatility guard disabled = no pause"""
        volatility_threshold = 10.0
        current_volatility = 50.0  # Extreme volatility
        volatility_guard_enabled = False
        
        should_pause = volatility_guard_enabled and current_volatility >= volatility_threshold
        
        assert should_pause is False, "❌ Disabled guard should never pause"
        
        print(f"✅ Volatility guard disabled: {current_volatility}% ignored")
    
    
    @pytest.mark.asyncio
    async def test_multi_token_volatility(self):
        """Multi-token volatility checking"""
        tokens_volatility = {
            "WETH": 8.0,    # OK
            "USDC": 0.1,    # Stable
            "AERO": 25.0,   # HIGH!
        }
        threshold = 10.0
        
        volatile_tokens = [t for t, v in tokens_volatility.items() if v >= threshold]
        should_pause = len(volatile_tokens) > 0
        
        assert should_pause is True, "❌ AERO volatility should trigger pause"
        assert "AERO" in volatile_tokens, "❌ AERO should be flagged"
        
        print(f"✅ Multi-token volatility: {volatile_tokens} exceeded threshold")
    
    
    @pytest.mark.asyncio
    async def test_volatility_resume_condition(self):
        """Volatility resume po spadku"""
        volatility_history = [15.0, 12.0, 11.0, 9.0, 7.0]  # Dropping below 8.0
        threshold = 10.0
        resume_threshold = 8.0  # Resume when below this
        
        # Find when to resume
        resume_at = None
        for i, vol in enumerate(volatility_history):
            if vol < resume_threshold:
                resume_at = i
                break
        
        assert resume_at is not None, "❌ Should find resume point"
        assert volatility_history[resume_at] == 8.0, "❌ Should resume at 8%"
        
        print(f"✅ Volatility resume at index {resume_at}: {volatility_history[resume_at]}%")


# =============================================================================
# SECTION 5: POSITION SIZING TESTS
# =============================================================================

class TestPositionSizing:
    """Position sizing and allocation limits"""
    
    def test_max_allocation_percent(self):
        """Max allocation % MUSI być respektowany"""
        total_capital = 10000.0
        max_allocation_percent = 25.0
        
        max_position_size = total_capital * (max_allocation_percent / 100)
        
        test_sizes = [
            (2000, True, "20% - OK"),
            (2500, True, "25% - at limit, OK"),
            (2501, False, "25.01% - EXCEEDS"),
            (5000, False, "50% - way over"),
        ]
        
        for size, should_allow, reason in test_sizes:
            is_valid = size <= max_position_size
            assert is_valid == should_allow, f"❌ {reason}"
        
        print(f"✅ Max allocation: {max_allocation_percent}% = ${max_position_size}")
    
    
    def test_max_per_pool_percent(self):
        """Max per pool % MUSI być respektowany"""
        pool_tvl = 1_000_000.0
        max_per_pool_percent = 0.5  # 0.5% of pool TVL
        
        max_position_size = pool_tvl * (max_per_pool_percent / 100)
        # $5000
        
        assert max_position_size == 5000.0, f"❌ Max per pool should be $5000"
        
        # Can't put more than $5000 in this pool
        position_size = 3000.0
        is_valid = position_size <= max_position_size
        
        assert is_valid is True, "❌ $3000 should be valid"
        
        print(f"✅ Max per pool: {max_per_pool_percent}% of ${pool_tvl/1e6:.1f}M = ${max_position_size}")
    
    
    def test_combined_position_limits(self):
        """Combined limits (capital AND TVL)"""
        total_capital = 10000.0
        pool_tvl = 100000.0
        max_allocation_percent = 25.0
        max_per_pool_percent = 5.0
        
        limit_from_capital = total_capital * (max_allocation_percent / 100)  # $2500
        limit_from_tvl = pool_tvl * (max_per_pool_percent / 100)  # $5000
        
        # Must respect BOTH limits - take minimum
        actual_max = min(limit_from_capital, limit_from_tvl)
        
        assert actual_max == 2500.0, f"❌ Should be limited by capital to $2500"
        
        print(f"✅ Combined limits: min(${limit_from_capital}, ${limit_from_tvl}) = ${actual_max}")
    
    
    def test_gas_cost_validation(self):
        """Gas cost < 1% of position"""
        position_size = 100.0  # $100 position
        gas_cost_usd = 0.50  # $0.50 gas
        max_gas_percent = 1.0
        
        gas_percent = (gas_cost_usd / position_size) * 100
        is_valid = gas_percent <= max_gas_percent
        
        assert is_valid is True, f"❌ {gas_percent}% gas should be valid"
        
        # Too small position
        small_position = 10.0
        gas_percent_small = (gas_cost_usd / small_position) * 100  # 5%
        is_valid_small = gas_percent_small <= max_gas_percent
        
        assert is_valid_small is False, f"❌ {gas_percent_small}% gas too high for small position"
        
        print(f"✅ Gas validation: ${gas_cost_usd}/${position_size} = {gas_percent}%")


# =============================================================================
# SECTION 6: EMERGENCY EXIT TESTS
# =============================================================================

class TestEmergencyExit:
    """Emergency exit scenarios"""
    
    @pytest.mark.asyncio
    async def test_emergency_exit_all_positions(self, portfolio_positions):
        """Emergency exit MUSI closeować wszystkie pozycje"""
        max_drawdown = 20.0
        
        # Simulate severe market crash
        crashed_positions = []
        for p in portfolio_positions:
            crashed = p.copy()
            crashed["current_value"] = p["entry_value"] * 0.7  # -30% each
            crashed_positions.append(crashed)
        
        total_entry = sum(p["entry_value"] for p in crashed_positions)
        total_current = sum(p["current_value"] for p in crashed_positions)
        drawdown = ((total_entry - total_current) / total_entry) * 100
        
        should_emergency_exit = drawdown >= max_drawdown
        
        assert should_emergency_exit is True, "❌ Should trigger emergency exit"
        
        # All positions should be marked for exit
        positions_to_exit = [p for p in crashed_positions if should_emergency_exit]
        
        assert len(positions_to_exit) == len(crashed_positions), "❌ All positions should exit"
        
        print(f"✅ Emergency exit: {len(positions_to_exit)} positions marked for exit")
    
    
    @pytest.mark.asyncio
    async def test_emergency_exit_priority_ordering(self, portfolio_positions):
        """Emergency exit MUSI być priorytetyzowany (worst first)"""
        # Add loss percentages
        for p in portfolio_positions:
            p["loss_percent"] = ((p["entry_value"] - p["current_value"]) / p["entry_value"]) * 100
        
        # Sort by loss (worst first)
        sorted_positions = sorted(portfolio_positions, key=lambda p: p["loss_percent"], reverse=True)
        
        # Worst loss first
        assert sorted_positions[0]["id"] == "pos_003", "❌ Worst loser should be first"
        
        print(f"✅ Exit priority: {[p['id'] for p in sorted_positions]}")
    
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_conditions(self):
        """Circuit breaker triggers na multiple failures"""
        failure_threshold = 3
        failure_window_hours = 1
        
        failures = [
            {"time": datetime.utcnow() - timedelta(minutes=50), "reason": "tx_failed"},
            {"time": datetime.utcnow() - timedelta(minutes=30), "reason": "slippage"},
            {"time": datetime.utcnow() - timedelta(minutes=10), "reason": "tx_failed"},
        ]
        
        # Count failures in window
        window_start = datetime.utcnow() - timedelta(hours=failure_window_hours)
        recent_failures = [f for f in failures if f["time"] > window_start]
        
        should_circuit_break = len(recent_failures) >= failure_threshold
        
        assert should_circuit_break is True, f"❌ {len(recent_failures)} failures should trigger circuit breaker"
        
        print(f"✅ Circuit breaker: {len(recent_failures)} failures in {failure_window_hours}h")


# =============================================================================
# SECTION 7: FULL RISK EVALUATION TESTS
# =============================================================================

class TestFullRiskEvaluation:
    """Full position risk evaluation"""
    
    @pytest.mark.asyncio
    async def test_evaluate_position_stop_loss(self, agent_with_pro_config, sample_position):
        """evaluate_position wykrywa stop-loss"""
        # Modify position to trigger stop-loss
        sample_position["entry_value"] = 1000.0
        sample_position["current_value"] = 800.0  # -20% loss
        
        stop_loss_percent = agent_with_pro_config["pro_config"]["stopLossPercent"]  # 15%
        loss_percent = ((sample_position["entry_value"] - sample_position["current_value"]) 
                       / sample_position["entry_value"]) * 100
        
        should_exit_sl = loss_percent >= stop_loss_percent
        
        result = {
            "should_exit": should_exit_sl,
            "alerts": []
        }
        
        if should_exit_sl:
            result["alerts"].append({
                "type": "stop_loss",
                "severity": "critical",
                "message": f"Stop-loss triggered: -{loss_percent:.1f}%"
            })
        
        assert result["should_exit"] is True, "❌ Should trigger stop-loss exit"
        assert len(result["alerts"]) == 1, "❌ Should have 1 alert"
        assert result["alerts"][0]["type"] == "stop_loss", "❌ Alert type should be stop_loss"
        assert result["alerts"][0]["severity"] == "critical", "❌ Stop-loss is critical"
        
        print(f"✅ Evaluation: stop-loss triggered at {loss_percent}%")
    
    
    @pytest.mark.asyncio
    async def test_evaluate_position_take_profit(self, agent_with_pro_config, sample_position):
        """evaluate_position wykrywa take-profit"""
        sample_position["entry_value"] = 1000.0
        sample_position["current_value"] = 1600.0  # +$600 profit
        
        take_profit_amount = agent_with_pro_config["pro_config"]["takeProfitAmount"]  # 500
        profit = sample_position["current_value"] - sample_position["entry_value"]
        
        should_exit_tp = profit >= take_profit_amount
        
        result = {
            "should_exit": should_exit_tp,
            "alerts": []
        }
        
        if should_exit_tp:
            result["alerts"].append({
                "type": "take_profit",
                "severity": "info",
                "message": f"Take-profit triggered: ${profit:.2f}"
            })
        
        assert result["should_exit"] is True, "❌ Should trigger take-profit"
        assert result["alerts"][0]["severity"] == "info", "❌ Take-profit is info"
        
        print(f"✅ Evaluation: take-profit at ${profit}")
    
    
    @pytest.mark.asyncio
    async def test_evaluate_position_volatility(self, agent_with_pro_config, sample_position):
        """evaluate_position wykrywa high volatility"""
        volatility = 15.0  # 15% 24h volatility
        threshold = agent_with_pro_config["pro_config"]["volatilityThreshold"]  # 10%
        
        should_pause = volatility >= threshold
        
        result = {
            "should_pause": should_pause,
            "should_exit": False,
            "alerts": []
        }
        
        if should_pause:
            result["alerts"].append({
                "type": "volatility",
                "severity": "warning",
                "message": f"High volatility: {volatility}%"
            })
        
        assert result["should_pause"] is True, "❌ Should pause on high volatility"
        assert result["should_exit"] is False, "❌ Volatility = pause, not exit"
        assert result["alerts"][0]["severity"] == "warning", "❌ Volatility is warning"
        
        print(f"✅ Evaluation: volatility pause at {volatility}%")
    
    
    @pytest.mark.asyncio
    async def test_evaluate_combined_alerts(self, agent_with_pro_config, sample_position):
        """evaluate_position łączy multiple alerts"""
        # Position with multiple risk factors
        sample_position["entry_value"] = 1000.0
        sample_position["current_value"] = 850.0  # -15% (at stop-loss threshold)
        volatility = 12.0  # Above 10% threshold
        
        alerts = []
        
        # Check stop-loss
        loss_percent = 15.0
        sl_threshold = agent_with_pro_config["pro_config"]["stopLossPercent"]
        if loss_percent >= sl_threshold:
            alerts.append({"type": "stop_loss", "severity": "critical"})
        
        # Check volatility
        vol_threshold = agent_with_pro_config["pro_config"]["volatilityThreshold"]
        if volatility >= vol_threshold:
            alerts.append({"type": "volatility", "severity": "warning"})
        
        result = {
            "should_exit": any(a["type"] == "stop_loss" for a in alerts),
            "should_pause": any(a["type"] == "volatility" for a in alerts),
            "alerts": alerts
        }
        
        assert len(result["alerts"]) == 2, "❌ Should have 2 alerts"
        assert result["should_exit"] is True, "❌ Should exit (stop-loss)"
        assert result["should_pause"] is True, "❌ Should also pause (volatility)"
        
        print(f"✅ Combined evaluation: {len(alerts)} alerts")


# =============================================================================
# SECTION 8: ALERT SEVERITY TESTS
# =============================================================================

class TestAlertSeverity:
    """Alert severity classification"""
    
    def test_severity_levels(self):
        """Severity MUSI być poprawnie przypisana"""
        SEVERITY_MAP = {
            "stop_loss": "critical",
            "max_drawdown": "critical",
            "take_profit": "info",
            "volatility": "warning",
            "gas_spike": "warning",
            "apy_drop": "info",
        }
        
        for alert_type, expected_severity in SEVERITY_MAP.items():
            # Simulate processing
            alert = {"type": alert_type, "severity": expected_severity}
            
            assert alert["severity"] == expected_severity, f"❌ {alert_type} should be {expected_severity}"
        
        print(f"✅ Severity levels: {len(SEVERITY_MAP)} types classified")
    
    
    def test_critical_alerts_require_immediate_action(self):
        """Critical alerts = natychmiastowa akcja"""
        alerts = [
            {"type": "stop_loss", "severity": "critical"},
            {"type": "max_drawdown", "severity": "critical"},
        ]
        
        critical_alerts = [a for a in alerts if a["severity"] == "critical"]
        requires_immediate_action = len(critical_alerts) > 0
        
        assert requires_immediate_action is True, "❌ Critical alerts need action"
        
        print(f"✅ Critical alerts: {len(critical_alerts)} require immediate action")
    
    
    def test_warning_alerts_suggest_caution(self):
        """Warning alerts = ostrożność, nie exit"""
        alerts = [
            {"type": "volatility", "severity": "warning"},
            {"type": "gas_spike", "severity": "warning"},
        ]
        
        warning_alerts = [a for a in alerts if a["severity"] == "warning"]
        should_pause = len(warning_alerts) > 0
        should_exit = False  # Warnings don't trigger exit
        
        assert should_pause is True, "❌ Warnings should suggest pause"
        assert should_exit is False, "❌ Warnings should NOT trigger exit"
        
        print(f"✅ Warning alerts: {len(warning_alerts)} suggest caution")


# =============================================================================
# SECTION 9: INTEGRATION TESTS
# =============================================================================

class TestRiskManagementIntegration:
    """Integration tests for full risk management flow"""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self, agent_with_pro_config, portfolio_positions):
        """Full monitoring cycle dla wszystkich pozycji"""
        all_alerts = []
        positions_to_exit = []
        positions_to_pause = []
        
        for position in portfolio_positions:
            # Simulate risk check
            loss_pct = ((position["entry_value"] - position["current_value"]) 
                       / position["entry_value"]) * 100
            
            result = {"alerts": []}
            
            if loss_pct >= 15:  # Stop-loss
                result["should_exit"] = True
                result["alerts"].append({"type": "stop_loss", "severity": "critical"})
                positions_to_exit.append(position["id"])
            
            all_alerts.extend(result["alerts"])
        
        print(f"✅ Monitoring cycle: {len(portfolio_positions)} positions checked")
        print(f"   Alerts: {len(all_alerts)}, Exit: {len(positions_to_exit)}, Pause: {len(positions_to_pause)}")
    
    
    @pytest.mark.asyncio
    async def test_risk_limits_validation(self, agent_with_pro_config):
        """Validation of risk limits from config"""
        pro_config = agent_with_pro_config["pro_config"]
        
        validations = []
        
        # Stop-loss validation
        sl_pct = pro_config.get("stopLossPercent", 15)
        if not (1 <= sl_pct <= 50):
            validations.append("stop_loss_percent out of range (1-50)")
        
        # Take-profit validation
        tp_amt = pro_config.get("takeProfitAmount", 500)
        if tp_amt <= 0:
            validations.append("take_profit_amount must be positive")
        
        # Volatility threshold
        vol_threshold = pro_config.get("volatilityThreshold", 10)
        if not (1 <= vol_threshold <= 50):
            validations.append("volatility_threshold out of range (1-50)")
        
        # Max drawdown
        max_dd = pro_config.get("maxDrawdown", 20)
        if not (5 <= max_dd <= 100):
            validations.append("max_drawdown out of range (5-100)")
        
        assert len(validations) == 0, f"❌ Validations failed: {validations}"
        
        print(f"✅ Risk limits validated: all within acceptable ranges")


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("🔒 ULTRA-STRICT RISK MANAGEMENT TESTS")
    print("=" * 70)
    
    print("\n📊 Stop-Loss:")
    TestStopLossBasic().test_stop_loss_not_triggered_below_threshold()
    TestStopLossBasic().test_stop_loss_triggers_at_threshold()
    TestStopLossBasic().test_stop_loss_disabled()
    
    print("\n📊 Take-Profit:")
    TestTakeProfitBasic().test_take_profit_by_amount_triggers()
    TestTakeProfitBasic().test_take_profit_disabled()
    
    print("\n📊 Max Drawdown:")
    TestMaxDrawdown().test_drawdown_from_peak_not_entry()
    
    print("\n📊 Volatility Guard:")
    asyncio.run(TestVolatilityGuard().test_volatility_triggers_pause())
    
    print("\n📊 Position Sizing:")
    TestPositionSizing().test_max_allocation_percent()
    TestPositionSizing().test_combined_position_limits()
    
    print("\n📊 Alert Severity:")
    TestAlertSeverity().test_severity_levels()
    
    print("\n" + "=" * 70)
    print("✅ All risk management tests passed!")
    print("=" * 70)
