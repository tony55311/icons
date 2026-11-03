"""洋流 keychain: 3 mm, 3 colors (orange base / white / black top 1 mm), corner hanging hole."""
import cv2, numpy as np, trimesh, sys
from functools import reduce
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

W, H = 32.0, 48.0          # body size (mm)
CORNER = 2.5
T_TOTAL, T_TOP = 3.0, 1.0  # total thickness, colored top layer
STRIP_X, STRIP_W = 0.9, 3.8           # date strips (black box + white digits)
PANEL = (9.4, 22.6)                    # white centre panel x-range
CHAR_X = (5.6, 26.4)                   # characters fit into this x-range
DATE = "20261128"
HOLE_D, EAR_R = 4.0, 4.4
EAR_C = (2.6, H + 1.4)

# ---- characters traced from the source ----
UP = 4
im = cv2.imread(sys.argv[1])
im = cv2.resize(im, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
im = cv2.GaussianBlur(im, (0, 0), 2.5)
v = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[..., 2]
m = (v < 95).astype(np.uint8) * 255
m[:, :33 * UP] = 0; m[:, 247 * UP:] = 0
m = cv2.medianBlur(m, 7)
cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE); hier = hier[0]
Hpx = m.shape[0]
def pts(c):
    p = c[:, 0, :].astype(float); p[:, 1] = Hpx - p[:, 1]; return p
polys = []
for i, c in enumerate(cnts):
    if hier[i][3] != -1 or cv2.contourArea(c) < 150 * UP * UP: continue
    holes, j = [], hier[i][2]
    while j != -1:
        if cv2.contourArea(cnts[j]) > 150 * UP * UP: holes.append(pts(cnts[j]))  # tiny pin-holes filled
        j = hier[j][0]
    polys.append(Polygon(pts(c), holes).buffer(0).simplify(1.0))
chars = unary_union(polys)
b = chars.bounds
s = (CHAR_X[1] - CHAR_X[0]) / (b[2] - b[0])
chars = affinity.scale(chars, s, s, origin=(b[0], b[1]))
chars = affinity.translate(chars, CHAR_X[0] - b[0], (H - (b[3] - b[1]) * s) / 2 - b[1])
chars = chars.buffer(0.15).buffer(-0.15)   # smooth jpeg jaggies

# ---- body outline + corner ear ----
body = box(CORNER, CORNER, W - CORNER, H - CORNER).buffer(CORNER, quad_segs=24)
ear = Point(EAR_C).buffer(EAR_R, quad_segs=48)
outline = unary_union([body, ear]).buffer(1.5, quad_segs=24).buffer(-1.5, quad_segs=24)
hole = Point(EAR_C).buffer(HOLE_D / 2, quad_segs=64)
outline = outline.difference(hole)

# ---- date strips (vector font) ----
fp = FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
def text_poly(t, size):
    tp = TextPath((0, 0), t, size=size, prop=fp)
    rings = [Polygon(r) for r in tp.to_polygons() if len(r) > 2]
    return reduce(lambda a, b: a.symmetric_difference(b), rings).buffer(0)
digits = text_poly(DATE, 3.55).buffer(0.08, quad_segs=8)   # embolden -> ~0.6 mm strokes
db = digits.bounds
digits = affinity.translate(digits, -db[0], -db[1])
L, Dh = db[2] - db[0], db[3] - db[1]
PAD = 0.7
box_len = L + 2 * PAD
y_lo, y_hi = 2.6, H - 2.6
gap = (y_hi - y_lo) - 2 * box_len
assert gap > 1.0, gap
black_boxes, white_digits = [], []
for side in ('L', 'R'):
    x0 = STRIP_X if side == 'L' else W - STRIP_X - STRIP_W
    for k in range(2):
        yb = y_lo + k * (box_len + gap)
        bx = box(x0, yb, x0 + STRIP_W, yb + box_len).buffer(-0.5).buffer(0.5)
        if side == 'L':   # reads bottom -> top
            d = affinity.rotate(digits, 90, origin=(0, 0))
            d = affinity.translate(d, x0 + (STRIP_W + Dh) / 2, yb + PAD)
        else:             # reads top -> bottom
            d = affinity.rotate(digits, -90, origin=(0, 0))
            d = affinity.translate(d, x0 + (STRIP_W - Dh) / 2, yb + PAD + L)
        black_boxes.append(bx); white_digits.append(d)
boxes = unary_union(black_boxes); dig = unary_union(white_digits)

# ---- 洋流 from a real font (replaces the traced, jagged version) ----
cjk = FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
def glyph(ch):
    # nonzero winding: fonts overlap stroke contours, so even-odd would punch holes
    tp = TextPath((0, 0), ch, size=10, prop=cjk)
    rings = [r for r in tp.to_polygons() if len(r) > 2]
    sa = [Polygon(r).exterior.is_ccw for r in rings]
    big = max(range(len(rings)), key=lambda i: Polygon(rings[i]).area)
    outer = [Polygon(r).buffer(0) for r, c in zip(rings, sa) if c == sa[big]]
    inner = [Polygon(r).buffer(0) for r, c in zip(rings, sa) if c != sa[big]]
    return unary_union(outer).difference(unary_union(inner)) if inner else unary_union(outer)
CW = CHAR_X[1] - CHAR_X[0]
EMB = 0.12                       # extra weight, closer to the heavy look of the source
gl = []
for ch in '洋流':
    g = glyph(ch); gb = g.bounds
    k = (CW - 2 * EMB) / (gb[2] - gb[0])
    g = affinity.scale(g, k, k, origin=(gb[0], gb[1]))
    gl.append(affinity.translate(g, CHAR_X[0] + EMB - gb[0], -gb[1]))
GAP = 1.6
h0 = gl[0].bounds[3] - gl[0].bounds[1]; h1 = gl[1].bounds[3] - gl[1].bounds[1]
tot = h0 + h1 + GAP + 2 * EMB
y0 = (H - tot) / 2 + EMB
chars = unary_union([affinity.translate(gl[1], 0, y0), affinity.translate(gl[0], 0, y0 + h1 + GAP + 2 * EMB)])
chars = chars.buffer(EMB, join_style=2, mitre_limit=2.0)
chars = chars.buffer(0.2, join_style=2, mitre_limit=2.0).buffer(-0.2, join_style=2, mitre_limit=2.0)  # close slivers <0.6 mm
cb = chars.bounds
print('chars %.1f x %.1f mm, y %.1f-%.1f' % (cb[2] - cb[0], cb[3] - cb[1], cb[1], cb[3]))

# ---- top-layer colour regions ----
panel = box(PANEL[0], -1, PANEL[1], H + 1).intersection(body)
black_top = unary_union([chars, boxes.difference(dig)]).intersection(outline)
white_top = unary_union([panel.difference(chars), dig]).intersection(outline).difference(black_top)
orange_top = outline.difference(black_top).difference(white_top)

def ext(g, h, z):
    gs = [p for p in getattr(g, 'geoms', [g]) if p.area > 1e-4]
    mm = trimesh.util.concatenate([trimesh.creation.extrude_polygon(p, h) for p in gs])
    mm.apply_translation([0, 0, z]); return mm
zb = T_TOTAL - T_TOP
orange = trimesh.boolean.union([ext(outline, zb, 0), ext(orange_top.buffer(0), T_TOP, zb)], engine='manifold')
white = ext(white_top, T_TOP, zb)
black = ext(black_top, T_TOP, zb)
for n, mm in (('orange', orange), ('white', white), ('black', black)):
    print(n, 'watertight', mm.is_watertight, 'bounds', mm.bounds.round(2).tolist())
ob = outline.bounds
print('overall %.1f x %.1f x %.1f mm' % (ob[2] - ob[0], ob[3] - ob[1], T_TOTAL))
print('digit text len %.1f mm, height %.2f mm, gap %.1f' % (L, Dh, gap))
for w in (0.4, 0.5, 0.6):
    for nm, g in (('digits', dig), ('chars', chars)):
        print(f'{nm}: area lost at min stroke {w}: {1 - g.buffer(-w/2).buffer(w/2).area / g.area:.3f}')
orange.export('../yangliu_orange.stl'); white.export('../yangliu_white.stl'); black.export('../yangliu_black.stl')
