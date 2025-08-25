-- Enable search extensions and indexes for all search modes (single reusable script)
-- Current app search modes:
--  - Substring search: ILIKE on title/artist (accelerated by trigram GIN)
--  - Trigram similarity: title % :q OR artist % :q (requires pg_trgm)
--  - ORDER BY title in some queries (helped by B-tree index)
--  - Full-text search (ts_rank): tsvector column + GIN index
-- Requires PostgreSQL. Run with a superuser or a role with CREATE privilege.
--
-- Usage (Windows PowerShell examples):
--   # Dev/local (fast, transaction-safe index builds)
--   psql "host=HOST port=5432 dbname=DB user=USER password=PASS" -v ENVPROD=false -f \
--     ".\\server\\scripts\\setup\\enable_pg_trgm.sql"
--
--   # Staging/Prod (minimal locking with CONCURRENTLY; not in a transaction)
--   psql "host=HOST port=5432 dbname=DB user=USER password=PASS" -v ENVPROD=true -f \
--     ".\\server\\scripts\\setup\\enable_pg_trgm.sql"
--
-- The script auto-selects CONCURRENTLY if ENVPROD is true/TRUE/1.

-- 1) Enable extension (idempotent)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2) Normalize ENVPROD and choose concurrent vs non-concurrent index builds
\if :{?ENVPROD}
  \echo Using ENVPROD = :ENVPROD
\else
  \set ENVPROD false
  \echo ENVPROD not provided; defaulting to false (non-concurrent)
\endif

\if :ENVPROD
  \set USE_CONCURRENT 1
\else
  \set USE_CONCURRENT 0
\endif

-- 3) Trigram GIN indexes to accelerate ILIKE/LIKE and similarity (%)
-- Note: CONCURRENTLY form avoids long locks but cannot run inside a transaction block.

\if :USE_CONCURRENT
  CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_title_trgm ON songs USING gin (title gin_trgm_ops);
  CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_artist_trgm ON songs USING gin (artist gin_trgm_ops);
\else
  CREATE INDEX IF NOT EXISTS idx_songs_title_trgm ON songs USING gin (title gin_trgm_ops);
  CREATE INDEX IF NOT EXISTS idx_songs_artist_trgm ON songs USING gin (artist gin_trgm_ops);
\endif

-- 4) B-tree index to improve ORDER BY title performance
\if :USE_CONCURRENT
  CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_title_btree ON songs (title);
\else
  CREATE INDEX IF NOT EXISTS idx_songs_title_btree ON songs (title);
\endif

-- 5) Full-text search: generated tsvector column and GIN index
--    Matches the app's text search on title+artist using 'simple' config.
ALTER TABLE songs
  ADD COLUMN IF NOT EXISTS ts tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(artist,''))
  ) STORED;

\if :USE_CONCURRENT
  CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_songs_ts_gin ON songs USING gin (ts);
\else
  CREATE INDEX IF NOT EXISTS idx_songs_ts_gin ON songs USING gin (ts);
\endif

-- Optional future: switch to trigram similarity ranking
-- Example query idea (not executed here):
--   SELECT id, title, artist
--   FROM songs
--   WHERE title % :q OR artist % :q
--   ORDER BY GREATEST(similarity(title, :q), similarity(artist, :q)) DESC
--   LIMIT :limit;
-- This uses the trigram similarity operator (%) and can leverage the same GIN indexes.

-- Full-text search is enabled above via a generated 'ts' column and GIN index.
-- Query example (align with application for best index usage):
--   SELECT id, title, artist, page_count,
--          ts_rank(ts, plainto_tsquery('simple', :q)) AS rank
--   FROM songs
--   WHERE ts @@ plainto_tsquery('simple', :q)
--   ORDER BY rank DESC, title ASC
--   LIMIT :limit;
