"""SOON 順 keychain v2: corner hanging hole + white outline rim."""
import cv2, numpy as np, trimesh, sys
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely import affinity

TARGET = 50.0    # overall max size (mm), incl. ear
T_BASE, T_TOP = 2.0, 2.0
MARGIN = 2.8     # orange border around letters
SMOOTH = 5.0     # round off concave notches of the outline
RIM_IN, RIM_W = 0.7, 0.85   # white rim: inset from edge, width (>=2 lines @0.4 nozzle)
HOLE_D = 4.5
EAR_R = 5.2
CLEAR = 2.2      # min distance hole edge -> letters

UP = 4
im = cv2.imread(sys.argv[1])
im = cv2.resize(im, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
im = cv2.GaussianBlur(im, (0, 0), 3)
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
m = ((hsv[..., 1] < 70) & (hsv[..., 2] > 190)).astype(np.uint8) * 255
m = cv2.medianBlur(m, 9)
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
hier = hier[0]; H = m.shape[0]
def pts(c):
    p = c[:, 0, :].astype(float); p[:, 1] = H - p[:, 1]; return p
polys = []
for i, c in enumerate(cnts):
    if hier[i][3] != -1 or cv2.contourArea(c) < 800 * UP * UP / 4: continue
    holes, j = [], hier[i][2]
    while j != -1:
        if cv2.contourArea(cnts[j]) > 60 * UP * UP / 4: holes.append(pts(cnts[j]))
        j = hier[j][0]
    polys.append(Polygon(pts(c), holes).buffer(0).simplify(1.0))
text0 = unary_union(polys)

def make(s):
    tx = affinity.scale(text0, s, s, origin=(0, 0))
    body = tx.buffer(MARGIN, join_style=1, quad_segs=24)
    body = Polygon(max(getattr(body, 'geoms', [body]), key=lambda g: g.area).exterior)
    body = body.buffer(SMOOTH, quad_segs=24).buffer(-SMOOTH, quad_segs=24)
    body = body.buffer(-1.5, quad_segs=24).buffer(1.5, quad_segs=24)
    # hole at top-left corner: slide outward along the diagonal until clear of letters
    minx, miny, maxx, maxy = tx.bounds
    k = 0.0
    while True:
        hc = Point(minx + 1.0 - k, maxy - 1.0 + k)
        if hc.distance(tx) >= HOLE_D / 2 + CLEAR: break
        k += 0.1
    ear = hc.buffer(EAR_R, quad_segs=48)
    outer = unary_union([body, ear]).buffer(2.5, quad_segs=24).buffer(-2.5, quad_segs=24)
    outer = Polygon(outer.exterior)
    return tx, outer, hc
tb = text0.bounds; s = TARGET / max(tb[2]-tb[0], tb[3]-tb[1])
for _ in range(8):
    tx, outer, hc = make(s)
    b = outer.bounds; s *= TARGET / max(b[2] - b[0], b[3] - b[1])
tx, outer, hc = make(s)
hole = hc.buffer(HOLE_D / 2, quad_segs=64)
base = outer.difference(hole)
rim = outer.buffer(-RIM_IN, quad_segs=24).difference(outer.buffer(-RIM_IN - RIM_W, quad_segs=24))
rim = rim.difference(hole.buffer(0.8))
top = unary_union([tx, rim])
b = outer.bounds
base, top = (affinity.translate(g, -b[0], -b[1]) for g in (base, top))
print('size %.1f x %.1f mm' % (b[2] - b[0], b[3] - b[1]))
print('rim->text gap %.2f mm' % rim.distance(tx), ' hole->text %.2f mm' % hole.distance(tx))

def ext(g, h, z):
    mm = trimesh.util.concatenate([trimesh.creation.extrude_polygon(p, h) for p in getattr(g, 'geoms', [g])])
    mm.apply_translation([0, 0, z]); return mm
mb, mt = ext(base, T_BASE, 0), ext(top, T_TOP, T_BASE)
print('watertight', mb.is_watertight, mt.is_watertight)
mb.export('../SOON_keychain_v2_base_orange.stl')
mt.export('../SOON_keychain_v2_top_white.stl')
