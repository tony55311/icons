import sys
import trimesh, numpy as np
from PIL import Image
MS = [(trimesh.load(sys.argv[1]), (1.0, 0.45, 0.05)), (trimesh.load(sys.argv[2]), (0.97, 0.97, 0.97)), (trimesh.load(sys.argv[3]), (0.12, 0.12, 0.12))]; b = MS[0][0]
def rot(el, az):
    a, e = np.radians(az), np.radians(el)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return Rx @ Rz
def render(R, W=700, Hh=700):
    tris, cols = [], []
    L = np.array([-0.35, 0.45, 0.82]); L /= np.linalg.norm(L)
    c0 = (b.bounds[0] + b.bounds[1]) / 2
    for m, col in MS:
        v = (m.triangles - c0) @ R.T
        n = m.face_normals @ R.T
        sh = 0.35 + 0.65 * np.clip(n @ L, 0, 1)
        tris.append(v); cols.append(np.array(col)[None] * sh[:, None])
    tris = np.concatenate(tris); cols = np.concatenate(cols)
    sc = 0.85 * W / np.ptp(tris[..., :2].reshape(-1, 2), axis=0).max()
    P = tris.copy(); P[..., 0] = P[..., 0] * sc + W / 2; P[..., 1] = Hh / 2 - P[..., 1] * sc
    zb = np.full((Hh, W), -1e9); img = np.full((Hh, W, 3), 0.93)
    for tri, c in zip(P, cols):
        x0, y0 = np.floor(tri[:, :2].min(0)).astype(int); x1, y1 = np.ceil(tri[:, :2].max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W - 1), min(y1, Hh - 1)
        if x1 < x0 or y1 < y0: continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12: continue
        w1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
        w2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
        w3 = 1 - w1 - w2
        ins = (w1 >= -1e-6) & (w2 >= -1e-6) & (w3 >= -1e-6)
        z = w1 * az + w2 * bz + w3 * cz
        sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = ins & (z > sub)
        sub[upd] = z[upd]; img[y0:y1 + 1, x0:x1 + 1][upd] = c
    return Image.fromarray((img * 255).astype(np.uint8))
a = render(rot(0, 0)); c = render(rot(-50, -25))
out = Image.new('RGB', (1400, 700)); out.paste(a, (0, 0)); out.paste(c, (700, 0))
out.save(sys.argv[4])
