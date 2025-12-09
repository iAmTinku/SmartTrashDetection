CREATE TABLE ingestion_log (
    ingestion_id   UUID PRIMARY KEY,
    device_id      UUID NOT NULL,
    raw_json       JSONB NOT NULL,
    received_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    process_status VARCHAR(20) NOT NULL CHECK (process_status IN ('pending', 'success', 'failure')),
    error_message  TEXT
);

SELECT *
FROM ingestion_log;