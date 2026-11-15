"""
Mask exact lat/lon coordinates by snapping them to hexagon bins of an
arbitrary, exact size (in km), then replacing each point's coordinates
with its hexagon's center.

A custom pointy-top hex grid is built in a local projected (meter)
coordinate system via pyproj, giving exact control over hex edge length.

Workflow:
  1. Project lat/lon -> local meters (Azimuthal Equidistant centered on
     the data's centroid -- distortion-free near the center, fine for a
     single hurricane-affected region).
  2. Snap each point to the nearest hex center on a pointy-top hex grid
     with the given edge length (HEX_EDGE_KM).
  3. Project hex centers back to lat/lon and use those as the masked
     coordinates.
"""

import numpy as np
import pandas as pd
from pyproj import Transformer

INPUT_CSV = "<path to building dataset with Latitude and Longitude>"
OUTPUT_CSV = "<path to output file>"
HEX_EDGE_KM = 0.6  # edge length = circumradius of a regular hexagon


def build_local_projection(lat0: float, lon0: float):
    fwd = Transformer.from_crs(
        "EPSG:4326",
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m +ellps=WGS84",
        always_xy=True,
    )
    inv = Transformer.from_crs(
        f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m +ellps=WGS84",
        "EPSG:4326",
        always_xy=True,
    )
    return fwd, inv


def xy_to_axial(x: np.ndarray, y: np.ndarray, s: float):
    # Pointy-top hex grid, s = edge length (center-to-corner radius).
    q = (np.sqrt(3) / 3 * x - 1 / 3 * y) / s
    r = (2 / 3 * y) / s
    return q, r


def axial_to_xy(q: np.ndarray, r: np.ndarray, s: float):
    x = s * (np.sqrt(3) * q + np.sqrt(3) / 2 * r)
    y = s * (3 / 2 * r)
    return x, y


def hex_corners_xy(cx: np.ndarray, cy: np.ndarray, s: float):
    # Pointy-top hexagon corners start at angle 30 deg and step by 60 deg.
    angles = np.deg2rad(np.arange(6) * 60 + 30)
    corner_x = cx[:, None] + s * np.cos(angles)[None, :]
    corner_y = cy[:, None] + s * np.sin(angles)[None, :]
    return corner_x, corner_y


def axial_round(q: np.ndarray, r: np.ndarray):
    cx, cz = q, r
    cy = -cx - cz
    rx, ry, rz = np.round(cx), np.round(cy), np.round(cz)
    dx, dy, dz = np.abs(rx - cx), np.abs(ry - cy), np.abs(rz - cz)

    x_largest = (dx > dy) & (dx > dz)
    y_largest = (~x_largest) & (dy > dz)

    rx = np.where(x_largest, -ry - rz, rx)
    ry = np.where((~x_largest) & y_largest, -rx - rz, ry)
    rz = np.where((~x_largest) & (~y_largest), -rx - ry, rz)
    return rx, rz  # q, r


def assign_hex_bins(df: pd.DataFrame, edge_km: float) -> pd.DataFrame:
    df = df.copy()
    s = edge_km * 1000  # meters

    lat0, lon0 = df["Latitude"].mean(), df["Longitude"].mean()
    fwd, inv = build_local_projection(lat0, lon0)

    x, y = fwd.transform(df["Longitude"].values, df["Latitude"].values)
    q, r = xy_to_axial(x, y, s)
    q, r = axial_round(q, r)

    df["hex_q"] = q.astype(int)
    df["hex_r"] = r.astype(int)
    df["hex_id"] = [f"{a}_{b}" for a, b in zip(df["hex_q"], df["hex_r"])]

    cx, cy = axial_to_xy(q, r, s)
    lon_c, lat_c = inv.transform(cx, cy)
    df["Latitude"] = lat_c
    df["Longitude"] = lon_c

    corner_x, corner_y = hex_corners_xy(cx, cy, s)
    corner_lon, corner_lat = inv.transform(corner_x, corner_y)
    df["hex_wkt"] = [
        "POLYGON ((" + ", ".join(f"{lo:.6f} {la:.6f}" for lo, la in zip(
            list(lons) + [lons[0]], list(lats) + [lats[0]]
        )) + "))"
        for lons, lats in zip(corner_lon, corner_lat)
    ]
    return df


def report_bins(df: pd.DataFrame, edge_km: float):
    counts = df["hex_id"].value_counts()
    print(f"Hex edge length: {edge_km} km")
    print(f"Hexagons used: {len(counts)}  |  Points: {len(df)}")
    print(f"Min/Median/Max points per hex: {counts.min()} / {counts.median()} / {counts.max()}")


if __name__ == "__main__":
    df = pd.read_csv(INPUT_CSV)
    masked = assign_hex_bins(df, HEX_EDGE_KM)
    report_bins(masked, HEX_EDGE_KM)
    masked.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved masked dataset -> {OUTPUT_CSV}")
