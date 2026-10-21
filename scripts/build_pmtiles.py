"""Build buildings.pmtiles from Supabase using the public REST API.

Usage:
  python scripts/build_pmtiles.py

By default, URL and key are read from config.js. Environment variables can
override them for CI. The publishable key is public; RLS protects the view.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BATCH = 1000
ROOT = Path(__file__).resolve().parents[1]
TABLE = "gebaeude_stp"


def read_public_config():
    config_text = (ROOT / "config.js").read_text(encoding="utf-8")
    config = {}
    for name in ("SUPABASE_URL", "SUPABASE_ANON_KEY"):
        match = re.search(
            rf'^\s*{name}:\s*("(?:\\.|[^"\\])*")\s*,?\s*(?://.*)?$',
            config_text,
            re.MULTILINE,
        )
        if match:
            config[name] = json.loads(match.group(1))
    return config


def fetch_page(base_url, api_key, offset):
    query = urlencode({
        "select": "id,globalid,address_1,address_2,hoehe_objekt_max,building_year,geom",
        "order": "id.asc",
        "limit": BATCH,
        "offset": offset,
    })
    request = Request(
        f"{base_url}/rest/v1/{TABLE}?{query}",
        headers={"apikey": api_key, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        sys.exit(f"Supabase REST request failed ({error.code}): {details}")
    except URLError as error:
        sys.exit(f"Could not reach Supabase: {error.reason}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "buildings.pmtiles",
        help="output PMTiles archive (default: buildings.pmtiles in the project root)",
    )
    args = parser.parse_args()

    config = read_public_config()
    supabase_url = (
        os.environ.get("SUPABASE_URL") or config.get("SUPABASE_URL", "")
    ).rstrip("/")
    api_key = (
        os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or config.get("SUPABASE_ANON_KEY")
    )
    if not supabase_url or not api_key:
        sys.exit("Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY or add them to config.js.")
    tippecanoe = shutil.which("tippecanoe") or str(Path.home() / ".local/bin/tippecanoe")
    if not os.access(tippecanoe, os.X_OK):
        sys.exit("tippecanoe is required; install it and retry.")

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_geojson = None
    count = 0

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".geojson", dir=output.parent, delete=False
        ) as geojson_file:
            temporary_geojson = Path(geojson_file.name)
            geojson_file.write('{"type":"FeatureCollection","features":[\n')

            offset = 0
            while rows := fetch_page(supabase_url, api_key, offset):
                for row in rows:
                    if count:
                        geojson_file.write(",\n")
                    feature = {
                        "type": "Feature",
                        "properties": {
                            "bev_id": row["globalid"],
                            "address_1": row["address_1"],
                            "address_2": row["address_2"],
                            "height_m": row["hoehe_objekt_max"],
                            "year_built": row["building_year"],
                        },
                        "geometry": row["geom"],
                    }
                    json.dump(feature, geojson_file, separators=(",", ":"))
                    count += 1
                offset += len(rows)

            geojson_file.write("\n]}\n")

        if not count:
            sys.exit("No buildings with geometry found in Supabase.")

        subprocess.run(
            [
                tippecanoe, "-o", str(output), "-l", "buildings", "-zg",
                "--drop-densest-as-needed", "--force", str(temporary_geojson),
            ],
            check=True,
        )
        print(f"Built {output} from {count} Supabase buildings.")
    finally:
        if temporary_geojson:
            temporary_geojson.unlink(missing_ok=True)


if __name__ == "__main__":
    main()