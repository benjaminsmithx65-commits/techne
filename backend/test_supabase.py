"""
Test inserting and reading a position from Supabase
"""
import os
import httpx
import asyncio

async def test_insert_and_read():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ SUPABASE_URL and SUPABASE_KEY must be set in environment")
        return
    
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    print("Testing Supabase insert and read...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Insert test position
        test_data = {
            "user_address": "0xtestwallet123",
            "protocol": "aave_test",
            "entry_value": 100.0,
            "current_value": 105.0,
            "asset": "USDC",
            "pool_type": "single",
            "apy": 6.5,
            "status": "active"
        }
        
        print(f"Inserting test position...")
        resp = await client.post(
            f"{url}/rest/v1/user_positions",
            headers=headers,
            json=test_data
        )
        
        if resp.status_code in [200, 201]:
            print(f"✅ Insert successful!")
            print(f"   Response: {resp.json()}")
        else:
            print(f"❌ Insert failed: {resp.status_code}")
            print(f"   Error: {resp.text}")
            return
        
        # Read back
        print(f"\nReading positions for 0xtestwallet123...")
        resp = await client.get(
            f"{url}/rest/v1/user_positions",
            headers=headers,
            params={
                "user_address": "eq.0xtestwallet123",
                "status": "eq.active",
                "select": "*"
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Read successful! Found {len(data)} positions")
            for pos in data:
                print(f"   - {pos['protocol']}: ${pos['current_value']} ({pos['apy']}% APY)")
        else:
            print(f"❌ Read failed: {resp.status_code}")
            print(f"   Error: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_insert_and_read())
