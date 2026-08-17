"""Debug why DB cache write appears to succeed but data doesn't persist."""
import asyncio
from datetime import datetime, timezone, timedelta
from app.db.session import SessionLocal, engine
from app.services.aqi_service import _fetch_from_waqi, _parse_float
from app.models.aqi_reading import AQIReading
from sqlalchemy import text

async def test():
    # 1. Fetch data
    result = await _fetch_from_waqi("Indore")
    records, waqi_aqi = result
    print(f"Got {len(records)} records from WAQI (aqi={waqi_aqi})")

    db = SessionLocal()

    # 2. Check table structure
    print("\n--- Table structure ---")
    try:
        cols = db.execute(text("DESCRIBE aqi_readings"))
        for row in cols:
            print(f"  {row[0]:20s} {row[1]:30s} {row[2]:5s} {row[3]:5s}")
    except Exception as e:
        print(f"DESCRIBE failed: {e}")

    # 3. Try inserting ONE record manually with full error reporting
    print("\n--- Manual insert test ---")
    rec = records[0]
    now = datetime.now(timezone.utc)
    try:
        reading = AQIReading(
            city="Indore",
            station=str(rec.get("station", "Unknown")).strip(),
            pollutant_id=str(rec.get("pollutant_id", "")).strip().upper(),
            pollutant_min=_parse_float(rec.get("min_value")),
            pollutant_max=_parse_float(rec.get("max_value")),
            pollutant_avg=_parse_float(rec.get("avg_value")),
            unit=str(rec.get("unit", "ug/m3")).strip() or "ug/m3",
            recorded_at=now,
            fetched_at=now,
        )
        print(f"  ORM object: {reading}")
        print(f"  city={reading.city}, station={reading.station}")
        print(f"  pollutant_id={reading.pollutant_id}, avg={reading.pollutant_avg}")
        print(f"  recorded_at={reading.recorded_at}, fetched_at={reading.fetched_at}")

        db.add(reading)
        db.commit()
        print("  INSERT + COMMIT: OK")
    except Exception as e:
        db.rollback()
        print(f"  INSERT FAILED: {type(e).__name__}: {e}")

    # 4. Check if it's actually in the DB
    print("\n--- Verify with raw SQL ---")
    try:
        result = db.execute(text("SELECT COUNT(*) FROM aqi_readings"))
        count = result.scalar()
        print(f"  Total rows in aqi_readings: {count}")

        result = db.execute(text("SELECT id, city, pollutant_id, pollutant_avg, recorded_at FROM aqi_readings ORDER BY id DESC LIMIT 5"))
        for row in result:
            print(f"  id={row[0]} city={row[1]} poll={row[2]} avg={row[3]} at={row[4]}")
    except Exception as e:
        print(f"  SELECT FAILED: {type(e).__name__}: {e}")

    db.close()

asyncio.run(test())
