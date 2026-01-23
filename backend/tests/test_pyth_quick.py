"""Quick Pyth Latency Test - 10 fetches"""
import asyncio
import time
import sys
import os
sys.path.insert(0, '.')

from dotenv import load_dotenv
# Load from parent directory (techne-finance/.env)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

print(f"Using RPC: {os.getenv('ALCHEMY_RPC_URL', 'NOT SET')[:50]}...")

from services.price_oracle import PythOracle

async def quick_test():
    print("Quick Pyth Latency Test (10 fetches)")
    print("="*60)
    
    oracle = PythOracle()
    latencies = []
    ages = []
    stale_count = 0
    
    for i in range(10):
        start = time.time()
        result = oracle.get_price("ETH/USD", 30)
        latency = (time.time() - start) * 1000
        latencies.append(latency)
        
        if "error" in result:
            print(f"{i+1}. ERROR: {str(result['error'])[:50]}")
            stale_count += 1
        else:
            age = result.get("age_seconds", 999)
            conf = result.get("confidence", 0)
            price = result.get("price", 0)
            stale = result.get("is_stale", True)
            
            ages.append(age)
            if stale:
                stale_count += 1
            
            status = "🚨 STALE!" if stale else "✓ OK"
            conf_pct = (conf / price * 100) if price > 0 else 0
            print(f"{i+1}. Price: ${price:,.2f} | Age: {age:.1f}s | Conf: {conf_pct:.4f}% | Latency: {latency:.0f}ms | {status}")
        
        await asyncio.sleep(1)
    
    print("="*60)
    print("SUMMARY:")
    print(f"  Avg Latency: {sum(latencies)/len(latencies):.0f}ms")
    print(f"  Max Latency: {max(latencies):.0f}ms")
    print(f"  Avg Age: {sum(ages)/len(ages):.1f}s" if ages else "  Avg Age: N/A")
    print(f"  Stale Count: {stale_count}/10")
    
    # Validation
    avg_latency = sum(latencies)/len(latencies)
    if avg_latency < 500:
        print(f"\n✅ PASSED: Latency {avg_latency:.0f}ms < 500ms")
    else:
        print(f"\n❌ FAILED: Latency {avg_latency:.0f}ms > 500ms")
    
    if ages:
        avg_age = sum(ages)/len(ages)
        if avg_age < 30:
            print(f"✅ PASSED: Age {avg_age:.1f}s < 30s")
        else:
            print(f"❌ FAILED: Age {avg_age:.1f}s > 30s - bot will be blocked!")

if __name__ == "__main__":
    asyncio.run(quick_test())
