# Dev tool: summarises film frames from a terminal. For each frame prints
# mean/percentile luminance, dominant hue, and a coarse ASCII map with an
# auto-exposed ramp (so dark, moody frames still show their composition).
#   python scripts/film-look.py film-frames/*.png
import sys
import colorsys
from PIL import Image

RAMP = " .:-=+*#%@"
for f in sys.argv[1:]:
    im = Image.open(f).convert("RGB")
    small = im.resize((160, 90))
    px = list(small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata())
    lum = sorted(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in px)
    p50, p95, p99 = lum[len(lum) // 2], lum[int(len(lum) * 0.95)], lum[int(len(lum) * 0.99)]
    bright = [(r, g, b) for r, g, b in px if 0.2126 * r + 0.7152 * g + 0.0722 * b > p50]
    ar = sum(p[0] for p in bright) / max(1, len(bright))
    ag = sum(p[1] for p in bright) / max(1, len(bright))
    ab = sum(p[2] for p in bright) / max(1, len(bright))
    h, s, v = colorsys.rgb_to_hsv(ar / 255, ag / 255, ab / 255)
    print(f"== {f}  mean={sum(lum)/len(lum):.1f} p50={p50:.0f} p95={p95:.0f} p99={p99:.0f}  tint=rgb({ar:.0f},{ag:.0f},{ab:.0f}) hue={h*360:.0f} sat={s:.2f}")
    m = im.convert("L").resize((64, 20))
    mp = m.load()
    top = max(8.0, p99)
    for y in range(20):
        print("|" + "".join(RAMP[min(9, int(mp[x, y] / top * 9.99))] for x in range(64)) + "|")
