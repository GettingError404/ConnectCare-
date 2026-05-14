-- PostgreSQL + TimescaleDB schema for healthcare time-series backend

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS timescaledb;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'metric_type_enum') THEN
        CREATE TYPE metric_type_enum AS ENUM (
            'steps',
            'heart_rate',
            'sleep',
            'calories',
            'spo2',
            'respiratory_rate',
            'body_temperature'
        );
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_identifier VARCHAR(128) NOT NULL,
    device_type VARCHAR(64) NOT NULL,
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_devices_device_identifier UNIQUE (device_identifier)
);

CREATE TABLE IF NOT EXISTS health_vitals (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    metric_type metric_type_enum NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(20) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_health_vitals PRIMARY KEY (id, recorded_at),
    CONSTRAINT uq_health_vitals_device_metric_recorded_at UNIQUE (device_id, metric_type, recorded_at)
);

SELECT create_hypertable('health_vitals', 'recorded_at', if_not_exists => TRUE, migrate_data => TRUE);

CREATE INDEX IF NOT EXISTS ix_health_vitals_user_recorded_at_desc
    ON health_vitals (user_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS ix_health_vitals_metric_type
    ON health_vitals (metric_type);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_set_updated_at ON users;
CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_devices_set_updated_at ON devices;
CREATE TRIGGER trg_devices_set_updated_at
BEFORE UPDATE ON devices
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_health_vitals_set_updated_at ON health_vitals;
CREATE TRIGGER trg_health_vitals_set_updated_at
BEFORE UPDATE ON health_vitals
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
