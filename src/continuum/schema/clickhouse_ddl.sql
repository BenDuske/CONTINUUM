-- CONTINUUM — ClickHouse Schema (Living Film Graph)
-- This is the production memory. Every action becomes an event.

-- ==========================================================================
-- Core event stream — the heart of CONTINUUM
-- ==========================================================================

CREATE DATABASE IF NOT EXISTS continuum;

CREATE TABLE IF NOT EXISTS continuum.production_events
(
    event_id       String,
    production_id  String,
    timestamp      DateTime64(3),
    event_type     LowCardinality(String),  -- SCRIPT_REVISION, TAKE_CAPTURED, etc.
    entity_type    LowCardinality(String),  -- scene, take, prop, character, location
    entity_id      String,
    data           String,                  -- JSON payload
    source         LowCardinality(String),  -- system, user, agent:<name>
    epistemic      LowCardinality(String),  -- observed, inferred, confirmed
    inserted_at    DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
ORDER BY (production_id, timestamp, event_type)
PARTITION BY toYYYYMM(timestamp);


-- ==========================================================================
-- Scenes — screenplay structure
-- ==========================================================================

CREATE TABLE IF NOT EXISTS continuum.scenes
(
    scene_id          String,
    production_id     String,
    scene_number      UInt32,
    slug              String,
    int_ext           LowCardinality(String),
    location_name     String,
    time_of_day       LowCardinality(String),
    description       String,
    characters        Array(String),
    props             Array(String),
    wardrobe_notes    Array(String),
    story_dependencies Array(String),
    revision          UInt32 DEFAULT 1,
    revision_color    LowCardinality(String) DEFAULT 'white',
    filmed            UInt8 DEFAULT 0,
    wrapped           UInt8 DEFAULT 0,
    updated_at        DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (production_id, scene_number);


-- ==========================================================================
-- Shots — planned coverage
-- ==========================================================================

CREATE TABLE IF NOT EXISTS continuum.shots
(
    shot_id        String,
    scene_id       String,
    production_id  String,
    shot_label     String,     -- e.g. '42A', '42B-CU'
    description    String,
    framing        LowCardinality(String),  -- CU, MCU, MS, WS, etc.
    captured       UInt8 DEFAULT 0,
    updated_at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (production_id, scene_id, shot_label);


-- ==========================================================================
-- Takes — captured footage
-- ==========================================================================

CREATE TABLE IF NOT EXISTS continuum.takes
(
    take_id                String,
    shot_id                String,
    scene_id               String,
    production_id          String,
    take_number            UInt32,
    camera                 LowCardinality(String) DEFAULT 'A',
    lens                   String,
    duration_seconds       Float64,
    rating                 LowCardinality(String) DEFAULT 'unrated',
    director_notes         String,
    script_supervisor_notes String,
    audio_clean            UInt8 DEFAULT 1,
    continuity_verified    UInt8 DEFAULT 0,
    captured_at            DateTime64(3),
    inserted_at            DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
ORDER BY (production_id, scene_id, shot_id, take_number);


-- ==========================================================================
-- Props — trackable production assets
-- ==========================================================================

CREATE TABLE IF NOT EXISTS continuum.props
(
    prop_id        String,
    production_id  String,
    name           String,
    state          String,       -- current physical state
    scenes         Array(String),
    notes          String,
    updated_at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (production_id, prop_id);


-- ==========================================================================
-- Wardrobe — costume tracking per character
-- ==========================================================================

CREATE TABLE IF NOT EXISTS continuum.wardrobe
(
    wardrobe_id    String,
    production_id  String,
    character      String,
    description    String,
    scenes         Array(String),
    state          String,
    updated_at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (production_id, character, wardrobe_id);


-- ==========================================================================
-- Continuity issues — detected problems
-- ==========================================================================

CREATE TABLE IF NOT EXISTS continuum.continuity_issues
(
    issue_id       String,
    production_id  String,
    scene_id       String,
    severity       LowCardinality(String),  -- critical, warning, info
    category       LowCardinality(String),  -- prop, wardrobe, dialogue, timeline
    description    String,
    evidence       Array(String),
    epistemic      LowCardinality(String),
    resolved       UInt8 DEFAULT 0,
    resolution     String,
    detected_at    DateTime64(3) DEFAULT now64(3),
    resolved_at    Nullable(DateTime64(3))
)
ENGINE = ReplacingMergeTree(detected_at)
ORDER BY (production_id, scene_id, issue_id);


-- ==========================================================================
-- Useful materialized views for agent queries
-- ==========================================================================

-- Scene coverage summary (how much of each scene has been captured)
CREATE TABLE IF NOT EXISTS continuum.scene_coverage_mv
(
    production_id   String,
    scene_id        String,
    planned_shots   UInt64,
    captured_shots  UInt64,
    total_takes     UInt64,
    good_takes      UInt64,
    select_takes    UInt64
)
ENGINE = SummingMergeTree()
ORDER BY (production_id, scene_id);

-- Production health dashboard metrics
CREATE TABLE IF NOT EXISTS continuum.production_health
(
    production_id       String,
    total_scenes        UInt64,
    scenes_filmed       UInt64,
    scenes_wrapped      UInt64,
    open_issues         UInt64,
    critical_issues     UInt64,
    total_takes         UInt64,
    calculated_at       DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(calculated_at)
ORDER BY (production_id);
