# stp_gebaede_app
## Loading building data
See `scripts/load_buildings.py`. Requires `DATABASE_URL` (Supabase Postgres URI) as an environment variable.

Building polygons: © BEV, CC BY 4.0.

## Map page
`index.html` (+ `config.js` with Supabase URL / publishable key) is a static page. PMTiles needs HTTP byte-range support, so for local development run `python scripts/serve.py` instead of `python -m http.server`.

The page loads building cards and related data directly from Supabase using the publishable key. RLS controls browser access. Building polygons are served as PMTiles. Build the archive directly from the existing `gebaeude_stp` relation using the URL and publishable key already in `config.js`:

    python scripts/build_pmtiles.py

The script writes `buildings.pmtiles` in the project root. Install `tippecanoe` before building. CI can override the config with `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` environment variables. The export maps `globalid`, `address_1`, `address_2`, `hoehe_objekt_max`, and `building_year` to tile properties. For publication, serve the archive as a static asset with HTTP byte-range support; rely on RLS for Supabase data access.

## Automatic PMTiles rebuilds
The GitHub Actions workflow builds the archive on `workflow_dispatch` and manual runs. A Supabase Database Webhook can trigger it when `public.gebaeude_stp` changes:

1. Deploy `supabase/functions/rebuild-pmtiles` with the Supabase CLI.
2. In Supabase Edge Function secrets, set `GITHUB_TOKEN` to a fine-grained GitHub token with Actions: write for `Faraposhka/stp_gebaede_app`, `GITHUB_REPOSITORY` to `Faraposhka/stp_gebaede_app`, `GITHUB_REF` to the default branch (`main`), and `WEBHOOK_SECRET` to a random secret.
3. In Database Webhooks, create a POST webhook for `public.gebaeude_stp` on INSERT (and UPDATE/DELETE if needed), pointing to the deployed function URL. Add the header `x-webhook-secret` with the same `WEBHOOK_SECRET` value.
4. The workflow output is available as the `buildings-pmtiles` Actions artifact for seven days. Configure a separate publishing step for your website host so the rebuilt archive replaces the deployed PMTiles file.

The GitHub token stays in Supabase Function secrets; never put it in `config.js` or the database webhook payload. Changes arriving during a build cancel the older run so the latest database state is rebuilt.
