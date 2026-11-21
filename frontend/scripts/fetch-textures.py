"""
Downloads the textures used by /story:

  public/story/rock/<formation>_{diff,nor,rough}.jpg
      CC0 rock scans from Poly Haven (polyhaven.com), one per formation in
      the Upper Assam column, for the borehole descent.
  public/story/earth/bluemarble.jpg   NASA Blue Marble NG (Jan 2004), public domain
  public/story/earth/nightlights.jpg  NASA Black Marble 2016, public domain

Run once (needs internet); outputs are committed.
    python scripts/fetch-textures.py
"""
import io
import json
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent / "public" / "story"
H = {"User-Agent": "DrillWise-asset-build"}

# Upper Assam formation -> Poly Haven scan that best matches its lithology.
ROCKS = {
    "alluvium": "rocks_ground_02",       # unconsolidated gravel, sand
    "tipam": "red_sandstone_pavement",   # Tipam: ferruginous sandstone
    "girujan": "rock_boulder_dry",       # Girujan: mottled clay
    "barail": "rock_wall_08",            # Barail: sandstone, shale, coal
    "kopili": "dark_rock",               # Kopili: dark shale (target)
    "sylhet": "marble_cliff_02",         # Sylhet: limestone
}

EARTH = {
    "bluemarble": "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/bmng/bmng-base/january/world.200401.3x5400x2700.jpg",
    "nightlights": "https://eoimages.gsfc.nasa.gov/images/imagerecords/144000/144898/BlackMarble_2016_01deg.jpg",
}


def get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=120).read()


def main() -> None:
    (ROOT / "rock").mkdir(parents=True, exist_ok=True)
    for name, asset in ROCKS.items():
        files = json.loads(get(f"https://api.polyhaven.com/files/{asset}"))
        for key, suffix in (("Diffuse", "diff"), ("nor_gl", "nor"), ("Rough", "rough")):
            url = files[key]["1k"]["jpg"]["url"]
            im = Image.open(io.BytesIO(get(url))).convert("RGB")
            im.save(ROOT / "rock" / f"{name}_{suffix}.jpg", quality=84, optimize=True)
        print(f"rock  {name:9s} <- {asset}")

    (ROOT / "earth").mkdir(parents=True, exist_ok=True)
    for name, url in EARTH.items():
        try:
            im = Image.open(io.BytesIO(get(url))).convert("RGB")
        except Exception as exc:
            print(f"earth {name}: FAILED {exc}")
            continue
        if im.size[0] > 5400:
            im = im.resize((5400, 2700), Image.LANCZOS)
        im.save(ROOT / "earth" / f"{name}.jpg", quality=86, optimize=True, progressive=True)
        print(f"earth {name}: {im.size}")


if __name__ == "__main__":
    main()
