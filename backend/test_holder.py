import asyncio
import os

# Load from env - do NOT hardcode API keys
if not os.getenv("MORALIS_API_KEY"):
    print("⚠️ MORALIS_API_KEY not set - using dotenv")
    from dotenv import load_dotenv
    load_dotenv()

from data_sources.holder_analysis import holder_analyzer

async def test_holder():
    # Test ZORA token (non-whitelisted token from the pool)
    token = "0x1111111111166b7fe7bd91427724b487980afc69"
    result = await holder_analyzer.get_holder_analysis(token, "base")
    print(f"Source: {result.get('source')}")
    print(f"Top 10%: {result.get('top_10_percent')}")
    print(f"Holder Count: {result.get('holder_count')}")
    print(f"Concentration Risk: {result.get('concentration_risk')}")

asyncio.run(test_holder())
