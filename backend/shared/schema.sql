CREATE TABLE IF NOT EXISTS vessel_master (
    imo               BIGINT PRIMARY KEY,
    name              TEXT,
    subtype           TEXT NOT NULL,
    dwt               INTEGER,
    design_draught_m  NUMERIC,
    length_m          NUMERIC,
    width_m           NUMERIC,
    flag              TEXT,
    year_built        SMALLINT,
    source            TEXT NOT NULL,
    loaded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vessels (
    mmsi               BIGINT PRIMARY KEY,
    imo                BIGINT REFERENCES vessel_master(imo),
    name               TEXT,
    ship_type          SMALLINT NOT NULL,
    subtype            TEXT NOT NULL DEFAULT 'unknown',
    flag               TEXT,
    length_m           NUMERIC,
    width_m            NUMERIC,
    current_draught_m  NUMERIC,
    first_seen         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    enriched_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS positions (
    id           BIGSERIAL PRIMARY KEY,
    mmsi         BIGINT NOT NULL REFERENCES vessels(mmsi),
    latitude     DOUBLE PRECISION NOT NULL,
    longitude    DOUBLE PRECISION NOT NULL,
    sog          REAL,
    cog          REAL,
    heading      REAL,
    nav_status   SMALLINT,
    draught_m    NUMERIC,
    reported_at  TIMESTAMPTZ NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (mmsi, reported_at)
);

CREATE INDEX IF NOT EXISTS idx_positions_mmsi_time ON positions (mmsi, reported_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_reported  ON positions (reported_at DESC);
CREATE INDEX IF NOT EXISTS idx_vessels_subtype     ON vessels (subtype);
