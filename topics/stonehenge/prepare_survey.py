"""Stonehenge: turn the raw open data into one measured table of stones.

Inputs (fetched by engine.fetch from sources.json):
  data/stonehenge/osm/map.osm                      OpenStreetMap extract (WGS84)
  data/stonehenge/lidar/SU1040_point_cloud_2021.zip  Environment Agency point cloud
  data/stonehenge/lidar/SU1040_dtm_2022.zip          Environment Agency 1 m ground model

Output:
  build/stonehenge/survey.json   every mapped footprint with its measured height,
                                 the ditch and bank lines, and the fitted circle.

Nothing here decides what a stone is called or whether it "stands": that is done
in stones.py against the published record. This file only measures.

Run:  python -m topics.stonehenge.prepare_survey
"""
from __future__ import annotations

import io
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import laspy
import numpy as np
import tifffile
from pyproj import Transformer
from scipy.optimize import least_squares
from shapely.geometry import Point, Polygon
from shapely.prepared import prep
from engine.files import fresh, write_text as save_text

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "stonehenge"
OUT = ROOT / "build" / "stonehenge"

CENTRE_GUESS = (412245.0, 142194.0)   # British National Grid, metres
WINDOW = 130.0                        # half-size of the point-cloud window, metres


def read_osm(path: Path) -> list[dict]:
    """OSM ways as polylines in British National Grid metres."""
    to_grid = Transformer.from_crs(4326, 27700, always_xy=True)
    root = ET.parse(path).getroot()
    nodes = {n.get("id"): to_grid.transform(float(n.get("lon")), float(n.get("lat")))
             for n in root.iter("node")}
    ways = []
    for way in root.iter("way"):
        refs = [nd.get("ref") for nd in way.findall("nd")]
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        ways.append({
            "id": way.get("id"),
            "tags": tags,
            "closed": len(refs) > 2 and refs[0] == refs[-1],
            "pts": [list(nodes[r]) for r in refs if r in nodes],
        })
    return ways


def read_point_window(zip_path: Path) -> np.ndarray:
    """x, y, z, class, return number for points within WINDOW of the centre."""
    cache = OUT / "points_window.npy"
    if cache.exists():
        return np.load(cache)
    with zipfile.ZipFile(zip_path) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".laz"))
        laz = OUT / name
        if not laz.exists():
            archive.extract(name, OUT)
    cx, cy = CENTRE_GUESS
    kept = []
    with laspy.open(laz) as reader:
        header = reader.header
        print("point cloud:", header.point_count, "points")
        for chunk in reader.chunk_iterator(2_000_000):
            inside = (np.abs(chunk.x - cx) < WINDOW) & (np.abs(chunk.y - cy) < WINDOW)
            if inside.any():
                kept.append(np.c_[chunk.x[inside], chunk.y[inside], chunk.z[inside],
                                  chunk.classification[inside], chunk.return_number[inside]])
    points = np.vstack(kept)
    np.save(fresh(cache), points)
    laz.unlink()            # the 188 MB file stays zipped under data/
    return points


def read_ground(zip_path: Path):
    """1 m ground model as (array, x of west edge, y of north edge, cell size)."""
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        tif = next(n for n in names if n.lower().endswith(".tif"))
        tfw = next((n for n in names if n.lower().endswith(".tfw")), None)
        grid = tifffile.imread(io.BytesIO(archive.read(tif)))
        if tfw:
            a, _, _, e, c, f = [float(v) for v in archive.read(tfw).decode().split()]
            west, north, cell = c - a / 2, f - e / 2, a
        else:
            with tifffile.TiffFile(io.BytesIO(archive.read(tif))) as handle:
                page = handle.pages[0]
                scale = page.tags["ModelPixelScaleTag"].value
                tie = page.tags["ModelTiepointTag"].value
                west, north, cell = tie[3], tie[4], scale[0]
    return grid, west, north, cell


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ways = read_osm(DATA / "osm" / "map.osm")
    points = read_point_window(DATA / "lidar" / "SU1040_point_cloud_2021.zip")
    grid, west, north, cell = read_ground(DATA / "lidar" / "SU1040_dtm_2022.zip")
    print("ground model", grid.shape, "west", west, "north", north, "cell", cell)

    def ground(x: float, y: float) -> float:
        col = int((x - west) / cell)
        row = int((north - y) / cell)
        return float(grid[row, col])

    xy = points[:, :2]
    stones = []
    for way in ways:
        tags = way["tags"]
        if not way["closed"] or tags.get("natural") != "stone":
            continue
        ring = np.array(way["pts"][:-1])
        polygon = Polygon(ring)
        centroid = polygon.centroid
        # points over the footprint, with a 0.4 m margin for map/scan offset
        near = prep(polygon.buffer(0.4))
        box = polygon.buffer(0.4).bounds
        candidates = np.where((xy[:, 0] >= box[0]) & (xy[:, 0] <= box[2]) &
                              (xy[:, 1] >= box[1]) & (xy[:, 1] <= box[3]))[0]
        over = [i for i in candidates if near.contains(Point(xy[i]))]
        base = ground(centroid.x, centroid.y)
        heights = points[over, 2] - base if over else np.array([0.0])
        # minimum rotated rectangle gives length, width and long-axis bearing
        rect = np.array(polygon.minimum_rotated_rectangle.exterior.coords)[:4]
        edges = [(np.hypot(*(rect[(i + 1) % 4] - rect[i])), rect[(i + 1) % 4] - rect[i]) for i in range(2)]
        edges.sort(key=lambda e: -e[0])
        long_len, long_vec = edges[0]
        stones.append({
            "osm_id": way["id"],
            "name": tags.get("name", ""),
            "ref": tags.get("ref", ""),
            "poly": ring.round(3).tolist(),
            "cx": round(centroid.x, 3), "cy": round(centroid.y, 3),
            "area": round(polygon.area, 2),
            "length": round(float(long_len), 2), "width": round(float(edges[1][0]), 2),
            "bearing": round(float(np.degrees(np.arctan2(long_vec[0], long_vec[1])) % 180), 1),
            "n_points": len(over),
            "h_max": round(float(heights.max()), 2),
            "h_p90": round(float(np.percentile(heights, 90)), 2),
            "ground": round(base, 2),
        })

    # circle through the larger unnamed footprints between 13.4 and 19 m from the guess
    c0 = np.array(CENTRE_GUESS)
    ring_pts = np.array([[s["cx"], s["cy"]] for s in stones
                         if 13.4 < np.hypot(s["cx"] - c0[0], s["cy"] - c0[1]) < 19 and s["area"] > 2 and not s["name"]])

    def residual(q, pts=ring_pts):
        return np.hypot(pts[:, 0] - q[0], pts[:, 1] - q[1]) - q[2]

    fit = least_squares(residual, [c0[0], c0[1], 16.0]).x
    keep = np.abs(residual(fit)) < 1.6
    fit = least_squares(lambda q: residual(q, ring_pts[keep]), fit).x
    cx, cy, radius = [float(v) for v in fit]

    for stone in stones:
        dx, dy = stone["cx"] - cx, stone["cy"] - cy
        stone["r"] = round(float(np.hypot(dx, dy)), 2)
        stone["azimuth"] = round(float(np.degrees(np.arctan2(dx, dy)) % 360), 1)   # clockwise from grid north

    def lines(key: str, value: str) -> list[dict]:
        return [{"closed": w["closed"], "name": w["tags"].get("name", ""),
                 "pts": np.array(w["pts"]).round(2).tolist()}
                for w in ways if w["tags"].get(key) == value and len(w["pts"]) > 1]

    survey = {
        "crs": "EPSG:27700",
        "centre": [round(cx, 3), round(cy, 3)],
        "circle_radius": round(radius, 3),
        "circle_fit_stones": int(keep.sum()),
        "stones": sorted(stones, key=lambda s: (round(s["r"] / 4), s["azimuth"])),
        "ditch": lines("barrier", "ditch"),
        "bank": lines("man_made", "embankment"),
        "points_in_window": int(len(points)),
    }
    save_text(OUT / "survey.json", json.dumps(survey, indent=1))
    print(f"centre {cx:.2f} {cy:.2f}  circle radius {radius:.2f} m  from {int(keep.sum())} footprints")
    print(f"{len(stones)} footprints")
    print(" osm_id        name              r   azim  area   len  wid  bear   n  hmax  hp90")
    for s in sorted(stones, key=lambda s: (s["r"] > 13.0 and s["r"] < 19.5, s["azimuth"])):
        print(f" {s['osm_id']:>11} {s['name'][:14]:<14} {s['r']:6.2f} {s['azimuth']:6.1f} {s['area']:5.1f} "
              f"{s['length']:5.2f} {s['width']:4.2f} {s['bearing']:5.1f} {s['n_points']:3d} {s['h_max']:5.2f} {s['h_p90']:5.2f}")


if __name__ == "__main__":
    main()
