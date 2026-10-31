import cv2, numpy as np, trimesh
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
import sys

TARGET = 50.0      # overall max size (mm), incl. tab
T_BASE = 2.0
T_TEXT = 2.0
MARGIN = 2.2       # orange border around letters (mm)
HOLE_D = 4.5       # keyring hole diameter (mm)
TAB_R = 4.6        # tab outer radius (mm)

im = cv2.imread(sys.argv[1])
UP = 4
im = cv2.resize(im, None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
im = cv2.GaussianBlur(im, (0, 0), 3)
hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
m = ((hsv[..., 1] < 75) & (hsv[..., 2] > 185)).astype(np.uint8) * 255
m = cv2.medianBlur(m, 9)
m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
cv2.imwrite('mask_up.png', m)

cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
hier = hier[0]
polys = []
H = m.shape[0]
def topts(c):
    p = c[:, 0, :].astype(float); p[:, 1] = H - p[:, 1]; return p
for i, c in enumerate(cnts):
    if hier[i][3] != -1: continue
    if cv2.contourArea(c) < 400 * UP * UP / 4: continue   # drop specks
    holes = []
    j = hier[i][2]
    while j != -1:
        if cv2.contourArea(cnts[j]) > 60 * UP * UP / 4:
            holes.append(topts(cnts[j]))
        j = hier[j][0]
    p = Polygon(topts(c), holes).buffer(0).simplify(1.2)
    polys.append(p)
text = unary_union(polys)

# provisional scale, then build outline, then rescale to TARGET
minx, miny, maxx, maxy = text.bounds
s = 1.0
for _ in range(6):
    t = trimesh.transformations
    from shapely import affinity
    tx = affinity.scale(text, s, s, origin=(0, 0))
    base = tx.buffer(MARGIN / 1, join_style=1, quad_segs=16)
    base = Polygon(max(getattr(base, 'geoms', [base]), key=lambda g: g.area).exterior)
    b = base.bounds
    cx = (b[0] + b[2]) / 2
    tab = Point(cx, b[3] + TAB_R * 0.35).buffer(TAB_R, quad_segs=48)
    base = unary_union([base, tab]).buffer(1.0, join_style=1).buffer(-1.0, join_style=1)  # fillet joint
    hole_c = (cx, b[3] + TAB_R * 0.35)
    bb = base.bounds
    size = max(bb[2] - bb[0], bb[3] - bb[1])
    s *= TARGET / size
base = base.difference(Point(hole_c).buffer(HOLE_D / 2, quad_segs=48))
# move to origin
bb = base.bounds
from shapely import affinity
base = affinity.translate(base, -bb[0], -bb[1])
tx = affinity.translate(tx, -bb[0], -bb[1])
print('scale mm/px(orig):', s * UP, 'size:', base.bounds)

def ext(g, h, z):
    ms = [trimesh.creation.extrude_polygon(p, h) for p in getattr(g, 'geoms', [g])]
    mm = trimesh.util.concatenate(ms); mm.apply_translation([0, 0, z]); return mm
mb = ext(base, T_BASE, 0)
mt = ext(tx, T_TEXT, T_BASE)
print('watertight', mb.is_watertight, mt.is_watertight)
mb.export('../SOON_keychain_base_orange.stl')
mt.export('../SOON_keychain_text_white.stl')
sc = trimesh.Scene(); sc.add_geometry(mb, 'base_orange'); sc.add_geometry(mt, 'text_white')
sc.export('../SOON_keychain_2color.3mf')

# min feature check: thinnest stroke via erosion test
for w in (0.8, 1.0, 1.2):
    e = tx.buffer(-w / 2)
    print(f'area lost if strokes <{w}mm removed: {1 - (e.buffer(w/2).area / tx.area):.3f}')
import pickle; pickle.dump((base, tx), open('geom.pkl', 'wb'))
