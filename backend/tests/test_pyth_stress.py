"""
Pyth Oracle Stress Test
5-minute continuous monitoring of price freshness

Tests:
- Latency to Pyth Network
- Price staleness detection
- Confidence intervals
- Alert on stale data (>30s)
"""

import asyncio
import time
from datetime import datetime
from services.price_oracle import PythOracle

# ANSI colors for terminal
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


async def stress_test_pyth(duration_seconds: int = 300, interval: float = 1.0):
    """
    Stress test Pyth Oracle for specified duration.
    
    Args:
        duration_seconds: How long to run (default 5 minutes)
        interval: Seconds between price fetches (default 1s)
    """
    print("="*70)
    print(f"{BOLD}PYTH ORACLE STRESS TEST{RESET}")
    print(f"Duration: {duration_seconds}s | Interval: {interval}s | Max Age: 30s")
    print("="*70)
    print()
    
    oracle = PythOracle()
    
    start_time = time.time()
    fetch_count = 0
    stale_count = 0
    error_count = 0
    latencies = []
    
    print(f"{'Time':^10} | {'Price':^12} | {'Conf':^10} | {'Age':^8} | {'Latency':^10} | Status")
    print("-"*70)
    
    while (time.time() - start_time) < duration_seconds:
        fetch_start = time.time()
        
        try:
            price_data = oracle.get_price("ETH/USD", max_age_seconds=30)
            latency = (time.time() - fetch_start) * 1000  # ms
            latencies.append(latency)
            
            fetch_count += 1
            
            # Format output
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if "error" in price_data:
                error_count += 1
                print(f"{timestamp:^10} | {'ERROR':^12} | {'-':^10} | {'-':^8} | {latency:>7.0f}ms | {RED}⚠ {price_data['error'][:30]}{RESET}")
            else:
                price = price_data.get("price", 0)
                conf = price_data.get("confidence", 0)
                age = price_data.get("age_seconds", 999)
                is_stale = price_data.get("is_stale", True)
                
                if is_stale:
                    stale_count += 1
                    status = f"{RED}{BOLD}🚨 STALE DATA ALERT! Age={age:.1f}s > 30s{RESET}"
                elif age > 20:
                    status = f"{YELLOW}⚠ Warning: Age approaching limit{RESET}"
                else:
                    status = f"{GREEN}✓ Fresh{RESET}"
                
                print(f"{timestamp:^10} | ${price:>10,.2f} | ±${conf:>7.4f} | {age:>5.1f}s | {latency:>7.0f}ms | {status}")
        
        except Exception as e:
            error_count += 1
            print(f"{datetime.now().strftime('%H:%M:%S'):^10} | {RED}EXCEPTION: {str(e)[:40]}{RESET}")
        
        # Wait for next interval
        elapsed = time.time() - fetch_start
        if elapsed < interval:
            await asyncio.sleep(interval - elapsed)
    
    # Summary
    print()
    print("="*70)
    print(f"{BOLD}TEST SUMMARY{RESET}")
    print("="*70)
    print(f"  Total Fetches: {fetch_count}")
    print(f"  Stale Alerts:  {stale_count} ({stale_count/fetch_count*100:.1f}%)" if fetch_count > 0 else "  Stale Alerts: 0")
    print(f"  Errors:        {error_count}")
    
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        print(f"\n  Latency Stats:")
        print(f"    Average: {avg_latency:.0f}ms")
        print(f"    Min:     {min_latency:.0f}ms")
        print(f"    Max:     {max_latency:.0f}ms")
    
    # Final verdict
    print()
    if stale_count == 0 and error_count == 0:
        print(f"{GREEN}{BOLD}✅ PASSED: Pyth Oracle is reliable for trading{RESET}")
    elif error_count > fetch_count * 0.1:
        print(f"{RED}{BOLD}❌ FAILED: Too many errors ({error_count}/{fetch_count}){RESET}")
    elif stale_count > fetch_count * 0.05:
        print(f"{YELLOW}{BOLD}⚠ WARNING: Stale data detected - check RPC connection{RESET}")
    else:
        print(f"{GREEN}✓ PASSED with minor issues{RESET}")
    
    print("="*70)


if __name__ == "__main__":
    print("\n🔥 Starting Pyth Oracle Stress Test (5 minutes)\n")
    print("Press Ctrl+C to stop early\n")
    
    try:
        asyncio.run(stress_test_pyth(duration_seconds=300, interval=1.0))
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
