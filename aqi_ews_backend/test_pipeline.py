"""Quick test of WAQI fetch -> DB cache -> DB read pipeline."""
import asyncio
from app.db.session import SessionLocal
from app.services.aqi_service import _fetch_from_waqi, _cache_readings, _get_cached_readings

async def test():
    # 1. Test WAQI fetch
    print("--- Step 1: WAQI Fetch ---")
    result = await _fetch_from_waqi("Indore")
    if result is None:
        print("WAQI FETCH FAILED - returned None")
        return
    records, waqi_aqi = result
    print(f"WAQI fetch OK: aqi={waqi_aqi}, records={len(records)}")
    for r in records:
        pid = r["pollutant_id"]
        avg = r["avg_value"]
        print(f"  {pid:10s} = {avg}")

    # 2. Test DB caching
    print("\n--- Step 2: DB Cache Write ---")
    db = SessionLocal()
    try:
        _cache_readings(db, "Indore", records)
        print("DB cache write: OK")
    except Exception as e:
        print(f"DB cache write FAILED: {e}")

    # 3. Test DB read
    print("\n--- Step 3: DB Cache Read ---")
    try:
        cached = _get_cached_readings(db, "Indore")
        print(f"DB cache read: {len(cached)} readings")
        for r in cached[:8]:
            print(f"  {r.pollutant_id:10s} = {r.pollutant_avg}  (recorded: {r.recorded_at})")
    except Exception as e:
        print(f"DB cache read FAILED: {e}")
    finally:
        db.close()

asyncio.run(test())
