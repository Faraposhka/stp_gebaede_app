"""Load gebaeude_stp.geojson (BEV, CC BY 4.0) into the Supabase `buildings` table.

Usage:
  pip install "psycopg[binary]"
  export DATABASE_URL='postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres'
  python scripts/load_buildings.py

DATABASE_URL is a secret: keep it in your shell/.env (git-ignored), never commit it.
Only GLOBALID, address_1, address_2 and the geometry are kept; the rest is dropped.
Re-running is safe (existing GLOBALIDs are skipped).
"""
import json
import os
import sys

import psycopg

FILE = os.path.join(os.path.dirname(__file__), "..", "gebaeude_stp.geojson")
GKZ = "30201"  # St. Pölten
BATCH = 500

# ST_MakeValid may return a collection; keep only polygons, as MultiPolygon.
SQL = """
insert into buildings (bev_id, gkz, address, address_2, geom)
values (%s, %s, %s, %s,
  ST_Multi(ST_CollectionExtract(
    ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3)))
on conflict (bev_id) do nothing
"""


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Set DATABASE_URL first (see docstring).")
    with open(FILE, encoding="utf-8") as f:
        features = json.load(f)["features"]

    rows = []
    for ft in features:
        p = ft["properties"]
        rows.append((p["GLOBALID"], GKZ, p.get("address_1"), p.get("address_2"),
                     json.dumps(ft["geometry"])))

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        for i in range(0, len(rows), BATCH):
            cur.executemany(SQL, rows[i:i + BATCH])
        conn.commit()
        cur.execute("select count(*), count(*) filter (where not ST_IsValid(geom)) from buildings")
        total, invalid = cur.fetchone()
    print(f"buildings in DB: {total}, invalid geometries: {invalid}")


if __name__ == "__main__":
    main()
