"""Check what timestamps WAQI API returns and what gets stored in DB."""
import asyncio
from app.db.session import SessionLocal
from app.services.aqi_service import _fetch_from_waqi, _cache_readings, _get_cached_readings
from sqlalchemy import text

async def test():
    # 1. Fetch from WAQI and print raw record details
    result = await _fetch_from_waqi("Indore")
    records, waqi_aqi = result
    print("--- WAQI Records (raw) ---")
    for r in records:
        print(f"  {r['pollutant_id']:10s} avg={r['avg_value']}  last_update={r.get('last_update', 'NONE')}")

    # 2. Cache them
    db = SessionLocal()
    _cache_readings(db, "Indore", records)

    # 3. Check what's actually in DB now
    print("\n--- All DB rows (last 15) ---")
    rows = db.execute(text("SELECT id, pollutant_id, pollutant_avg, recorded_at, fetched_at FROM aqi_readings ORDER BY id DESC LIMIT 15"))
    for row in rows:
        print(f"  id={row[0]:4d}  {row[1]:10s}  avg={row[2]}  recorded={row[3]}  fetched={row[4]}")

    # 4. Check cached readings (24h filter)
    print("\n--- Cached readings (24h filter) ---")
    cached = _get_cached_readings(db, "Indore")
    print(f"  Found: {len(cached)} readings")
    for r in cached:
        print(f"  {r.pollutant_id:10s} = {r.pollutant_avg}  recorded={r.recorded_at}")

    db.close()

asyncio.run(test())
