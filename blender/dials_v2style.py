# Dial faces in the game's flat style: big ticks, few numbers, no fine print. One set per colour scheme.
# Writes v2_<dial>_<scheme>.png (dial = tacho, speedo, fuel, temp) and v2_incl.png (inclinometer face).
# Needle sweeps are the same as dials.py: big dials 270 degrees, small ones 90, 0 = straight up.
# Run with any Python that has cairosvg (pip install cairosvg):  python dials_v2style.py <assets folder>
import math
import os
import sys

import cairosvg

OUT = sys.argv[1]
FONT = "DejaVu Sans, Verdana, sans-serif"
S = 512
SCHEMES = {
    "black": dict(face="#2a2a30", ink="#f3ead8", red="#ef6a4c"),      # most cars
    "cream": dict(face="#efe4c8", ink="#2c2a28", red="#c8442e"),      # 1940s-50s
    "olive": dict(face="#2f3326", ink="#e9e2b8", red="#e07a3a"),      # military
    "eighties": dict(face="#1e1f24", ink="#f6a04a", red="#ff5a3c"),   # 1980s-90s
}


def at(deg, r):
    a = math.radians(deg)
    return 256 + math.sin(a) * r, 256 - math.cos(a) * r


def line(deg, r_out, length, width, color):
    x0, y0 = at(deg, r_out - length)
    x1, y1 = at(deg, r_out)
    return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round"/>')


def arc(d0, d1, r, width, color):
    x0, y0 = at(d0, r)
    x1, y1 = at(d1, r)
    return (f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 {1 if abs(d1 - d0) > 180 else 0} 1 {x1:.1f},{y1:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')


def text(s, x, y, size, color):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-weight="bold" font-size="{size}" '
            f'fill="{color}" text-anchor="middle" dominant-baseline="central">{s}</text>')


def save(name, body, face):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}">'
           f'<rect width="{S}" height="{S}" fill="{face}"/>{body}</svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(OUT, name), output_width=S, output_height=S)


def big(name, c, top, step, every, red_from=None, div=1):
    deg = lambda v: -135 + 270 * v / top
    s = arc(deg(red_from), deg(top), 200, 30, c["red"]) if red_from is not None else ""
    v = 0
    while v <= top:
        major = v % every == 0
        s += line(deg(v), 225, 46 if major else 24, 14 if major else 9, c["ink"])
        if major:
            x, y = at(deg(v), 140)
            s += text(str(v // div), x, y, 64 if div > 1 else 54, c["ink"])
        v += step
    save(name, s, c["face"])


def small(name, c, left, right, low_red=False):
    deg = lambda f: -45 + 90 * f
    s = arc(deg(0), deg(0.2), 200, 34, c["red"]) if low_red else ""
    for i in range(5):
        s += line(deg(i / 4), 230, 60 if i % 2 == 0 else 36, 18, c["ink"])
    xl, yl = at(-52, 120)
    xr, yr = at(52, 120)
    s += text(left, xl - 10, yl + 40, 76, c["ink"]) + text(right, xr + 10, yr + 40, 76, c["ink"])
    save(name, s, c["face"])


for scheme, c in SCHEMES.items():
    big(f"v2_tacho_{scheme}.png", c, 6000, 500, 1000, red_from=4500, div=1000)
    big(f"v2_speedo_{scheme}.png", c, 140, 10, 20)
    small(f"v2_fuel_{scheme}.png", c, "E", "F", low_red=True)
    small(f"v2_temp_{scheme}.png", c, "C", "H")

# Inclinometer face (decor: a car silhouette level on a tilt scale).
c = SCHEMES["eighties"]
s = ""
for d in range(-40, 41, 10):
    s += line(d, 236, 40 if d % 20 == 0 else 22, 12, c["red"] if abs(d) >= 30 else c["ink"])
s += ('<g fill="#f6a04a"><path d="M120,300 L120,262 L150,250 L200,248 L216,200 L330,198 L350,250 L392,256 L392,300 Z"/>'
      '<circle cx="170" cy="306" r="30"/><circle cx="342" cy="306" r="30"/></g>')
save("v2_incl.png", s, c["face"])
print("dial faces written to", OUT)
