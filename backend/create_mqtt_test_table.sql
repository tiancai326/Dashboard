CREATE TABLE IF NOT EXISTS `Real` (
    id BIGINT NOT NULL AUTO_INCREMENT,
    timestamp DATETIME NOT NULL,
    zone_id VARCHAR(20) NOT NULL,
    air_temp FLOAT,
    air_humidity FLOAT,
    light_intensity INT,
    soil_temp FLOAT,
    soil_humidity FLOAT,
    ec FLOAT,
    ph FLOAT,
    n FLOAT,
    p FLOAT,
    k FLOAT,
    PRIMARY KEY (id),
    KEY idx_timestamp (timestamp),
    KEY idx_zone_id (zone_id),
    KEY idx_zone_timestamp (zone_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `predictions` (
    id BIGINT NOT NULL AUTO_INCREMENT,
    run_timestamp DATETIME NOT NULL,
    predict_time DATETIME NOT NULL,
    zone_id VARCHAR(20) NOT NULL,
    soil_temp_pred FLOAT NOT NULL,
    soil_humidity_pred FLOAT NOT NULL,
    ec_pred FLOAT NOT NULL,
    weather_temp FLOAT,
    weather_humidity FLOAT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_predict_time (predict_time),
    KEY idx_zone_predict (zone_id, predict_time),
    KEY idx_run_ts (run_timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
