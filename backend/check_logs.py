import asyncio
import os
os.environ['SUPABASE_URL'] = 'https://qbsllpllbulbocuypsjy.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFic2xscGxsYnVsYm9jdXlwc2p5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg5ODIwMjgsImV4cCI6MjA4NDU1ODAyOH0.iZzL6e8Eqc_eOoxvOWq3JXFhAzfHwSUWJ4S8XfcBviY'
import httpx

async def check():
    url = 'https://qbsllpllbulbocuypsjy.supabase.co'
    key = os.environ['SUPABASE_KEY']
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
    
    async with httpx.AsyncClient() as client:
        # Get recent records
        resp = await client.get(
            f'{url}/rest/v1/api_call_logs', 
            headers=headers, 
            params={'select': '*', 'order': 'timestamp.desc', 'limit': '10'}
        )
        data = resp.json()
        print(f"Records in Supabase: {len(data)}")
        print("\nRecent API calls:")
        for r in data[:5]:
            svc = r.get('service', '?')
            endpoint = r.get('endpoint', '?')
            status = r.get('status', '?')
            time_ms = r.get('response_time_ms', 0)
            print(f"  {svc}: {endpoint} - {status} ({time_ms:.0f}ms)")

asyncio.run(check())
