import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
import httpx
from collections import defaultdict

# Validate env
if not os.getenv('SUPABASE_URL') or not os.getenv('SUPABASE_KEY'):
    print("❌ SUPABASE_URL and SUPABASE_KEY must be set")
    exit(1)

async def detailed_report():
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
    
    async with httpx.AsyncClient() as client:
        # Get all recent records (up to 500)
        resp = await client.get(
            f'{url}/rest/v1/api_call_logs', 
            headers=headers, 
            params={'select': '*', 'order': 'timestamp.desc', 'limit': '500'}
        )
        data = resp.json()
        
        print(f"=== API METRICS REPORT ===")
        print(f"Total records: {len(data)}\n")
        
        # Group by service
        by_service = defaultdict(list)
        for r in data:
            by_service[r.get('service', 'unknown')].append(r)
        
        print(f"{'SERVICE':<20} {'CALLS':>8} {'SUCCESS':>8} {'AVG MS':>10} {'MIN MS':>10} {'MAX MS':>10}")
        print("-" * 76)
        
        for service, calls in sorted(by_service.items()):
            total = len(calls)
            success = sum(1 for c in calls if c.get('status') == 'success')
            times = [c.get('response_time_ms', 0) for c in calls]
            avg_ms = sum(times) / len(times) if times else 0
            min_ms = min(times) if times else 0
            max_ms = max(times) if times else 0
            
            print(f"{service:<20} {total:>8} {success:>8} {avg_ms:>10.0f} {min_ms:>10.0f} {max_ms:>10.0f}")
        
        print("\n=== ENDPOINTS BREAKDOWN ===")
        
        # Group by service + endpoint
        by_endpoint = defaultdict(list)
        for r in data:
            key = f"{r.get('service', '?')}: {r.get('endpoint', '?')}"
            by_endpoint[key].append(r)
        
        print(f"\n{'ENDPOINT':<50} {'CALLS':>6} {'AVG MS':>10}")
        print("-" * 70)
        
        for endpoint, calls in sorted(by_endpoint.items(), key=lambda x: -len(x[1]))[:20]:
            total = len(calls)
            times = [c.get('response_time_ms', 0) for c in calls]
            avg_ms = sum(times) / len(times) if times else 0
            print(f"{endpoint[:50]:<50} {total:>6} {avg_ms:>10.0f}")

asyncio.run(detailed_report())
