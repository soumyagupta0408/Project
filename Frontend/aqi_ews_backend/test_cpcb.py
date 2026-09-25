import asyncio
import httpx
import sys
import os

# Add project root to path so app.core.config is importable
sys.path.insert(0, os.getcwd())

from app.core.config import get_settings

settings = get_settings()

print("=== CONFIG CHECK ===")
print(f"RESOURCE_ID : {settings.DATA_GOV_RESOURCE_ID}")
print(f"API_KEY     : {settings.DATA_GOV_API_KEY[:8]}..." if settings.DATA_GOV_API_KEY else "API_KEY: MISSING!")

url = (
    f"https://api.data.gov.in/resource/{settings.DATA_GOV_RESOURCE_ID}"
    f"?api-key={settings.DATA_GOV_API_KEY}&format=json&limit=10"
)

async def test():
    print("\n=== CPCB API TEST ===")
    print(f"URL: {url[:100]}...")
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url)
            print(f"Status : {r.status_code}")
            data = r.json()
            records = data.get("records", [])
            print(f"Total records returned: {len(records)}")
            if records:
                print(f"First record: {records[0]}")
            else:
                print("No records in response!")
                print(f"Full response: {r.text[:500]}")

            # Check specifically for Indore
            indore = [r for r in records if "indore" in str(r.get("city","")).lower()]
            print(f"\nIndore records: {len(indore)}")
            if indore:
                print(f"Sample Indore record: {indore[0]}")
    except Exception as e:
        print(f"ERROR: {e}")

asyncio.run(test())
