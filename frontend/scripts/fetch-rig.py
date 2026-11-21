"""
Downloads the drilling-rig parts used by /story from the CC0 "Offshore Oil
Rig and Platform" pack on 3dassets.dev (CC0 1.0, no attribution required).
Only the land-rig equipment is used: derrick, crown block, travelling
block, drawworks, rotary table, mud pumps, mud tanks, shale shaker, BOP,
pipe rack, generators, floodlights, flare.

Outputs public/story/rig/*.glb and manifest.json. Run once (needs
internet); the outputs are committed.   python scripts/fetch-rig.py
"""
import json
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "public" / "story" / "rig"
OUT.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "DrillWise-asset-build"}

# local file name -> substring of the asset slug
PAD_WANT = {
    # rig-site dressing (other CC0 packs on 3dassets.dev)
    "fuel-tanker": "long-haul-trucking-and-truck-stop-fuel-tanker-trailer",
    "flatbed-crane": "car-park-and-road-vehicle-fleet-crane-flatbed-truck",
    "site-office": "ore-processing-and-haulage-plant-site-office",
    "container": "fps-survival-forest-outpost-shipping-container-9486",
    "fence-bay": "fps-survival-forest-outpost-chain-link-bay",
    "light-tower": "endurance-and-gt-paddock-light-tower",
    "water-tank": "motorway-services-and-truck-park-water-tank",
}

WANT = {
    "derrick-section": "derrick-section",
    "crown-block": "derrick-crown-block",
    "travelling-block": "travelling-block",
    "drawworks": "drawworks",
    "rotary-table": "drill-floor-rotary-table",
    "mud-pump": "mud-pump",
    "mud-tank": "mud-tank-73",
    "mud-tank-agitated": "mud-tank-agitated",
    "shale-shaker": "shale-shaker",
    "bop-stack": "blowout-preventer",
    "pipe-rack": "setback-pipe-rack",
    "pipe-stands": "drill-pipe-stand",
    "generator": "generator-set",
    "diesel-tank": "diesel-fuel-tank",
    "floodlight-mast": "deck-floodlight",
    "flare-tip": "flare-boom-tip",
    "cement-unit": "cement-unit",
    "bunk-cabin": "bunk-cabin",
}


def get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read()


def main() -> None:
    data = json.loads(get("https://3dassets.dev/api/v1/assets?q=offshore%20oil%20rig%20and%20platform&limit=100"))
    if isinstance(data, dict):
        data = data.get("assets") or data.get("items") or data.get("data") or data.get("results") or []
    items = [a for a in data if "offshore-oil-rig" in a["slug"]]
    manifest = {}
    for name, key in WANT.items():
        a = next((x for x in items if key in x["slug"]), None)
        if not a:
            print(f"missing {name}")
            continue
        url = a.get("cdnUrl") or a.get("downloadUrl")
        blob = get(url)
        (OUT / f"{name}.glb").write_bytes(blob)
        lic = (a.get("license") or {}).get("slug")
        manifest[name] = {"slug": a["slug"], "title": a.get("title"), "license": lic, "bytes": len(blob)}
        print(f"{name:20s} {len(blob) / 1024:7.0f} KB  {a.get('title')}  [{lic}]")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))


def pad() -> None:
    manifest = json.loads((OUT / "manifest.json").read_text())
    for name, slug in PAD_WANT.items():
        q = slug.replace("-", "%20")
        data = json.loads(get(f"https://3dassets.dev/api/v1/assets?q={q}&limit=10"))
        items = data.get("data", data) if isinstance(data, dict) else data
        a = next((x for x in items if x["slug"].startswith(slug)), None)
        if not a:
            print(f"missing {name}")
            continue
        blob = get(a.get("cdnUrl") or a.get("downloadUrl"))
        (OUT / f"{name}.glb").write_bytes(blob)
        lic = (a.get("license") or {}).get("slug")
        manifest[name] = {"slug": a["slug"], "title": a.get("title"), "license": lic, "bytes": len(blob)}
        print(f"{name:16s} {len(blob) / 1024:7.0f} KB  {a.get('title')}  [{lic}]")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    import sys

    if "--pad" in sys.argv:
        pad()
    else:
        main()
