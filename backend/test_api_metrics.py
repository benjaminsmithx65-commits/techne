import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

# Ensure credentials loaded
if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
    print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

from infrastructure.supabase_client import SupabaseClient

async def test():
    supabase = SupabaseClient()
    print(f"Supabase available: {supabase.is_available}")
    
    # Test api_call_logs
    result = await supabase.get_recent_api_calls(limit=5)
    print(f"api_call_logs table: OK ({len(result)} records)")
    
    # Test logging a call
    success = await supabase.log_api_call(
        service="geckoterminal",
        endpoint="/pools/test",
        status="success",
        response_time_ms=456.78
    )
    print(f"Insert test: {'OK' if success else 'FAILED'}")
    
    # Check if it was inserted
    result2 = await supabase.get_recent_api_calls(service="geckoterminal", limit=3)
    print(f"Read back: {len(result2)} records")
    for r in result2:
        print(f"  - {r.get('service')}: {r.get('endpoint')} ({r.get('response_time_ms')}ms)")
    
asyncio.run(test())
