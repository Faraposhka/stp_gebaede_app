# stp_gebaede_app
## Loading building data
See `scripts/load_buildings.py`. Requires `DATABASE_URL` (Supabase Postgres URI) as an environment variable.

Building polygons: © BEV, CC BY 4.0.

## Map page
`index.html` (+ `config.js` with Supabase URL / publishable key) is a static page. PMTiles needs HTTP byte-range support, so for local development run `python scripts/serve.py` instead of `python -m http.server`.

The page loads building cards and related data directly from Supabase using the publishable key. RLS controls browser access. Building polygons are served as PMTiles. Build the archive directly from the existing `gebaeude_stp` relation using the URL and publishable key already in `config.js`:

    python scripts/build_pmtiles.py

The script writes `buildings.pmtiles` in the project root. Install `tippecanoe` before building. CI can override the config with `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` environment variables. The export maps `globalid`, `address_1`, `address_2`, `hoehe_objekt_max`, and `building_year` to tile properties. For publication, serve the archive as a static asset with HTTP byte-range support; rely on RLS for Supabase data access.
