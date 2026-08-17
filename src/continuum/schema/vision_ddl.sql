-- CONTINUUM — Vision Subsystem Schema
-- Tables that hold observations produced by Google Video Intelligence,
-- Vertex AI multimodal Gemini, and Imagen 3 embeddings.
--
-- Every row carries provenance (source model, confidence, epistemic layer)
-- so agents can reason about *how* something is known — not just what.

-- ==========================================================================
-- Take media assets — the raw video/image inputs the vision layer analyzes
-- ==========================================================================
CREATE TABLE IF NOT EXISTS continuum.take_media_assets
(
    asset_id        String,
    production_id   String,
    take_id         String,
    scene_id        String,
    gcs_uri         String,                   -- gs://bucket/path.mp4
    mime_type       LowCardinality(String),   -- video/mp4, image/jpeg
    duration_ms     UInt32,                   -- 0 for stills
    width           UInt32,
    height          UInt32,
    fps             Float32,
    checksum_sha256 String,
    ingested_at     DateTime64(3) DEFAULT now64(3),
    version         UInt64 DEFAULT toUnixTimestamp64Milli(now64(3))
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (production_id, take_id, asset_id);


-- ==========================================================================
-- Vision jobs — async operation tracking (Video Intelligence is long-running)
-- ==========================================================================
CREATE TABLE IF NOT EXISTS continuum.vision_jobs
(
    job_id          String,
    production_id   String,
    asset_id        String,
    take_id         String,
    engine          LowCardinality(String),   -- video_intelligence, gemini_multimodal, imagen_embed
    features        Array(LowCardinality(String)),  -- SHOT_CHANGE_DETECTION, OBJECT_TRACKING, ...
    state           LowCardinality(String),   -- pending, running, succeeded, failed
    operation_name  String,                   -- Google long-running operation ref
    started_at      DateTime64(3),
    finished_at     Nullable(DateTime64(3)),
    error           String,
    version         UInt64 DEFAULT toUnixTimestamp64Milli(now64(3))
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (production_id, job_id);


-- ==========================================================================
-- Frame observations — the wide, denormalized fact table
-- One row per (asset, feature, time_ms, entity). Agents JOIN into this.
-- Includes provenance fields on every row (source_model, confidence, epistemic).
-- ==========================================================================
CREATE TABLE IF NOT EXISTS continuum.frame_observations
(
    obs_id          String,
    production_id   String,
    take_id         String,
    asset_id        String,
    scene_id        String,
    feature         LowCardinality(String),   -- shot, object, face, person, label, text, speech, safety
    ts_ms           UInt64,                   -- observation timestamp within the asset
    end_ms          UInt64,                   -- for interval features (shots, speech segments)
    entity_kind     LowCardinality(String),   -- prop, actor, label, transcript, ocr_text, safety_flag
    entity_id       String,                   -- e.g. prop:cam-p14, actor:sarah, label:apartment
    entity_label    String,                   -- human-readable
    payload         String,                   -- JSON: bboxes, tracks, transcript segments, VI raw
    source_model    LowCardinality(String),   -- videointelligence-v1p3beta1, gemini-3.5-flash, imagen-3
    confidence      Float32,                  -- 0..1
    epistemic       LowCardinality(String),   -- observed, inferred, confirmed
    inserted_at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
ORDER BY (production_id, take_id, feature, ts_ms)
PARTITION BY toYYYYMM(inserted_at);


-- ==========================================================================
-- Take dialogue — speech transcription output, kept separate for text search
-- ==========================================================================
CREATE TABLE IF NOT EXISTS continuum.take_dialogue
(
    obs_id          String,
    production_id   String,
    take_id         String,
    asset_id        String,
    scene_id        String,
    segment_index   UInt32,
    ts_ms           UInt64,
    end_ms          UInt64,
    speaker_tag     Int32,                    -- VI speaker diarization; -1 if unknown
    transcript      String,
    confidence      Float32,
    source_model    LowCardinality(String),
    epistemic       LowCardinality(String),
    inserted_at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
ORDER BY (production_id, take_id, segment_index);


-- ==========================================================================
-- Frame embeddings — Imagen 3 image embeddings for similarity search
-- ==========================================================================
CREATE TABLE IF NOT EXISTS continuum.frame_embeddings
(
    obs_id          String,
    production_id   String,
    take_id         String,
    asset_id        String,
    ts_ms           UInt64,
    embedding       Array(Float32),           -- 1408-dim Imagen 3 multimodal embedding
    source_model    LowCardinality(String),
    inserted_at     DateTime64(3) DEFAULT now64(3)
)
ENGINE = MergeTree()
ORDER BY (production_id, take_id, ts_ms);


-- ==========================================================================
-- Vision verdicts — structured Gemini multimodal conclusions
-- Feeds directly into the CONTINUITY agent's continuity_issues pipeline.
-- ==========================================================================
CREATE TABLE IF NOT EXISTS continuum.vision_verdicts
(
    verdict_id      String,
    production_id   String,
    take_id         String,
    asset_id        String,
    scene_id        String,
    question        String,                   -- e.g. "Does Camera P-14 show damage?"
    verdict         LowCardinality(String),   -- yes, no, unclear
    evidence        String,                   -- JSON: keyframe refs, ts_ms, reasoning
    confidence      Float32,
    source_model    LowCardinality(String),   -- gemini-3.5-flash
    epistemic       LowCardinality(String),   -- inferred (until SKEPTIC confirms)
    inserted_at     DateTime64(3) DEFAULT now64(3),
    version         UInt64 DEFAULT toUnixTimestamp64Milli(now64(3))
)
ENGINE = ReplacingMergeTree(version)
ORDER BY (production_id, take_id, verdict_id);
