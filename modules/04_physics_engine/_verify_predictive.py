import json
import urllib.request
from dotenv import dotenv_values

KEY = dotenv_values(".env")["NWIS_API_KEY"]
BASE = "http://localhost:8003/api/v3"


def call(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-API-Key", KEY)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


# Pull recent historian records (accumulated while LOST_CIRCULATION active)
hist = call("GET", "/physics/historian?limit=40")
print("historian records:", len(hist))

well_id = None
last_eval = None
for rec in hist:
    last_eval = call("POST", "/predictive/evaluate", {"telemetry": rec})
    well_id = last_eval["well_id"]

print("\n=== final evaluate result (hazards) ===")
for name, h in last_eval["hazards"].items():
    print(f"  {name}: score={h['score']} state={h['state']} anomaly={h['contributors'].get('anomaly_score')}")

print("\nwell_id:", well_id, "md:", last_eval["md"])
print("alerts in last evaluate response:", len(last_eval["alerts"]))
for a in last_eval["alerts"]:
    print("  -", a["severity"], a["hazard_type"], "|", a["headline"], "| status:", a["status"])

print("\n=== GET /predictive/alerts/{well_id} ===")
alerts = call("GET", f"/predictive/alerts/{well_id}")
print("total alerts:", len(alerts))
for a in alerts:
    print(json.dumps(a, indent=2))
