-- GPS-01 normalized multi-provider contract

ALTER TABLE gps_imports ADD COLUMN IF NOT EXISTS source_format VARCHAR;
ALTER TABLE gps_imports ADD COLUMN IF NOT EXISTS sample_rate_hz DOUBLE;
ALTER TABLE gps_imports ADD COLUMN IF NOT EXISTS time_basis VARCHAR;
ALTER TABLE gps_imports ADD COLUMN IF NOT EXISTS coordinate_system VARCHAR;
ALTER TABLE gps_imports ADD COLUMN IF NOT EXISTS distance_mode VARCHAR;
ALTER TABLE gps_imports ADD COLUMN IF NOT EXISTS source_units JSON;
ALTER TABLE gps_imports ADD COLUMN IF NOT EXISTS mapping_config JSON;
ALTER TABLE gps_imports ADD COLUMN IF NOT EXISTS notes VARCHAR;

CREATE TABLE IF NOT EXISTS gps_player_map (
    gps_import_id VARCHAR NOT NULL,
    source_player_key VARCHAR NOT NULL,
    source_player_name VARCHAR,
    player_id VARCHAR NOT NULL,
    mapping_method VARCHAR NOT NULL,
    mapping_confidence DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (gps_import_id, source_player_key),
    FOREIGN KEY (gps_import_id) REFERENCES gps_imports(gps_import_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

ALTER TABLE gps_observations ADD COLUMN IF NOT EXISTS source_row_number BIGINT;
ALTER TABLE gps_observations ADD COLUMN IF NOT EXISTS quality_flags JSON;

INSERT INTO schema_meta (schema_version, description)
SELECT '0.4.0', 'GPS multi-provider normalization contract'
WHERE NOT EXISTS (
    SELECT 1 FROM schema_meta WHERE schema_version = '0.4.0'
);
