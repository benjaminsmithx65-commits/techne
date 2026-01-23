"""Test agent status endpoint with real address"""
import asyncio
import httpx

async def main():
    # Test agent status endpoint with YOUR address
    addr = "0xba9d6947c0ad6ea2aaa99507355cf83b4d098058"
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://localhost:8080/api/agent/status/{addr}")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

asyncio.run(main())
