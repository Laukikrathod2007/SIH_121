# Dev tool: describes /story frames from a terminal. For the 3D stage only
# (between the nav/status bar and the transport bar) it prints average
# colours of a 6x4 grid of cells, plus a coarse luminance map.
#   python scripts/story-look.py film-frames/t00007.png ...
import sys
from PIL import Image

RAMP = " .:-=+*#%@"
for f in sys.argv[1:]:
    im = Image.open(f).convert("RGB")
    w, h = im.size
    st = im.crop((0, 88, w, h - 78))
    sw, sh = st.size
    print(f"== {f}")
    for r in range(4):
        row = []
        for c in range(6):
            cell = st.crop((c * sw // 6, r * sh // 4, (c + 1) * sw // 6, (r + 1) * sh // 4)).resize((1, 1)).getpixel((0, 0))
            row.append("%3d,%3d,%3d" % cell)
        print("   " + " | ".join(row))
    g = st.convert("L").resize((72, 16))
    vals = sorted(g.get_flattened_data() if hasattr(g, "get_flattened_data") else g.getdata())
    top = max(10, vals[int(len(vals) * 0.99)])
    px = g.load()
    for y in range(16):
        print("   |" + "".join(RAMP[min(9, int(px[x, y] / top * 9.99))] for x in range(72)) + "|")
