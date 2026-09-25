-- DATA-04 — normalized raw player-match aggregate layer
-- Provider-specific values are mapped into stable logical columns but remain raw:
-- source NULLs are preserved and no derived rates/features are stored here.

CREATE TABLE IF NOT EXISTS player_match_raw_stats (
    match_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    player_id VARCHAR NOT NULL,
    source_type VARCHAR NOT NULL,
    source_match_id VARCHAR,
    source_player_id VARCHAR,
    source_minutes DOUBLE,

    passes_total INTEGER,
    passes_completed INTEGER,
    assists INTEGER,
    long_balls_total INTEGER,
    long_balls_completed INTEGER,
    crosses_total INTEGER,
    crosses_completed INTEGER,
    dribbles_total INTEGER,
    dribbles_won INTEGER,
    turnovers INTEGER,
    dispossessed INTEGER,
    shots_total INTEGER,
    shots_blocked INTEGER,
    goals INTEGER,
    tackles_total INTEGER,
    interceptions INTEGER,
    blocked_passes INTEGER,
    clearances INTEGER,
    fouls_committed INTEGER,
    fouls_received INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,
    penalties_conceded INTEGER,
    penalties_won INTEGER,
    saves INTEGER,

    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (match_id, player_id, source_type),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_stats_team_match
    ON player_match_raw_stats(team_id, match_id);

INSERT INTO schema_meta (schema_version, description)
SELECT '0.2.0', 'Add raw player-match aggregate stats layer'
WHERE NOT EXISTS (
    SELECT 1 FROM schema_meta WHERE schema_version = '0.2.0'
);
