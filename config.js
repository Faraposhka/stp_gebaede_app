// Public config. The anon key is read-only (RLS allows SELECT only) and safe to expose.
window.APP_CONFIG = {
  SUPABASE_URL: "https://YOUR-PROJECT.supabase.co",
  SUPABASE_ANON_KEY: "YOUR-ANON-KEY",
  PMTILES_URL: "buildings.pmtiles", // layer name inside the archive: "buildings"
  CENTER: [15.6256, 48.2047],       // St. Pölten
  ZOOM: 14
};
