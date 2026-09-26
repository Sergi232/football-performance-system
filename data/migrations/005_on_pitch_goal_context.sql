-- PERF-17 on-pitch goal context

CREATE TABLE IF NOT EXISTS player_match_on_pitch_context (
    match_id VARCHAR NOT NULL,
    team_id VARCHAR NOT NULL,
    player_id VARCHAR NOT NULL,
    start_second INTEGER NOT NULL,
    end_second INTEGER,
    start_source VARCHAR NOT NULL,
    end_source VARCHAR,
    timing_precision VARCHAR NOT NULL,
    goals_for_on_pitch INTEGER NOT NULL,
    goals_against_on_pitch INTEGER NOT NULL,
    goal_diff_on_pitch INTEGER NOT NULL,
    team_goals_for INTEGER NOT NULL,
    team_goals_against INTEGER NOT NULL,
    boundary_ambiguity_goals INTEGER NOT NULL DEFAULT 0,
    context_version VARCHAR NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (match_id, player_id, context_version),
    FOREIGN KEY (match_id) REFERENCES matches(match_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

INSERT INTO schema_meta (schema_version, description)
SELECT '0.5.0', 'Player-match on-pitch goal context'
WHERE NOT EXISTS (
    SELECT 1 FROM schema_meta WHERE schema_version = '0.5.0'
);
