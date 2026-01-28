"""
Run API Metrics Migration in Supabase
Execute this script to create the required tables.
"""
import httpx
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

# Test by inserting a sample record
async def test_insert():
    """Test write access to api_metrics_daily table"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    from datetime import datetime
    data = {
        "date": datetime.utcnow().date().isoformat(),
        "service": "test_connection",
        "total_calls": 1,
        "success_count": 1,
        "error_count": 0,
        "avg_response_ms": 100.0
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try to insert
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/api_metrics_daily",
            headers=headers,
            json=data
        )
        
        if resp.status_code in [200, 201]:
            print("✅ SUCCESS: Table api_metrics_daily exists and is writable!")
            print(f"   Response: {resp.json()}")
            
            # Clean up test record
            await client.delete(
                f"{SUPABASE_URL}/rest/v1/api_metrics_daily",
                headers=headers,
                params={"service": "eq.test_connection"}
            )
            print("   Cleaned up test record.")
            return True
        elif resp.status_code == 404:
            print("❌ ERROR: Table api_metrics_daily does not exist!")
            print("   Please run the migration SQL in Supabase SQL Editor:")
            print("   File: backend/migrations/run_api_metrics_migration.sql")
            return False
        else:
            print(f"❌ ERROR: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return False

async def check_tables():
    """Check which tables exist"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    tables = ["api_metrics_daily", "api_metrics_weekly"]
    
    print("\n📊 Checking API Metrics Tables...")
    print("-" * 40)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for table in tables:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers=headers,
                params={"limit": "1"}
            )
            
            if resp.status_code == 200:
                print(f"  ✅ {table}: EXISTS")
            else:
                print(f"  ❌ {table}: MISSING (run migration)")

if __name__ == "__main__":
    print("🔍 Testing Supabase API Metrics Integration")
    print("=" * 50)
    asyncio.run(check_tables())
    print()
    asyncio.run(test_insert())
