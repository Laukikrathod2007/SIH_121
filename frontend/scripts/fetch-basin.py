"""
Builds the real-world basin assets for the /story page:

  public/story/basin-height.png   16-bit greyscale elevation (metres), from
                                  AWS Terrain Tiles (Terrarium; Mapzen
                                  sources incl. SRTM). Open data.
  public/story/basin-sat.jpg      Sentinel-2 cloudless 2016 imagery by EOX
                                  IT Services GmbH, CC BY 4.0.
  public/story/basin.json         bounds, size, elevation range, and each
                                  demo well's position in the image.

Run once (needs internet); the outputs are committed so the page works
offline:  python scripts/fetch-basin.py
"""
from __future__ import annotations

import io
import json
import math
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "public" / "story"
OUT.mkdir(parents=True, exist_ok=True)

# Demo wells (lat, lon) -- same as frontend/src/data/fallbackWells.ts.
WELLS = {
    "NHK-001": (27.149183, 95.292326),
    "NHK-002": (27.260229, 95.291487),
    "NHK-003": (27.152943, 95.406274),
    "MRN-004": (27.037065, 94.981018),
    "MRN-005": (27.088685, 94.984708),
    "MRN-006": (27.078776, 95.047567),
    "BGJ-007": (27.486087, 95.393323),
    "BGJ-008": (27.600434, 95.312772),
    "BGJ-009": (27.607952, 95.283917),
    "HGJ-010": (27.277859, 94.738453),
    "HGJ-011": (27.202888, 94.750397),
    "HGJ-012": (27.274571, 94.723159),
}
ACTIVE = "NHK-002"

# Area: all wells plus a margin, with the Naga-Patkai foothills to the SE.
LAT_MIN, LAT_MAX = 26.80, 27.78
LON_MIN, LON_MAX = 94.55, 95.75

DEM_Z = 11  # ~ 70 m/px at this latitude
SAT_Z = 12  # ~ 34 m/px
DETAIL_Z = 14  # ~ 8.5 m/px (Sentinel-2 native is 10 m)
DETAIL_KM = 10.0  # side of the square detail patch around the active well

UA = {"User-Agent": "DrillWise-SIH26121-asset-build/1.0"}


def tile_xy(lat: float, lon: float, z: int) -> tuple[float, float]:
    n = 2**z
    x = (lon + 180) / 360 * n
    lr = math.radians(lat)
    y = (1 - math.asinh(math.tan(lr)) / math.pi) / 2 * n
    return x, y


def fetch(url: str, tries: int = 4) -> bytes:
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except Exception as exc:  # retry transient failures, then give up loudly
            if i == tries - 1:
                raise RuntimeError(f"failed: {url}: {exc}")
            time.sleep(1.5 * (i + 1))
    raise AssertionError


def mosaic_bbox(z: int, lat_min: float, lat_max: float, lon_min: float, lon_max: float, url_fmt: str):
    """Tiles covering an arbitrary bbox, cropped to it exactly."""
    x0f, y0f = tile_xy(lat_max, lon_min, z)
    x1f, y1f = tile_xy(lat_min, lon_max, z)
    xs = range(int(x0f), int(x1f) + 1)
    ys = range(int(y0f), int(y1f) + 1)
    img = Image.new("RGB", (256 * len(xs), 256 * len(ys)))
    for j, ty in enumerate(ys):
        for i, tx in enumerate(xs):
            img.paste(Image.open(io.BytesIO(fetch(url_fmt.format(z=z, x=tx, y=ty)))).convert("RGB"), (256 * i, 256 * j))
    box = ((x0f - xs.start) * 256, (y0f - ys.start) * 256, (x1f - xs.start) * 256, (y1f - ys.start) * 256)
    return img.crop(tuple(round(b) for b in box)), (lat_min, lat_max, lon_min, lon_max)


def mosaic(z: int, url_fmt: str, mode: str) -> tuple[Image.Image, float, float]:
    """Download the tiles covering the bbox; return the mosaic and the
    fractional tile coords of its top-left corner."""
    x0f, y0f = tile_xy(LAT_MAX, LON_MIN, z)
    x1f, y1f = tile_xy(LAT_MIN, LON_MAX, z)
    xs = range(int(x0f), int(x1f) + 1)
    ys = range(int(y0f), int(y1f) + 1)
    img = Image.new(mode, (256 * len(xs), 256 * len(ys)))
    total = len(xs) * len(ys)
    k = 0
    for j, ty in enumerate(ys):
        for i, tx in enumerate(xs):
            k += 1
            data = fetch(url_fmt.format(z=z, x=tx, y=ty))
            img.paste(Image.open(io.BytesIO(data)).convert(mode), (256 * i, 256 * j))
            print(f"  z{z} {k}/{total}", end="\r")
    print()
    # crop to the exact bbox
    left = (x0f - xs.start) * 256
    top = (y0f - ys.start) * 256
    right = (x1f - xs.start) * 256
    bottom = (y1f - ys.start) * 256
    return img.crop((round(left), round(top), round(right), round(bottom))), x0f, y0f


def main() -> None:
    print("Elevation (AWS Terrain Tiles, Terrarium)...")
    dem_rgb, dx0, dy0 = mosaic(DEM_Z, "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png", "RGB")
    a = np.asarray(dem_rgb).astype(np.float64)
    elev = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    elev = np.clip(elev, 0, None)
    lo, hi = float(np.percentile(elev, 0.5)), float(elev.max())
    norm = np.clip((elev - lo) / (hi - lo), 0, 1)
    # 1024 px wide (~115 m/px) is plenty for the mesh. Stored as 16-bit
    # packed into R (high byte) and G (low byte) of an 8-bit RGB PNG,
    # because browsers decode PNGs to 8 bits per channel.
    q = Image.fromarray((norm * 65535).astype(np.float32), mode="F")
    q = q.resize((1024, round(1024 * q.size[1] / q.size[0])), Image.BILINEAR)
    v = np.clip(np.asarray(q), 0, 65535).astype(np.uint16)
    packed = np.stack([(v >> 8).astype(np.uint8), (v & 255).astype(np.uint8), np.zeros_like(v, dtype=np.uint8)], axis=-1)
    Image.fromarray(packed, "RGB").save(OUT / "basin-height.png", optimize=True)
    print(f"  {q.size[0]}x{q.size[1]}  elevation {lo:.0f}..{hi:.0f} m")

    print("Imagery (Sentinel-2 cloudless 2016, EOX)...")
    sat, sx0, sy0 = mosaic(SAT_Z, "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg", "RGB")
    sat = sat.resize((4096, round(4096 * sat.size[1] / sat.size[0])), Image.LANCZOS)
    sat.save(OUT / "basin-sat.jpg", quality=82, optimize=True, progressive=True)
    print(f"  saved {sat.size[0]}x{sat.size[1]}")

    # Detail patch around the active well (Sentinel-2's native ~10 m), for
    # the close shots at the rig.
    print("Detail imagery around the active well...")
    alat, alon = WELLS[ACTIVE]
    half_lat = DETAIL_KM / 2 / 110.57
    half_lon = DETAIL_KM / 2 / (111.32 * math.cos(math.radians(alat)))
    det, d_bbox = mosaic_bbox(DETAIL_Z, alat - half_lat, alat + half_lat, alon - half_lon, alon + half_lon,
                              "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg")
    det = det.resize((2048, 2048), Image.LANCZOS)
    det.save(OUT / "basin-detail.jpg", quality=84, optimize=True, progressive=True)
    print(f"  saved {det.size[0]}x{det.size[1]}")

    # Ground size of the area (km), and each well's position in [0,1] uv
    # (Web Mercator, matching both images).
    x0, y0 = tile_xy(LAT_MAX, LON_MIN, 0)
    x1, y1 = tile_xy(LAT_MIN, LON_MAX, 0)
    mid_lat = math.radians((LAT_MIN + LAT_MAX) / 2)
    width_km = (LON_MAX - LON_MIN) * 111.32 * math.cos(mid_lat)
    height_km = (LAT_MAX - LAT_MIN) * 110.57
    wells = {}
    for wid, (lat, lon) in WELLS.items():
        wx, wy = tile_xy(lat, lon, 0)
        wells[wid] = {"u": (wx - x0) / (x1 - x0), "v": (wy - y0) / (y1 - y0), "lat": lat, "lon": lon}
    meta = {
        "bbox": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
        "width_km": round(width_km, 3),
        "height_km": round(height_km, 3),
        "elev_min_m": round(lo, 1),
        "elev_max_m": round(hi, 1),
        "active": ACTIVE,
        "detail_km": DETAIL_KM,
        "wells": wells,
        "credits": {
            "imagery": "Sentinel-2 cloudless - https://s2maps.eu by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2016 & 2017), CC BY 4.0",
            "elevation": "AWS Terrain Tiles (Mapzen; sources incl. SRTM, NASA/USGS)",
        },
    }
    (OUT / "basin.json").write_text(json.dumps(meta, indent=2))
    print(f"  area {width_km:.1f} x {height_km:.1f} km -> {OUT}")


# Wide surround: the real horizon around the basin, from the Eastern
# Himalaya (Arunachal, ~5-6 km peaks, 100-250 km north) to the Naga-Patkai
# hills (south-east). Low resolution: it's only ever seen in the distance.
WIDE = {"lat_min": 25.6, "lat_max": 29.2, "lon_min": 92.9, "lon_max": 97.4}
WIDE_Z = 8  # ~550 m/px elevation; imagery at the same zoom + 1


def wide() -> None:
    print("Wide surround elevation...")
    img, _ = mosaic_bbox(WIDE_Z, WIDE["lat_min"], WIDE["lat_max"], WIDE["lon_min"], WIDE["lon_max"],
                         "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png")
    a = np.asarray(img).astype(np.float64)
    elev = np.clip(a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768, 0, None)
    hi = float(elev.max())
    q = Image.fromarray((elev / hi * 65535).astype(np.float32), mode="F").resize((512, 512), Image.BILINEAR)
    v = np.clip(np.asarray(q), 0, 65535).astype(np.uint16)
    packed = np.stack([(v >> 8).astype(np.uint8), (v & 255).astype(np.uint8), np.zeros_like(v, dtype=np.uint8)], axis=-1)
    Image.fromarray(packed, "RGB").save(OUT / "wide-height.png", optimize=True)
    print(f"  max elevation {hi:.0f} m")
    print("Wide surround imagery...")
    sat, _ = mosaic_bbox(WIDE_Z + 1, WIDE["lat_min"], WIDE["lat_max"], WIDE["lon_min"], WIDE["lon_max"],
                         "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg")
    sat.resize((2048, 2048), Image.LANCZOS).save(OUT / "wide-sat.jpg", quality=82, optimize=True, progressive=True)
    # Placement relative to the active well, km (equirectangular approx.).
    alat, alon = WELLS[ACTIVE]
    kx = 111.32 * math.cos(math.radians(alat))
    ky = 110.57
    x0w, y0w = tile_xy(WIDE["lat_max"], WIDE["lon_min"], 0)
    x1w, y1w = tile_xy(WIDE["lat_min"], WIDE["lon_max"], 0)
    ax, ay = tile_xy(alat, alon, 0)
    meta = json.loads((OUT / "basin.json").read_text())
    meta["wide"] = {
        "width_km": round((WIDE["lon_max"] - WIDE["lon_min"]) * kx, 2),
        "height_km": round((WIDE["lat_max"] - WIDE["lat_min"]) * ky, 2),
        # active well's position in the wide images, uv (Web Mercator)
        "u": (ax - x0w) / (x1w - x0w),
        "v": (ay - y0w) / (y1w - y0w),
        "elev_max_m": round(hi, 1),
    }
    (OUT / "basin.json").write_text(json.dumps(meta, indent=2))
    print(f"  wide {meta['wide']['width_km']:.0f} x {meta['wide']['height_km']:.0f} km")


if __name__ == "__main__":
    import sys

    if "--wide-only" in sys.argv:
        wide()
    else:
        main()
        wide()
