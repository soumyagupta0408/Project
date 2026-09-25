import httpx, json
from app.core.config import get_settings

s = get_settings()
url = (
    f"https://api.data.gov.in/resource/{s.DATA_GOV_RESOURCE_ID}"
    f"?api-key={s.DATA_GOV_API_KEY}&format=json&limit=2000"
)
r = httpx.get(url, timeout=20)
records = r.json().get("records", [])
indore = [x for x in records if str(x.get("city","")).strip().lower() == "indore"]

print(f"Total records: {len(records)}")
print(f"Indore records: {len(indore)}")
print("---")
for rec in indore[:10]:
    print(json.dumps(rec, indent=2))