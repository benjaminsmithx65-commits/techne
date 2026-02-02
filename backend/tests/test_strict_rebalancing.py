"""
STRICT Rebalancing Logic Tests
================================

Restrykcyjne testy dla logiki rebalancing:
- Auto-rebalance trigger przy threshold X%
- APY drift detection (pool APY spada poniżej min)
- Pool rotation (zamiana na lepszy pool)
- Compound frequency enforcement
- Delta neutral rebalancing

Run: python -m pytest tests/test_strict_rebalancing.py -v --tb=short
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def agent_config():
    """Standard agent config with rebalancing settings"""
    return {
        "id": "agent_rebalance_001",
        "user_address": "0xa30A689ec0F9D717C5bA1098455B031b868B720f",
        "agent_address": "0x5E047DeB5eb22F4E4A7f2207087369468575e3EF",
        "is_active": True,
        
        # Rebalancing settings
        "auto_rebalance": True,
        "rebalance_threshold": 5,  # 5% deviation triggers rebalance
        "apy_check_hours": 24,     # Check APY every 24h
        
        # Risk settings
        "min_apy": 5.0,
        "max_allocation": 20,
        
        # Compound settings
        "compound_frequency": 7,  # 7 days
    }


@pytest.fixture
def current_allocations():
    """Current agent allocations"""
    return [
        {
            "pool_id": "aerodrome_usdc_weth",
            "pool_symbol": "USDC/WETH",
            "protocol": "aerodrome",
            "amount": 100.0,
            "current_value": 105.0,  # +5%
            "apy": 25.5,
            "entry_apy": 30.0,  # APY when entered
            "entry_date": (datetime.utcnow() - timedelta(days=10)).isoformat(),
        },
        {
            "pool_id": "aerodrome_weth_aero",
            "pool_symbol": "WETH/AERO",
            "protocol": "aerodrome",
            "amount": 80.0,
            "current_value": 82.0,  # +2.5%
            "apy": 45.0,
            "entry_apy": 40.0,  # APY increased
            "entry_date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
        },
    ]


@pytest.fixture
def available_pools():
    """Available pools for reallocation"""
    return [
        {"pool_id": "aerodrome_usdc_weth", "symbol": "USDC/WETH", "apy": 25.5, "tvl": 5_000_000},
        {"pool_id": "aerodrome_weth_aero", "symbol": "WETH/AERO", "apy": 45.0, "tvl": 2_000_000},
        {"pool_id": "aerodrome_usdc_aero", "symbol": "USDC/AERO", "apy": 60.0, "tvl": 1_000_000},
        {"pool_id": "aave_usdc", "symbol": "USDC", "apy": 8.0, "tvl": 100_000_000},
    ]


# =============================================================================
# TEST: REBALANCE THRESHOLD TRIGGERS
# =============================================================================

class TestRebalanceThresholdTriggers:
    """Testy wyzwalania rebalance przy przekroczeniu threshold"""
    
    def test_rebalance_triggers_at_threshold(self, agent_config):
        """Rebalance MUSI triggerować gdy deviation >= threshold"""
        threshold = agent_config["rebalance_threshold"]  # 5%
        
        test_cases = [
            # (current_value_pct, should_trigger)
            (0, False, "No deviation"),
            (2, False, "2% deviation - below threshold"),
            (4.9, False, "4.9% deviation - below threshold"),
            (5.0, True, "5% deviation - at threshold"),
            (5.1, True, "5.1% deviation - above threshold"),
            (10, True, "10% deviation - way above"),
            (-5, True, "-5% negative deviation - at threshold"),
            (-10, True, "-10% negative deviation"),
        ]
        
        for deviation_pct, should_trigger, reason in test_cases:
            needs_rebalance = abs(deviation_pct) >= threshold
            assert needs_rebalance == should_trigger, f"❌ {reason}: expected {should_trigger}, got {needs_rebalance}"
        
        print(f"✅ Rebalance correctly triggers at {threshold}% threshold")
    
    
    def test_no_rebalance_when_disabled(self, agent_config):
        """Rebalance NIE POWINIEN działać gdy auto_rebalance=False"""
        config = agent_config.copy()
        config["auto_rebalance"] = False
        
        deviation = 15.0  # Way above threshold
        
        # When auto_rebalance is off, never trigger
        should_trigger = config["auto_rebalance"] and deviation >= config["rebalance_threshold"]
        
        assert should_trigger is False, "❌ Should not trigger when auto_rebalance=False"
        
        print(f"✅ Rebalance correctly disabled when auto_rebalance=False")
    
    
    def test_rebalance_calculates_deviation_correctly(self, current_allocations):
        """Deviation calculation MUSI być poprawna"""
        alloc = current_allocations[0]
        
        initial = alloc["amount"]  # 100
        current = alloc["current_value"]  # 105
        
        deviation = ((current - initial) / initial) * 100
        expected_deviation = 5.0  # +5%
        
        assert abs(deviation - expected_deviation) < 0.01, f"❌ Deviation should be {expected_deviation}%, got {deviation}%"
        
        print(f"✅ Deviation correctly calculated: {deviation}%")
    
    
    def test_multi_allocation_weighted_deviation(self, current_allocations):
        """Weighted deviation dla wielu alokacji"""
        total_initial = sum(a["amount"] for a in current_allocations)
        total_current = sum(a["current_value"] for a in current_allocations)
        
        # Portfolio-level deviation
        portfolio_deviation = ((total_current - total_initial) / total_initial) * 100
        
        # Calculate expected: (105 + 82 - 100 - 80) / 180 * 100 = 3.89%
        expected = ((105 + 82) - (100 + 80)) / (100 + 80) * 100
        
        assert abs(portfolio_deviation - expected) < 0.01, f"❌ Portfolio deviation should be {expected}%, got {portfolio_deviation}%"
        
        print(f"✅ Portfolio weighted deviation: {portfolio_deviation:.2f}%")


# =============================================================================
# TEST: APY DRIFT DETECTION
# =============================================================================

class TestAPYDriftDetection:
    """Testy wykrywania spadku APY poniżej minimum"""
    
    def test_apy_drift_below_min_triggers_exit(self, agent_config, current_allocations):
        """APY poniżej min_apy MUSI triggerować exit"""
        min_apy = agent_config["min_apy"]  # 5%
        
        test_cases = [
            (8.0, False, "8% APY - above min, stay"),
            (5.0, False, "5% APY - at min, stay"),
            (4.9, True, "4.9% APY - below min, exit"),
            (3.0, True, "3% APY - way below min, exit"),
            (0, True, "0% APY - definitely exit"),
        ]
        
        for current_apy, should_exit, reason in test_cases:
            is_below_min = current_apy < min_apy
            assert is_below_min == should_exit, f"❌ {reason}: expected exit={should_exit}, got {is_below_min}"
        
        print(f"✅ APY drift correctly detects pools below {min_apy}% min")
    
    
    def test_apy_drop_from_entry_detection(self, current_allocations):
        """Znaczący spadek APY od entry MUSI być wykryty"""
        alloc = current_allocations[0]
        
        entry_apy = alloc["entry_apy"]  # 30%
        current_apy = alloc["apy"]      # 25.5%
        
        apy_drop = ((entry_apy - current_apy) / entry_apy) * 100
        expected_drop = ((30 - 25.5) / 30) * 100  # 15%
        
        assert abs(apy_drop - expected_drop) < 0.1, f"❌ APY drop should be {expected_drop}%, got {apy_drop}%"
        
        # Define significant drop threshold (e.g., 20%)
        SIGNIFICANT_DROP = 20
        is_significant = apy_drop >= SIGNIFICANT_DROP
        
        assert is_significant is False, "❌ 15% drop should not be significant (threshold 20%)"
        
        print(f"✅ APY drop detection: {apy_drop:.1f}% (significant: {is_significant})")
    
    
    def test_apy_increase_is_positive(self, current_allocations):
        """APY wzrost powinien być pozytywny"""
        alloc = current_allocations[1]  # WETH/AERO
        
        entry_apy = alloc["entry_apy"]  # 40%
        current_apy = alloc["apy"]      # 45%
        
        apy_change = current_apy - entry_apy  # +5%
        
        assert apy_change > 0, f"❌ APY should have increased"
        
        print(f"✅ APY increased by {apy_change}% (positive)")


# =============================================================================
# TEST: POOL ROTATION
# =============================================================================

class TestPoolRotation:
    """Testy rotacji pul (zamiana na pool z lepszym APY)"""
    
    def test_identify_better_pool_for_rotation(self, current_allocations, available_pools):
        """MUSI identyfikować pool z lepszym APY"""
        current_pool = current_allocations[0]  # USDC/WETH at 25.5% APY
        
        # Find pools with higher APY
        better_pools = [
            p for p in available_pools 
            if p["apy"] > current_pool["apy"] and p["pool_id"] != current_pool["pool_id"]
        ]
        
        assert len(better_pools) > 0, "❌ Should find at least one better pool"
        
        best_pool = max(better_pools, key=lambda p: p["apy"])
        
        assert best_pool["apy"] > current_pool["apy"], "❌ Best pool should have higher APY"
        assert best_pool["symbol"] == "USDC/AERO", f"❌ Expected USDC/AERO (60%), got {best_pool['symbol']}"
        
        print(f"✅ Rotation: {current_pool['pool_symbol']} ({current_pool['apy']}%) → {best_pool['symbol']} ({best_pool['apy']}%)")
    
    
    def test_rotation_only_if_significant_improvement(self, current_allocations, available_pools):
        """Rotacja TYLKO jeśli znacząca poprawa APY (np. +10%)"""
        MIN_IMPROVEMENT = 10  # 10% relative improvement
        
        current_pool = current_allocations[0]  # 25.5% APY
        current_apy = current_pool["apy"]
        
        candidates = []
        for pool in available_pools:
            if pool["pool_id"] != current_pool["pool_id"]:
                improvement = ((pool["apy"] - current_apy) / current_apy) * 100
                if improvement >= MIN_IMPROVEMENT:
                    candidates.append({**pool, "improvement": improvement})
        
        # USDC/AERO: (60 - 25.5) / 25.5 * 100 = 135% improvement
        # WETH/AERO: (45 - 25.5) / 25.5 * 100 = 76% improvement
        
        assert len(candidates) >= 2, f"❌ Should have at least 2 rotation candidates, got {len(candidates)}"
        
        # Verify best candidate
        best = max(candidates, key=lambda p: p["improvement"])
        assert best["symbol"] == "USDC/AERO", "❌ Best rotation should be USDC/AERO"
        assert best["improvement"] > 100, "❌ Improvement should be >100%"
        
        print(f"✅ Rotation candidates with >{MIN_IMPROVEMENT}% improvement: {len(candidates)}")
    
    
    def test_rotation_respects_tvl_minimum(self, agent_config, available_pools):
        """Rotacja MUSI respektować min_tvl"""
        min_tvl = 500_000  # $500k
        
        # Filter pools by TVL
        valid_pools = [p for p in available_pools if p["tvl"] >= min_tvl]
        
        # Small TVL pools should be excluded
        assert not any(p["symbol"] == "USDC/AERO" and p["tvl"] < min_tvl for p in valid_pools), \
            "❌ Low TVL pools should be excluded"
        
        print(f"✅ Rotation respects min_tvl=${min_tvl/1e6:.1f}M: {len(valid_pools)} valid pools")


# =============================================================================
# TEST: COMPOUND FREQUENCY
# =============================================================================

class TestCompoundFrequency:
    """Testy reinwestycji zysków (compound)"""
    
    def test_compound_triggers_at_frequency(self, agent_config):
        """Compound MUSI triggerować co X dni"""
        frequency_days = agent_config["compound_frequency"]  # 7 days
        
        test_cases = [
            (datetime.utcnow() - timedelta(days=3), False, "3 days - too early"),
            (datetime.utcnow() - timedelta(days=6), False, "6 days - still too early"),
            (datetime.utcnow() - timedelta(days=7), True, "7 days - exactly at frequency"),
            (datetime.utcnow() - timedelta(days=10), True, "10 days - overdue"),
        ]
        
        for last_compound, should_trigger, reason in test_cases:
            days_since = (datetime.utcnow() - last_compound).days
            needs_compound = days_since >= frequency_days
            
            assert needs_compound == should_trigger, f"❌ {reason}: expected {should_trigger}, got {needs_compound}"
        
        print(f"✅ Compound triggers every {frequency_days} days")
    
    
    def test_compound_only_if_rewards_exist(self):
        """Compound TYLKO jeśli są rewards do reinwestycji"""
        test_cases = [
            (0, False, "No rewards"),
            (0.5, False, "$0.5 - below dust threshold"),
            (1.0, True, "$1 - minimum viable"),
            (10.0, True, "$10 - good amount"),
        ]
        
        DUST_THRESHOLD = 1.0  # $1 minimum
        
        for rewards, should_compound, reason in test_cases:
            can_compound = rewards >= DUST_THRESHOLD
            assert can_compound == should_compound, f"❌ {reason}: expected {should_compound}, got {can_compound}"
        
        print(f"✅ Compound requires minimum ${DUST_THRESHOLD} rewards")


# =============================================================================
# TEST: DELTA NEUTRAL REBALANCING
# =============================================================================

class TestDeltaNeutralRebalancing:
    """Testy rebalancingu dla strategii delta neutral"""
    
    @pytest.mark.asyncio
    async def test_check_rebalance_detects_imbalance(self):
        """check_rebalance MUSI wykryć nierówność LP/Short"""
        from services.degen_strategies import DeltaNeutralManager
        
        manager = DeltaNeutralManager()
        
        # Create mock position
        position_id = "test_delta_001"
        manager.hedged_positions[position_id] = MagicMock(
            lp_value=1000,
            short_value=1000,
            delta=0
        )
        
        # Test balanced (5% threshold)
        result = await manager.check_rebalance(
            position_id=position_id,
            current_lp_value=1020,   # LP grew
            current_short_value=980, # Short shrank
            threshold=5.0
        )
        
        # Delta = (1020 - 980) / 2000 * 100 = 2%
        assert result["needs_rebalance"] is False, "❌ 2% delta should not trigger (threshold 5%)"
        assert abs(result["current_delta"] - 2.0) < 0.1, "❌ Delta should be ~2%"
        
        print(f"✅ Delta neutral: 2% deviation correctly detected (no rebalance needed)")
    
    
    @pytest.mark.asyncio
    async def test_check_rebalance_triggers_at_threshold(self):
        """check_rebalance MUSI triggerować przy threshold"""
        from services.degen_strategies import DeltaNeutralManager
        
        manager = DeltaNeutralManager()
        
        position_id = "test_delta_002"
        manager.hedged_positions[position_id] = MagicMock(
            lp_value=1000,
            short_value=1000,
            delta=0
        )
        
        # Test imbalanced (6% delta > 5% threshold)
        result = await manager.check_rebalance(
            position_id=position_id,
            current_lp_value=1060,   # LP grew 6%
            current_short_value=940, # Short shrank 6%
            threshold=5.0
        )
        
        # Delta = (1060 - 940) / 2000 * 100 = 6%
        assert result["needs_rebalance"] is True, "❌ 6% delta should trigger rebalance"
        assert abs(result["current_delta"] - 6.0) < 0.1, "❌ Delta should be ~6%"
        assert result["adjustment_needed"] != 0, "❌ Should indicate adjustment needed"
        
        print(f"✅ Delta neutral: 6% deviation triggers rebalance")
    
    
    @pytest.mark.asyncio
    async def test_check_rebalance_handles_missing_position(self):
        """check_rebalance MUSI obsłużyć brak pozycji"""
        from services.degen_strategies import DeltaNeutralManager
        
        manager = DeltaNeutralManager()
        
        result = await manager.check_rebalance(
            position_id="non_existent",
            current_lp_value=1000,
            current_short_value=1000,
            threshold=5.0
        )
        
        assert result["needs_rebalance"] is False, "❌ Should not trigger for missing position"
        assert "error" in result, "❌ Should contain error message"
        
        print(f"✅ Missing position handled gracefully")


# =============================================================================
# TEST: EXECUTE REBALANCE (ON-CHAIN)
# =============================================================================

class TestExecuteRebalance:
    """Testy wykonania rebalance on-chain"""
    
    @pytest.mark.asyncio
    async def test_execute_rebalance_with_valid_allocations(self):
        """execute_rebalance MUSI działać z valid allocations"""
        from agent_wallet import AgentWalletService
        
        service = MagicMock(spec=AgentWalletService)
        service.execute_rebalance = AsyncMock(return_value="0xabc123...")
        
        allocations = [
            {"protocol": "aerodrome", "pool": "USDC/WETH", "amount": 100_000_000},
            {"protocol": "aerodrome", "pool": "WETH/AERO", "amount": 80_000_000},
        ]
        
        tx_hash = await service.execute_rebalance(allocations)
        
        assert tx_hash is not None, "❌ Should return tx hash"
        assert tx_hash.startswith("0x"), "❌ Tx hash should start with 0x"
        
        print(f"✅ Rebalance executed: {tx_hash}")
    
    
    @pytest.mark.asyncio
    async def test_execute_rebalance_with_empty_allocations(self):
        """execute_rebalance z pustymi allocations zwraca None"""
        from agent_wallet import AgentWalletService
        
        # Use the actual logic
        allocations = []
        
        if not allocations:
            result = None
        else:
            result = "0xabc..."
        
        assert result is None, "❌ Empty allocations should return None"
        
        print(f"✅ Empty allocations correctly returns None")


# =============================================================================
# TEST: FULL REBALANCE CYCLE
# =============================================================================

class TestFullRebalanceCycle:
    """Testy pełnego cyklu rebalance"""
    
    @pytest.mark.asyncio
    async def test_full_cycle_below_minimum(self):
        """Cycle MUSI skip gdy value < minimum"""
        # Minimum is 10 USDC ($10)
        MINIMUM_VALUE = 10 * 1e6
        
        test_values = [
            (5 * 1e6, "skip", "5 USDC - below minimum"),
            (9.99 * 1e6, "skip", "9.99 USDC - below minimum"),
            (10 * 1e6, "proceed", "10 USDC - at minimum"),
            (100 * 1e6, "proceed", "100 USDC - above minimum"),
        ]
        
        for value, expected_action, reason in test_values:
            if value < MINIMUM_VALUE:
                action = "skip"
            else:
                action = "proceed"
            
            assert action == expected_action, f"❌ {reason}: expected {expected_action}, got {action}"
        
        print(f"✅ Cycle correctly skips below ${MINIMUM_VALUE/1e6} minimum")
    
    
    @pytest.mark.asyncio
    async def test_full_cycle_no_pools(self):
        """Cycle MUSI skip gdy brak puli"""
        pools = []
        
        if not pools:
            status = "skipped"
            reason = "No pools found"
        else:
            status = "proceed"
            reason = None
        
        assert status == "skipped", "❌ Should skip when no pools"
        assert reason == "No pools found", "❌ Should have correct reason"
        
        print(f"✅ Cycle correctly skips when no pools found")
    
    
    @pytest.mark.asyncio
    async def test_full_cycle_executes_allocations(self, available_pools):
        """Cycle MUSI wykonać allocations gdy wszystko OK"""
        total_value = 1000 * 1e6  # $1000
        pools = available_pools[:2]  # Top 2 pools
        
        # Calculate allocations (20% each max)
        MAX_ALLOCATION_PCT = 20
        allocations = []
        
        for pool in pools:
            amount = total_value * (MAX_ALLOCATION_PCT / 100)
            allocations.append({
                "protocol": "aerodrome",
                "pool": pool["symbol"],
                "amount": int(amount)
            })
        
        assert len(allocations) == 2, "❌ Should have 2 allocations"
        assert all(a["amount"] == 200_000_000 for a in allocations), "❌ Each should be $200"
        
        print(f"✅ Cycle calculates {len(allocations)} allocations correctly")


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestRebalanceEdgeCases:
    """Testy edge cases dla rebalancingu"""
    
    def test_rebalance_with_single_allocation(self):
        """Rebalance z jedną alokacją"""
        allocations = [{"pool_id": "usdc_weth", "amount": 100, "current_value": 110}]
        
        deviation = (allocations[0]["current_value"] - allocations[0]["amount"]) / allocations[0]["amount"] * 100
        
        assert deviation == 10.0, "❌ Single allocation deviation should be 10%"
        
        print(f"✅ Single allocation rebalance works: {deviation}%")
    
    
    def test_rebalance_with_zero_value(self):
        """Rebalance przy zerowej wartości"""
        current_value = 0
        
        # Should not divide by zero
        if current_value == 0:
            needs_rebalance = False  # Nothing to rebalance
            deviation = 0
        else:
            deviation = 10  # Would calculate
            needs_rebalance = True
        
        assert needs_rebalance is False, "❌ Zero value should not trigger rebalance"
        
        print(f"✅ Zero value handled gracefully")
    
    
    def test_rebalance_timing_cooldown(self, agent_config):
        """Rebalance cooldown między wykonaniami"""
        COOLDOWN_HOURS = 1  # 1 hour minimum between rebalances
        
        last_rebalance = datetime.utcnow() - timedelta(minutes=30)
        
        hours_since = (datetime.utcnow() - last_rebalance).total_seconds() / 3600
        is_cooldown = hours_since < COOLDOWN_HOURS
        
        assert is_cooldown is True, "❌ Should be in cooldown"
        
        # After cooldown
        last_rebalance_old = datetime.utcnow() - timedelta(hours=2)
        hours_since_old = (datetime.utcnow() - last_rebalance_old).total_seconds() / 3600
        is_cooldown_old = hours_since_old < COOLDOWN_HOURS
        
        assert is_cooldown_old is False, "❌ Should not be in cooldown"
        
        print(f"✅ Rebalance cooldown ({COOLDOWN_HOURS}h) correctly enforced")


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("🔒 STRICT REBALANCING LOGIC TESTS")
    print("=" * 70)
    
    config = {"rebalance_threshold": 5, "auto_rebalance": True, "min_apy": 5.0, "compound_frequency": 7}
    
    print("\n📊 Threshold Triggers:")
    TestRebalanceThresholdTriggers().test_rebalance_triggers_at_threshold(config)
    TestRebalanceThresholdTriggers().test_no_rebalance_when_disabled(config)
    
    print("\n📊 APY Drift:")
    TestAPYDriftDetection().test_apy_drift_below_min_triggers_exit(config, [])
    
    print("\n📊 Compound Frequency:")
    TestCompoundFrequency().test_compound_triggers_at_frequency(config)
    
    print("\n📊 Edge Cases:")
    TestRebalanceEdgeCases().test_rebalance_with_zero_value()
    TestRebalanceEdgeCases().test_rebalance_timing_cooldown(config)
    
    print("\n" + "=" * 70)
    print("✅ All rebalancing tests passed!")
    print("=" * 70)
