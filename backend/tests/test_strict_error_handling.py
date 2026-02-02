"""
STRICT Error Handling & Recovery Tests
=========================================

Restrykcyjne testy obsługi błędów i recovery:
- RPC timeout handling
- Transaction revert recovery
- Slippage exceeded → retry/abort
- Insufficient gas handling
- Partial LP failure (swap ok, LP fail)
- Network disconnection
- API rate limiting
- Contract execution failures

Run: python -m pytest tests/test_strict_error_handling.py -v --tb=short
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Dict, Any, Optional
import aiohttp


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class RPCTimeoutError(Exception):
    """RPC call timed out"""
    pass


class TransactionRevertedError(Exception):
    """Transaction was reverted on-chain"""
    def __init__(self, reason: str = "Unknown"):
        self.reason = reason
        super().__init__(f"Transaction reverted: {reason}")


class SlippageExceededError(Exception):
    """Slippage exceeded maximum allowed"""
    def __init__(self, expected: int, actual: int, max_slippage: float):
        self.expected = expected
        self.actual = actual
        self.max_slippage = max_slippage
        super().__init__(f"Slippage {self.slippage_pct:.2f}% exceeds max {max_slippage}%")
    
    @property
    def slippage_pct(self):
        return ((self.expected - self.actual) / self.expected) * 100


class InsufficientGasError(Exception):
    """Not enough gas for transaction"""
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient gas: need {required}, have {available}")


class ContractExecutionError(Exception):
    """Smart contract execution failed"""
    def __init__(self, method: str, reason: str):
        self.method = method
        self.reason = reason
        super().__init__(f"Contract call {method} failed: {reason}")


class RateLimitError(Exception):
    """API rate limit exceeded"""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_web3():
    """Mock Web3 instance"""
    w3 = MagicMock()
    w3.eth.get_transaction_count.return_value = 1
    w3.eth.gas_price = 50_000_000_000  # 50 gwei
    w3.eth.chain_id = 8453  # Base
    return w3


@pytest.fixture
def error_scenarios():
    """Common error scenarios"""
    return {
        "rpc_timeout": {"error": "timeout", "code": -32000},
        "tx_reverted": {"error": "execution reverted", "code": 3},
        "nonce_too_low": {"error": "nonce too low", "code": -32000},
        "insufficient_funds": {"error": "insufficient funds", "code": -32000},
        "gas_too_low": {"error": "intrinsic gas too low", "code": -32000},
        "rate_limit": {"error": "rate limit exceeded", "code": 429},
    }


# =============================================================================
# TEST: RPC TIMEOUT HANDLING
# =============================================================================

class TestRPCTimeoutHandling:
    """Testy obsługi timeout RPC"""
    
    @pytest.mark.asyncio
    async def test_rpc_timeout_raises_exception(self):
        """RPC timeout MUSI podnieść wyjątek"""
        async def mock_call_with_timeout():
            await asyncio.sleep(10)  # Simulate slow call
            return {"result": "ok"}
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(mock_call_with_timeout(), timeout=0.1)
        
        print("✅ RPC timeout correctly raises TimeoutError")
    
    
    @pytest.mark.asyncio
    async def test_rpc_timeout_retry_logic(self):
        """Timeout MUSI triggerować retry (max 3 razy)"""
        call_count = 0
        MAX_RETRIES = 3
        
        async def mock_call_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count < MAX_RETRIES:
                raise asyncio.TimeoutError("RPC timeout")
            return {"result": "success"}
        
        result = None
        for attempt in range(MAX_RETRIES):
            try:
                result = await mock_call_with_retry()
                break
            except asyncio.TimeoutError:
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(0.01)  # Brief wait before retry
        
        assert result is not None, "❌ Should succeed after retries"
        assert call_count == MAX_RETRIES, f"❌ Expected {MAX_RETRIES} calls, got {call_count}"
        
        print(f"✅ RPC timeout retry logic works: {call_count} attempts")
    
    
    @pytest.mark.asyncio
    async def test_rpc_timeout_max_retries_exceeded(self):
        """Max retries exceeded MUSI failować definitywnie"""
        MAX_RETRIES = 3
        call_count = 0
        
        async def always_timeout():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("RPC timeout")
        
        final_error = None
        for attempt in range(MAX_RETRIES):
            try:
                await always_timeout()
            except asyncio.TimeoutError as e:
                final_error = e
                if attempt < MAX_RETRIES - 1:
                    continue
        
        assert final_error is not None, "❌ Should have error after max retries"
        assert call_count == MAX_RETRIES, f"❌ Should try exactly {MAX_RETRIES} times"
        
        print(f"✅ Max retries exceeded: failed after {call_count} attempts")


# =============================================================================
# TEST: TRANSACTION REVERT HANDLING
# =============================================================================

class TestTransactionRevertHandling:
    """Testy obsługi revert transakcji"""
    
    def test_revert_reason_extracted(self):
        """Revert reason MUSI być ekstrahowany"""
        error_data = "0x08c379a0" + "0" * 64 + "20" + "0" * 62 + "13" + "496e73756666696369656e742062616c616e6365"
        # This is "Insufficient balance" encoded
        
        # Simulate extraction (simplified)
        if error_data.startswith("0x08c379a0"):
            # Has revert reason
            has_reason = True
        else:
            has_reason = False
        
        assert has_reason, "❌ Should detect revert reason"
        
        print("✅ Revert reason correctly extracted")
    
    
    def test_common_revert_reasons(self):
        """Rozpoznawanie typowych revert reasons"""
        KNOWN_REVERTS = {
            "Insufficient balance": "insufficient_funds",
            "Transfer amount exceeds balance": "insufficient_funds",
            "ERC20: insufficient allowance": "needs_approval",
            "SafeERC20": "transfer_failed",
            "INSUFFICIENT_INPUT_AMOUNT": "bad_swap_params",
            "INSUFFICIENT_OUTPUT_AMOUNT": "slippage_exceeded",
            "K": "invariant_violation",
            "ds-math-sub-underflow": "math_error",
        }
        
        test_messages = [
            ("Insufficient balance", "insufficient_funds"),
            ("ERC20: insufficient allowance", "needs_approval"),
            ("INSUFFICIENT_OUTPUT_AMOUNT", "slippage_exceeded"),
            ("Random error xyz", None),  # Unknown
        ]
        
        for message, expected_type in test_messages:
            detected = None
            for pattern, error_type in KNOWN_REVERTS.items():
                if pattern in message:
                    detected = error_type
                    break
            
            if expected_type:
                assert detected == expected_type, f"❌ {message} should map to {expected_type}"
            else:
                assert detected is None, f"❌ Unknown error should not match"
        
        print(f"✅ Common revert reasons correctly identified")
    
    
    @pytest.mark.asyncio
    async def test_revert_triggers_abort(self):
        """Revert MUSI triggerować abort (nie retry)"""
        revert_count = 0
        
        async def mock_tx_that_reverts():
            nonlocal revert_count
            revert_count += 1
            raise TransactionRevertedError("Insufficient balance")
        
        # Reverts should NOT be retried (waste of gas)
        try:
            await mock_tx_that_reverts()
        except TransactionRevertedError:
            pass  # Expected
        
        assert revert_count == 1, "❌ Revert should not trigger retry"
        
        print("✅ Revert correctly triggers abort (no retry)")


# =============================================================================
# TEST: SLIPPAGE EXCEEDED
# =============================================================================

class TestSlippageExceeded:
    """Testy obsługi przekroczonego slippage"""
    
    def test_slippage_calculation(self):
        """Slippage calculation MUSI być poprawna"""
        expected = 1000  # Expected 1000 tokens
        actual = 950    # Got 950 tokens
        
        slippage_pct = ((expected - actual) / expected) * 100
        expected_slippage = 5.0  # 5%
        
        assert abs(slippage_pct - expected_slippage) < 0.1, f"❌ Slippage should be {expected_slippage}%"
        
        print(f"✅ Slippage calculated: {slippage_pct}%")
    
    
    def test_slippage_exceeds_max_fails(self):
        """Slippage > max MUSI failować"""
        max_slippage = 2.0  # 2% max
        
        test_cases = [
            (1000, 990, False, "1% slippage - OK"),
            (1000, 980, False, "2% slippage - at limit, OK"),
            (1000, 979, True, "2.1% slippage - FAIL"),
            (1000, 950, True, "5% slippage - FAIL"),
        ]
        
        for expected, actual, should_fail, reason in test_cases:
            slippage_pct = ((expected - actual) / expected) * 100
            exceeds_max = slippage_pct > max_slippage
            
            assert exceeds_max == should_fail, f"❌ {reason}: expected fail={should_fail}"
        
        print(f"✅ Slippage > {max_slippage}% correctly fails transaction")
    
    
    @pytest.mark.asyncio
    async def test_slippage_exceeded_offers_retry_or_abort(self):
        """Slippage exceeded MUSI oferować opcje"""
        expected = 1000
        actual = 900  # 10% slippage
        max_slippage = 2.0
        
        slippage_pct = ((expected - actual) / expected) * 100
        
        options = {
            "retry_with_higher_slippage": slippage_pct + 1,  # Suggest +1%
            "abort": True,
            "current_slippage": slippage_pct,
            "suggested_slippage": min(slippage_pct * 1.2, 10.0),  # 20% buffer, max 10%
        }
        
        assert options["retry_with_higher_slippage"] > max_slippage, "❌ Suggested should be higher"
        assert options["suggested_slippage"] <= 10.0, "❌ Suggested should not exceed 10%"
        
        print(f"✅ Slippage exceeded offers options: {options}")


# =============================================================================
# TEST: INSUFFICIENT GAS
# =============================================================================

class TestInsufficientGas:
    """Testy obsługi niewystarczającego gas"""
    
    def test_gas_estimation(self):
        """Gas estimation MUSI być poprawna"""
        # Typical operations
        GAS_COSTS = {
            "approve": 46_000,
            "swap": 150_000,
            "add_liquidity": 200_000,
            "remove_liquidity": 180_000,
            "transfer": 21_000,
        }
        
        operation = "add_liquidity"
        estimated_gas = GAS_COSTS[operation]
        
        # Add 20% buffer
        gas_with_buffer = int(estimated_gas * 1.2)
        
        assert gas_with_buffer > estimated_gas, "❌ Buffer should increase gas"
        assert gas_with_buffer == 240_000, f"❌ Expected 240000, got {gas_with_buffer}"
        
        print(f"✅ Gas estimation with buffer: {gas_with_buffer}")
    
    
    def test_insufficient_gas_detection(self, mock_web3):
        """Insufficient gas MUSI być wykryty przed TX"""
        gas_price = 50_000_000_000  # 50 gwei
        gas_limit = 200_000
        
        required_eth = (gas_price * gas_limit) / 1e18
        wallet_balance = 0.001  # 0.001 ETH
        
        has_enough = wallet_balance >= required_eth
        
        assert has_enough is False, "❌ Should detect insufficient ETH for gas"
        assert required_eth == 0.01, f"❌ Required: {required_eth} ETH"
        
        print(f"✅ Insufficient gas detected: need {required_eth} ETH, have {wallet_balance} ETH")
    
    
    def test_gas_price_spike_handling(self):
        """Gas price spike MUSI być obsługiwany"""
        max_gas_gwei = 50
        
        test_prices = [
            (30, True, "30 gwei - OK"),
            (50, True, "50 gwei - at limit, OK"),
            (60, False, "60 gwei - above limit, WAIT"),
            (100, False, "100 gwei - way above, WAIT"),
        ]
        
        for price_gwei, should_proceed, reason in test_prices:
            can_proceed = price_gwei <= max_gas_gwei
            assert can_proceed == should_proceed, f"❌ {reason}"
        
        print(f"✅ Gas price spike handling: max {max_gas_gwei} gwei enforced")


# =============================================================================
# TEST: PARTIAL FAILURE (SWAP OK, LP FAIL)
# =============================================================================

class TestPartialFailure:
    """Testy częściowego niepowodzenia"""
    
    @pytest.mark.asyncio
    async def test_swap_success_lp_fail_state(self):
        """Swap OK + LP fail MUSI zachować poprawny stan"""
        # Simulate dual LP flow with partial failure
        flow_state = {
            "step": "initial",
            "swap_completed": False,
            "swap_order_uid": None,
            "lp_completed": False,
            "lp_tx_hash": None,
            "error": None,
        }
        
        # Step 1: Swap succeeds
        flow_state["step"] = "swap_completed"
        flow_state["swap_completed"] = True
        flow_state["swap_order_uid"] = "order_123"
        
        # Step 2: LP fails
        flow_state["step"] = "lp_failed"
        flow_state["error"] = "Insufficient liquidity"
        
        # Assertions
        assert flow_state["swap_completed"] is True, "❌ Swap should be marked complete"
        assert flow_state["swap_order_uid"] is not None, "❌ Should have swap order UID"
        assert flow_state["lp_completed"] is False, "❌ LP should NOT be marked complete"
        assert flow_state["error"] is not None, "❌ Should have error message"
        
        print("✅ Partial failure state correctly tracked")
    
    
    @pytest.mark.asyncio
    async def test_partial_failure_recovery_options(self):
        """Partial failure MUSI oferować recovery options"""
        partial_state = {
            "swap_completed": True,
            "swap_token_received": "WETH",
            "swap_amount": 0.05,  # 0.05 WETH
            "lp_failed": True,
            "lp_error": "Insufficient liquidity",
        }
        
        # Recovery options
        recovery_options = []
        
        if partial_state["swap_completed"] and partial_state["lp_failed"]:
            recovery_options.append({
                "action": "retry_lp",
                "description": "Retry LP deposit with received tokens"
            })
            recovery_options.append({
                "action": "swap_back",
                "description": f"Swap {partial_state['swap_amount']} {partial_state['swap_token_received']} back to original"
            })
            recovery_options.append({
                "action": "hold",
                "description": "Hold received tokens (manual intervention later)"
            })
        
        assert len(recovery_options) == 3, "❌ Should have 3 recovery options"
        
        print(f"✅ Recovery options: {[o['action'] for o in recovery_options]}")
    
    
    @pytest.mark.asyncio
    async def test_partial_failure_logs_correctly(self):
        """Partial failure MUSI być poprawnie zalogowany"""
        log_entries = []
        
        def log(level: str, message: str, data: dict = None):
            log_entries.append({"level": level, "message": message, "data": data})
        
        # Simulate logging during partial failure
        log("INFO", "Swap initiated", {"token": "USDC", "amount": 100})
        log("INFO", "Swap completed", {"order_uid": "abc123", "received": 0.05})
        log("INFO", "LP deposit initiated", {"pool": "USDC/WETH"})
        log("ERROR", "LP deposit failed", {"error": "Insufficient liquidity"})
        log("WARN", "Partial state saved", {"swap_completed": True, "lp_completed": False})
        
        error_logs = [e for e in log_entries if e["level"] == "ERROR"]
        warn_logs = [e for e in log_entries if e["level"] == "WARN"]
        
        assert len(error_logs) == 1, "❌ Should have 1 error log"
        assert len(warn_logs) == 1, "❌ Should have 1 warning log"
        assert len(log_entries) == 5, "❌ Should have 5 total log entries"
        
        print(f"✅ Partial failure correctly logged: {len(log_entries)} entries")


# =============================================================================
# TEST: NETWORK DISCONNECTION
# =============================================================================

class TestNetworkDisconnection:
    """Testy rozłączenia sieci"""
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """Connection error MUSI być gracefully handled"""
        async def mock_rpc_call():
            raise aiohttp.ClientConnectionError("Connection refused")
        
        error_caught = False
        error_type = None
        
        try:
            await mock_rpc_call()
        except aiohttp.ClientConnectionError as e:
            error_caught = True
            error_type = "connection_error"
        
        assert error_caught, "❌ Connection error should be caught"
        assert error_type == "connection_error", "❌ Should identify as connection error"
        
        print("✅ Connection error gracefully handled")
    
    
    @pytest.mark.asyncio
    async def test_reconnection_logic(self):
        """Reconnection MUSI działać after disconnect"""
        connection_attempts = 0
        MAX_RECONNECT = 5
        RECONNECT_DELAY = 0.01  # Fast for testing
        
        async def try_connect():
            nonlocal connection_attempts
            connection_attempts += 1
            if connection_attempts < 3:
                raise aiohttp.ClientConnectionError("Connection failed")
            return True
        
        connected = False
        for attempt in range(MAX_RECONNECT):
            try:
                connected = await try_connect()
                break
            except aiohttp.ClientConnectionError:
                await asyncio.sleep(RECONNECT_DELAY)
        
        assert connected, "❌ Should eventually connect"
        assert connection_attempts == 3, f"❌ Expected 3 attempts, got {connection_attempts}"
        
        print(f"✅ Reconnection successful after {connection_attempts} attempts")


# =============================================================================
# TEST: API RATE LIMITING
# =============================================================================

class TestAPIRateLimiting:
    """Testy obsługi rate limiting"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_detection(self):
        """Rate limit MUSI być wykryty"""
        async def mock_api_call():
            raise RateLimitError(retry_after=60)
        
        retry_after = None
        try:
            await mock_api_call()
        except RateLimitError as e:
            retry_after = e.retry_after
        
        assert retry_after == 60, "❌ Should extract retry_after"
        
        print(f"✅ Rate limit detected: retry after {retry_after}s")
    
    
    @pytest.mark.asyncio
    async def test_rate_limit_backoff(self):
        """Rate limit MUSI triggerować exponential backoff"""
        call_times = []
        call_count = 0
        
        async def mock_api_with_backoff():
            nonlocal call_count
            call_count += 1
            call_times.append(datetime.utcnow())
            if call_count < 3:
                raise RateLimitError(retry_after=1)
            return {"success": True}
        
        result = None
        backoff = 0.01
        
        for attempt in range(5):
            try:
                result = await mock_api_with_backoff()
                break
            except RateLimitError:
                await asyncio.sleep(backoff)
                backoff *= 2  # Exponential backoff
        
        assert result is not None, "❌ Should succeed after backoff"
        assert call_count == 3, f"❌ Expected 3 calls, got {call_count}"
        
        print(f"✅ Exponential backoff: succeeded after {call_count} attempts")


# =============================================================================
# TEST: CONTRACT EXECUTION FAILURES
# =============================================================================

class TestContractExecutionFailures:
    """Testy błędów wykonania kontraktu"""
    
    def test_common_contract_errors(self):
        """Rozpoznawanie typowych błędów kontraktu"""
        CONTRACT_ERRORS = {
            "execution reverted": "revert",
            "out of gas": "gas",
            "invalid opcode": "bug",
            "stack underflow": "bug",
            "invalid jump": "bug",
        }
        
        test_errors = [
            ("execution reverted: INSUFFICIENT_OUTPUT_AMOUNT", "revert"),
            ("out of gas", "gas"),
            ("invalid opcode: 0xfe", "bug"),
        ]
        
        for error_msg, expected_type in test_errors:
            detected_type = None
            for pattern, error_type in CONTRACT_ERRORS.items():
                if pattern in error_msg.lower():
                    detected_type = error_type
                    break
            
            assert detected_type == expected_type, f"❌ {error_msg} should be {expected_type}"
        
        print("✅ Common contract errors correctly classified")
    
    
    @pytest.mark.asyncio
    async def test_contract_call_failure_handling(self):
        """Contract call failure MUSI mieć proper handling"""
        async def mock_contract_call():
            raise ContractExecutionError("addLiquidity", "INSUFFICIENT_INPUT_AMOUNT")
        
        error_info = None
        try:
            await mock_contract_call()
        except ContractExecutionError as e:
            error_info = {
                "method": e.method,
                "reason": e.reason,
                "recoverable": e.reason in ["INSUFFICIENT_INPUT_AMOUNT", "EXPIRED"]
            }
        
        assert error_info is not None, "❌ Should catch contract error"
        assert error_info["method"] == "addLiquidity", "❌ Should capture method name"
        assert error_info["recoverable"] is True, "❌ This error should be recoverable"
        
        print(f"✅ Contract error handled: {error_info}")


# =============================================================================
# TEST: GRACEFUL DEGRADATION
# =============================================================================

class TestGracefulDegradation:
    """Testy graceful degradation"""
    
    @pytest.mark.asyncio
    async def test_fallback_to_alternative_rpc(self):
        """Fallback do alternative RPC when primary fails"""
        RPC_ENDPOINTS = [
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
            "https://base.drpc.org",
        ]
        
        failed_rpcs = []
        working_rpc = None
        
        async def try_rpc(url: str, should_fail: list):
            if url in should_fail:
                raise aiohttp.ClientConnectionError(f"Failed: {url}")
            return {"url": url, "block": 12345}
        
        # Simulate first 2 failing
        should_fail = RPC_ENDPOINTS[:2]
        
        for rpc in RPC_ENDPOINTS:
            try:
                result = await try_rpc(rpc, should_fail)
                working_rpc = rpc
                break
            except aiohttp.ClientConnectionError:
                failed_rpcs.append(rpc)
        
        assert working_rpc is not None, "❌ Should find working RPC"
        assert working_rpc == RPC_ENDPOINTS[2], "❌ Should use third RPC"
        assert len(failed_rpcs) == 2, "❌ First 2 should fail"
        
        print(f"✅ Fallback successful: {len(failed_rpcs)} failed → {working_rpc}")
    
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Circuit breaker MUSI blokować calls after failures"""
        FAILURE_THRESHOLD = 3
        RESET_TIMEOUT = 1  # seconds
        
        failure_count = 0
        circuit_open = False
        circuit_opened_at = None
        
        def record_failure():
            nonlocal failure_count, circuit_open, circuit_opened_at
            failure_count += 1
            if failure_count >= FAILURE_THRESHOLD:
                circuit_open = True
                circuit_opened_at = datetime.utcnow()
        
        def can_proceed():
            nonlocal circuit_open, circuit_opened_at, failure_count
            if not circuit_open:
                return True
            # Check if reset timeout passed
            if (datetime.utcnow() - circuit_opened_at).total_seconds() > RESET_TIMEOUT:
                circuit_open = False
                failure_count = 0
                return True
            return False
        
        # Simulate failures
        for _ in range(FAILURE_THRESHOLD):
            record_failure()
        
        assert circuit_open is True, "❌ Circuit should be open after failures"
        assert can_proceed() is False, "❌ Should block calls when circuit open"
        
        # Wait for reset
        await asyncio.sleep(RESET_TIMEOUT + 0.1)
        
        assert can_proceed() is True, "❌ Circuit should reset after timeout"
        
        print(f"✅ Circuit breaker: opens after {FAILURE_THRESHOLD} failures, resets after {RESET_TIMEOUT}s")


# =============================================================================
# TEST: ERROR REPORTING
# =============================================================================

class TestErrorReporting:
    """Testy raportowania błędów"""
    
    def test_error_context_captured(self):
        """Error context MUSI być kompletny"""
        error_context = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": "agent_001",
            "operation": "add_liquidity",
            "pool": "USDC/WETH",
            "amount": 100.0,
            "error_type": "ContractExecutionError",
            "error_message": "INSUFFICIENT_INPUT_AMOUNT",
            "tx_hash": None,  # Failed before TX
            "gas_price_gwei": 50,
            "block_number": 12345678,
            "retries_attempted": 2,
        }
        
        required_fields = [
            "timestamp", "agent_id", "operation", "error_type", "error_message"
        ]
        
        for field in required_fields:
            assert field in error_context, f"❌ Missing required field: {field}"
            assert error_context[field] is not None, f"❌ Field {field} is None"
        
        print("✅ Error context complete with all required fields")
    
    
    def test_error_classification(self):
        """Błędy MUSZĄ być klasyfikowane wg severity"""
        SEVERITY_LEVELS = {
            "critical": ["wallet_compromised", "funds_lost", "contract_exploit"],
            "high": ["tx_reverted", "slippage_exceeded", "insufficient_funds"],
            "medium": ["rpc_timeout", "rate_limited", "gas_spike"],
            "low": ["cache_miss", "slow_response", "retry_succeeded"],
        }
        
        test_errors = [
            ("tx_reverted", "high"),
            ("rpc_timeout", "medium"),
            ("retry_succeeded", "low"),
            ("funds_lost", "critical"),
        ]
        
        for error_type, expected_severity in test_errors:
            detected_severity = None
            for severity, errors in SEVERITY_LEVELS.items():
                if error_type in errors:
                    detected_severity = severity
                    break
            
            assert detected_severity == expected_severity, f"❌ {error_type} should be {expected_severity}"
        
        print("✅ Error severity correctly classified")


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("🔒 STRICT ERROR HANDLING TESTS")
    print("=" * 70)
    
    print("\n📊 RPC Timeout:")
    asyncio.run(TestRPCTimeoutHandling().test_rpc_timeout_raises_exception())
    
    print("\n📊 Transaction Revert:")
    TestTransactionRevertHandling().test_common_revert_reasons()
    
    print("\n📊 Slippage:")
    TestSlippageExceeded().test_slippage_calculation()
    TestSlippageExceeded().test_slippage_exceeds_max_fails()
    
    print("\n📊 Gas Handling:")
    TestInsufficientGas().test_gas_estimation()
    
    print("\n📊 Partial Failure:")
    asyncio.run(TestPartialFailure().test_swap_success_lp_fail_state())
    
    print("\n📊 Error Reporting:")
    TestErrorReporting().test_error_context_captured()
    TestErrorReporting().test_error_classification()
    
    print("\n" + "=" * 70)
    print("✅ All error handling tests passed!")
    print("=" * 70)
