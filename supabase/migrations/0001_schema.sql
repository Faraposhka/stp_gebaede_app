-- St. Pölten history map: PostgreSQL/PostGIS schema (Supabase).
-- Geometries use EPSG:4326 (lon/lat), which MapLibre expects.
-- Building polygons: BEV (CC BY 4.0) - attribution "© BEV" must be shown in the UI.

create extension if not exists postgis;

-- Cities -------------------------------------------------------------
create table cities (
  id          bigint generated always as identity primary key,
  name        text not null unique,
  country     text not null default 'AT',
  wikidata_id text,
  center      geometry(Point, 4326)
);

-- Sources (provenance of every fact) ---------------------------------
create table sources (
  id            bigint generated always as identity primary key,
  source_type   text not null
    check (source_type in ('Denkmalliste','Gedenktafel','Bauakt','Literatur','Wikidata')),
  reference     text not null,          -- citation, URL, file number, Q-id ...
  date_accessed date,
  photo_url     text
);

-- Buildings (BEV polygons) -------------------------------------------
create table buildings (
  id         bigint generated always as identity primary key,
  bev_id     text not null unique,      -- id from the BEV dataset
  city_id    bigint references cities(id) on delete set null,
  geom       geometry(MultiPolygon, 4326) not null,
  name       text,                      -- optional own attributes
  address    text,
  year_built int check (year_built between 0 and 2100)
);

-- Cards (facts) -------------------------------------------------------
create table cards (
  id          bigint generated always as identity primary key,
  title       text,
  body        text not null,
  year_from   int,
  year_to     int,
  date_type   text not null
    check (date_type in ('Bau','Umbau','Erwähnung','Gedenktafel')),
  confidence  smallint not null default 3
    check (confidence between 1 and 5),  -- 1 = uncertain, 5 = documented
  building_id bigint references buildings(id) on delete cascade,
  geom        geometry(Point, 4326),    -- used when no building is linked
  source_id   bigint references sources(id) on delete set null,
  city_id     bigint references cities(id) on delete set null,
  check (building_id is not null or geom is not null),
  check (year_to is null or year_from is null or year_to >= year_from)
);

-- People --------------------------------------------------------------
create table people (
  id          bigint generated always as identity primary key,
  name        text not null,
  birth_year  int,
  death_year  int,
  wikidata_id text unique,
  description text
);

-- Events --------------------------------------------------------------
create table events (
  id          bigint generated always as identity primary key,
  name        text not null,
  date_from   date,
  date_to     date,
  wikidata_id text unique,
  check (date_to is null or date_from is null or date_to >= date_from)
);

-- Tags (controlled vocabulary) ---------------------------------------
create table tags (
  id   bigint generated always as identity primary key,
  name text not null unique
);

-- Join tables ---------------------------------------------------------
create table card_people (
  card_id   bigint not null references cards(id)  on delete cascade,
  person_id bigint not null references people(id) on delete cascade,
  primary key (card_id, person_id)
);
create table card_events (
  card_id  bigint not null references cards(id)  on delete cascade,
  event_id bigint not null references events(id) on delete cascade,
  primary key (card_id, event_id)
);
create table card_tags (
  card_id bigint not null references cards(id) on delete cascade,
  tag_id  bigint not null references tags(id)  on delete cascade,
  primary key (card_id, tag_id)
);

-- Indexes -------------------------------------------------------------
-- Spatial
create index buildings_geom_idx on buildings using gist (geom);
create index cards_geom_idx     on cards     using gist (geom);
create index cities_center_idx  on cities    using gist (center);
-- Foreign keys (the PK of join tables already covers the first column)
create index buildings_city_idx   on buildings (city_id);
create index cards_building_idx   on cards (building_id);
create index cards_source_idx     on cards (source_id);
create index cards_city_idx       on cards (city_id);
create index cards_years_idx      on cards (year_from, year_to);
create index card_people_person_idx on card_people (person_id);
create index card_events_event_idx  on card_events (event_id);
create index card_tags_tag_idx      on card_tags (tag_id);

-- Row Level Security: public anon/authenticated roles may only read ----
-- No insert/update/delete policies exist, so writes are denied.
-- Writes must use the service_role key (bypasses RLS) from trusted code.
do $$
declare t text;
begin
  foreach t in array array['cities','sources','buildings','cards','people',
    'events','tags','card_people','card_events','card_tags']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy "public read" on %I for select to anon, authenticated using (true)', t);
    execute format('revoke insert, update, delete, truncate on %I from anon, authenticated', t);
  end loop;
end $$;
