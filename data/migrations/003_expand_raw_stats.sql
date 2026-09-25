-- DATA-04 v2 — extend raw player-match stats with approved variables
-- User-approved additions: tackles_won and goals_conceded.

ALTER TABLE player_match_raw_stats
    ADD COLUMN IF NOT EXISTS tackles_won INTEGER;

ALTER TABLE player_match_raw_stats
    ADD COLUMN IF NOT EXISTS goals_conceded INTEGER;

INSERT INTO schema_meta (schema_version, description)
SELECT '0.3.0', 'Add tackles_won and goals_conceded to raw player-match stats'
WHERE NOT EXISTS (
    SELECT 1 FROM schema_meta WHERE schema_version = '0.3.0'
);
