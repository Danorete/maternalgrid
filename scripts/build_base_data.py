"""Build the real Georgia county base layer for MaternalGrid.

Input : a national county GeoJSON (US Census cartographic boundaries, 500k).
Output: data/ga_counties.geojson  (159 Georgia counties, keyed by 5 char GEOID)
        data/counties.csv         (GEOID, county, lat, lon, land_area_sq_mi)

Centroids are area weighted polygon centroids computed from the real boundary
geometry, so they are derived values rather than an outside estimate.

Usage: python scripts/build_base_data.py <path_to_national_counties.geojson>
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GA_STATE_FIPS = "13"


def ring_area_and_centroid(ring):
    """Shoelace area and centroid of one linear ring in degree space."""
    a = 0.0
    cx = 0.0
    cy = 0.0
    n = len(ring)
    for i in range(n - 1):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[i + 1][0], ring[i + 1][1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if a == 0:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return a, cx / (6 * a), cy / (6 * a)


def polygons_of(geometry):
    """Yield each polygon (list of rings) from a Polygon or MultiPolygon."""
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            yield poly


def feature_centroid(geometry):
    """Area weighted centroid across all polygons, outer ring minus holes."""
    total = 0.0
    sx = 0.0
    sy = 0.0
    for poly in polygons_of(geometry):
        for idx, ring in enumerate(poly):
            area, cx, cy = ring_area_and_centroid(ring)
            # Outer ring adds area, interior rings (holes) subtract it.
            signed = abs(area) if idx == 0 else -abs(area)
            total += signed
            sx += cx * signed
            sy += cy * signed
    if total == 0:
        raise ValueError("degenerate geometry")
    return sy / total, sx / total  # lat, lon


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: build_base_data.py <national_counties.geojson>")
    src = json.loads(Path(sys.argv[1]).read_text())

    features = []
    rows = []
    for feat in src["features"]:
        props = feat["properties"]
        if props.get("STATE") != GA_STATE_FIPS:
            continue
        geoid = f"{props['STATE']}{props['COUNTY']}"
        name = props["NAME"]
        lat, lon = feature_centroid(feat["geometry"])
        features.append(
            {
                "type": "Feature",
                "id": geoid,
                "properties": {"GEOID": geoid, "county": name},
                "geometry": feat["geometry"],
            }
        )
        rows.append((geoid, name, round(lat, 6), round(lon, 6), props.get("CENSUSAREA", "")))

    if len(features) != 159:
        raise SystemExit(f"expected 159 Georgia counties, got {len(features)}")

    rows.sort(key=lambda r: r[0])
    features.sort(key=lambda f: f["id"])

    DATA.mkdir(exist_ok=True)
    (DATA / "ga_counties.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    with (DATA / "counties.csv").open("w") as fh:
        fh.write("GEOID,county,lat,lon,land_area_sq_mi\n")
        for geoid, name, lat, lon, area in rows:
            fh.write(f"{geoid},{name},{lat},{lon},{area}\n")

    print(f"wrote {len(features)} counties to data/ga_counties.geojson and data/counties.csv")


if __name__ == "__main__":
    main()
