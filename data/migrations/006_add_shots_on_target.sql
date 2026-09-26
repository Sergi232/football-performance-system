-- DATA-04 v3 — approved raw shot-on-target count
-- shots_on_target is directly collectable in the FPS Collector and is available
-- in the inspected PannaData opta_player_stats export as ontargetScoringAtt.

ALTER TABLE player_match_raw_stats
    ADD COLUMN IF NOT EXISTS shots_on_target INTEGER;

INSERT INTO schema_meta (schema_version, description)
SELECT '0.6.0', 'Add approved shots_on_target to raw player-match stats'
WHERE NOT EXISTS (
    SELECT 1 FROM schema_meta WHERE schema_version = '0.6.0'
);
