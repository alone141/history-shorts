"""Triangle and line geometry for the phase model, as numpy arrays.

World frame: x east, y up, z south. Plan data arrives as (x east, y north)
and is turned with z = -north.

Every builder returns float32 arrays of interleaved position + normal
(6 floats per vertex, triangles), unless noted.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import Polygon

HARD_CORNER_DOT = 0.78        # neighbouring edges that turn more sharply than this keep a crisp corner


def _ring(poly: list[list[float]]) -> np.ndarray:
    """Plan polygon -> counter-clockwise ring in (x, z)."""
    pts = np.array([[x, -y] for x, y in poly], dtype=np.float64)
    nxt = np.roll(pts, -1, axis=0)
    if np.sum(pts[:, 0] * nxt[:, 1] - nxt[:, 0] * pts[:, 1]) < 0:
        pts = pts[::-1]
    return pts


def _chaikin(pts: np.ndarray) -> np.ndarray:
    nxt = np.roll(pts, -1, axis=0)
    out = np.empty((2 * len(pts), 2))
    out[0::2] = 0.75 * pts + 0.25 * nxt
    out[1::2] = 0.25 * pts + 0.75 * nxt
    return out


def prism(poly: list[list[float]], base: float, top: float, taper: float = 1.0, bevel: float = 0.15,
          hole: list[list[float]] | None = None, rings: tuple[bool, bool] = (True, True), cap: bool = True) -> dict:
    """A tapered prism with a small top bevel.

    `hole` leaves out the part of the top face that another block stands on (a plan
    polygon inside the top face), so a stack of blocks is not drawn many times over.
    `rings` says whether the foot ring and the shoulder ring are among the edges drawn in light.
    `cap=False` leaves the top open (for a volume that another volume continues).

    Sides shade smoothly round curves and stay crisp at real corners.
    Returns {"tris": (n, 6), "lines": (m, 3) line-segment endpoints for the
    edges worth drawing in light, "foot": (k, 3) triangles of the footprint
    at y = 0, "centre": (x, z)}.
    """
    ring = _ring(poly)
    if len(ring) > 20:
        ring = _chaikin(ring)
    n = len(ring)
    centre = ring.mean(axis=0)
    mean_r = float(np.mean(np.hypot(*(ring - centre).T)))
    height = top - base
    bv = min(bevel, height * 0.3, mean_r * 0.35)
    levels = [(base, 1.0), (top - bv, taper), (top, taper * (1 - bv / mean_r))]

    def at(level: tuple[float, float]) -> np.ndarray:
        y, s = level
        xz = centre + (ring - centre) * s
        return np.c_[xz[:, 0], np.full(n, y), xz[:, 1]]

    edge = np.roll(ring, -1, axis=0) - ring
    edge /= np.maximum(np.hypot(edge[:, 0], edge[:, 1])[:, None], 1e-9)
    edge_n = np.c_[edge[:, 1], -edge[:, 0]]                    # outward normal of edge i -> i+1
    prev_n = np.roll(edge_n, 1, axis=0)
    smooth = np.sum(prev_n * edge_n, axis=1) > HARD_CORNER_DOT
    vert_n = prev_n + edge_n
    vert_n /= np.maximum(np.hypot(vert_n[:, 0], vert_n[:, 1])[:, None], 1e-9)

    tris: list[np.ndarray] = []
    nxt = (np.arange(n) + 1) % n
    for lo, hi in zip(levels[:-1], levels[1:]):
        a, d = at(lo), at(hi)
        b, c = a[nxt], d[nxt]
        inset = (lo[1] - hi[1]) * mean_r
        tilt = np.arctan2(inset, hi[0] - lo[0])
        ct, st = np.cos(tilt), np.sin(tilt)
        n_i = np.where(smooth[:, None], vert_n, edge_n)                 # normal at vertex i for edge i
        n_j = np.where(smooth[nxt][:, None], vert_n[nxt], edge_n)       # normal at vertex i+1 for edge i
        ni = np.c_[n_i[:, 0] * ct, np.full(n, st), n_i[:, 1] * ct]
        nj = np.c_[n_j[:, 0] * ct, np.full(n, st), n_j[:, 1] * ct]
        quad = np.stack([np.c_[a, ni], np.c_[b, nj], np.c_[c, nj], np.c_[a, ni], np.c_[c, nj], np.c_[d, ni]], axis=1)
        tris.append(quad.reshape(-1, 6))

    cap_y, cap_s = levels[-1]
    cap_xz = centre + (ring - centre) * cap_s
    if cap:
        lid = _triangulate(cap_xz, _ring(hole) if hole else None)
        tris.append(np.c_[lid[:, 0], np.full(len(lid), cap_y), lid[:, 1], np.zeros(len(lid)), np.ones(len(lid)), np.zeros(len(lid))])

    # edges to draw in light: foot ring, shoulder ring, and uprights at hard corners
    lines: list[np.ndarray] = []
    for level, wanted in zip((levels[0], levels[1]), rings):
        if wanted:
            p = at(level)
            lines.append(np.stack([p, p[nxt]], axis=1).reshape(-1, 3))
    hard = np.where(~smooth)[0]
    if len(hard):
        lo, hi = at(levels[0])[hard], at(levels[1])[hard]
        lines.append(np.stack([lo, hi], axis=1).reshape(-1, 3))

    foot = _triangulate(ring)
    return {
        "tris": np.vstack(tris).astype("f4"),
        "lines": (np.vstack(lines) if lines else np.zeros((0, 3))).astype("f4"),
        "foot": np.c_[foot[:, 0], np.zeros(len(foot)), foot[:, 1]].astype("f4"),
        "centre": (float(centre[0]), float(centre[1])),
    }


def _triangulate(ring_xz: np.ndarray, hole_xz: np.ndarray | None = None) -> np.ndarray:
    """Triangles (k*3, 2) filling a simple polygon, less an optional hole."""
    polygon = Polygon(ring_xz, [hole_xz] if hole_xz is not None else None)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    out = []
    for tri in shapely.constrained_delaunay_triangles(polygon).geoms:
        out.extend(list(tri.exterior.coords)[:3])
    return np.array(out, dtype=np.float64)


def disc(radius: float, y: float, segments: int = 192) -> np.ndarray:
    a = np.linspace(0, 2 * np.pi, segments + 1)
    rim = np.c_[radius * np.cos(a), np.full(segments + 1, y), radius * np.sin(a)]
    centre = np.array([0.0, y, 0.0])
    tri = np.stack([np.repeat(centre[None], segments, 0), rim[:-1], rim[1:]], axis=1).reshape(-1, 3)
    return np.c_[tri, np.tile([0.0, 1.0, 0.0], (len(tri), 1))].astype("f4")


def annulus(r0: float, r1: float, y: float, segments: int = 192) -> np.ndarray:
    a = np.linspace(0, 2 * np.pi, segments + 1)
    inner = np.c_[r0 * np.cos(a), np.full(segments + 1, y), r0 * np.sin(a)]
    outer = np.c_[r1 * np.cos(a), np.full(segments + 1, y), r1 * np.sin(a)]
    tri = np.stack([inner[:-1], outer[:-1], outer[1:], inner[:-1], outer[1:], inner[1:]], axis=1).reshape(-1, 3)
    return np.c_[tri, np.tile([0.0, 1.0, 0.0], (len(tri), 1))].astype("f4")


def cone_wall(r_top: float, r_bottom: float, y_top: float, y_bottom: float, segments: int = 192) -> np.ndarray:
    """Side wall of a (possibly tapered) cylinder, smooth normals."""
    a = np.linspace(0, 2 * np.pi, segments + 1)
    cos, sin = np.cos(a), np.sin(a)
    top = np.c_[r_top * cos, np.full(segments + 1, y_top), r_top * sin]
    bottom = np.c_[r_bottom * cos, np.full(segments + 1, y_bottom), r_bottom * sin]
    slope = (r_bottom - r_top) / max(y_top - y_bottom, 1e-9)
    normal = np.c_[cos, np.full(segments + 1, slope), sin]
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    quads = [np.c_[bottom[:-1], normal[:-1]], np.c_[bottom[1:], normal[1:]], np.c_[top[1:], normal[1:]],
             np.c_[bottom[:-1], normal[:-1]], np.c_[top[1:], normal[1:]], np.c_[top[:-1], normal[:-1]]]
    return np.stack(quads, axis=1).reshape(-1, 6).astype("f4")
