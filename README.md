# stp_gebaede_app
## Loading building data
See `scripts/load_buildings.py`. Requires `DATABASE_URL` (Supabase Postgres URI) as an environment variable.

Building polygons: © BEV, CC BY 4.0.

## Map page
`index.html` (+ `config.js` with Supabase URL / anon key) is a static page; serve it with any static server, e.g. `python -m http.server`.
Build the tiles (layer must be named `buildings`, properties `bev_id`, `height_m`, `year_built`), e.g. from the database export:

    tippecanoe -o buildings.pmtiles -l buildings -zg --drop-densest-as-needed --force buildings.geojson

The Supabase anon key is read-only (RLS). Colours use `year_built` (gray = unknown).
