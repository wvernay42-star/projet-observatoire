-- Beta : SQLite. V2 : Postgres, même schéma.
CREATE TABLE sources (
  id TEXT PRIMARY KEY,            -- 'afp_factuel'
  name TEXT, country TEXT, url TEXT,
  full_scale INTEGER,             -- publie des verdicts positifs ?
  licence TEXT, connector TEXT
);

CREATE TABLE persons (
  id TEXT PRIMARY KEY,            -- QID Wikidata, ex. 'Q12345'
  full_name TEXT, aliases TEXT,   -- JSON
  country TEXT, public_role TEXT
);

CREATE TABLE parties (
  id TEXT PRIMARY KEY, name TEXT, short_name TEXT,
  country TEXT, parlgov_id INTEGER
);

CREATE TABLE affiliations (       -- datées : un politique peut changer de parti
  person_id TEXT, party_id TEXT,
  start_date TEXT, end_date TEXT, source_url TEXT
);

CREATE TABLE claims (             -- une affirmation, dédoublonnée
  id TEXT PRIMARY KEY,
  text TEXT, person_id TEXT,      -- NULL tant que non attribuée
  claim_date TEXT, date_precision TEXT, date_is_fallback INTEGER,
  country TEXT, channel TEXT,     -- 'tv', 'x', 'presse', 'meeting'...
  attribution_status TEXT         -- 'auto_sure', 'to_review', 'validated', 'rejected'
);

CREATE TABLE reviews (            -- un fact-check ; plusieurs par claim possible
  id TEXT PRIMARY KEY,            -- hash(url)
  claim_id TEXT, source_id TEXT,
  url TEXT UNIQUE, title TEXT,
  rating_original TEXT,           -- libellé exact de la source
  rating_normalized TEXT,         -- échelle commune
  review_date TEXT, ingested_at TEXT, lang TEXT
);

CREATE TABLE rating_map (
  source_id TEXT, rating_original TEXT, rating_normalized TEXT,
  decided_by TEXT                 -- 'rule', 'llm_validated', 'human'
);

CREATE TABLE official_refs (      -- module B
  claim_id TEXT, provider TEXT, series_id TEXT,
  value TEXT, unit TEXT, period TEXT, url TEXT, status TEXT
);

CREATE TABLE runs (
  id INTEGER PRIMARY KEY, started_at TEXT, connector TEXT,
  fetched INTEGER, new_reviews INTEGER, errors TEXT
);
