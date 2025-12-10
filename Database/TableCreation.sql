-- CREATE TABLE ingestion_log (
--     ingestion_id   UUID PRIMARY KEY,
--     device_id      UUID NOT NULL,
--     raw_json       JSONB NOT NULL,
--     received_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
--     process_status VARCHAR(20) NOT NULL CHECK (process_status IN ('pending', 'success', 'failure')),
--     error_message  TEXT
-- );

CREATE TABLE location (
    location_id UUID PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    area_description TEXT,
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6)
);

CREATE TABLE device (
    device_id UUID PRIMARY KEY,
    device_name VARCHAR(100) NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    location_id UUID REFERENCES location(location_id),
    status VARCHAR(20) NOT NULL DEFAULT 'active' , -- e.g., 'active', 'offline', 'error'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE image (
    image_id UUID PRIMARY KEY,
    ingestion_id UUID REFERENCES ingestion_log(ingestion_id),
    capture_timestamp TIMESTAMPTZ,
    image_path VARCHAR(255) NOT NULL, -- URL to S3/GCS
    resolution_x INTEGER,
    resolution_y INTEGER,
    checksum VARCHAR(64) UNIQUE NOT NULL, -- SHA256 or similar
    format VARCHAR(10),
    confirmed_class VARCHAR(50) NULL -- Manual confirmation field
);

CREATE TABLE prediction (
    prediction_id UUID PRIMARY KEY,
    image_id UUID REFERENCES image(image_id),
    predicted_class VARCHAR(50) NOT NULL,
    probability NUMERIC(5, 4) NOT NULL,
    predicted_json JSONB,
    predicted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE etl_job_log (
    etl_id UUID PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL, -- 'running', 'success', 'failure'
    total_records_processed INTEGER
);

-- A. LOCATION
INSERT INTO location (location_id, site_name, area_description, latitude, longitude)
VALUES (
    'a1b2c3d4-0000-4000-8000-000000000001', 
    'Recycling Station 1', 
    'Loading dock near main warehouse', 
    40.256789, 
    -74.512345
);


-- B. DEVICE
INSERT INTO device (device_id, device_name, device_type, location_id, status, created_at, updated_at)
VALUES (
    'a1b2c3d4-0000-4000-8000-000000000002', 
    'Pi_Cam_005', 
    'Raspberry Pi Camera', 
    'a1b2c3d4-0000-4000-8000-000000000001', -- FK: location_id
    'active', 
    '2025-12-09 10:00:00 EST', 
    '2025-12-09 15:30:00 EST'
);


-- C. IMAGE
-- NOTE: Requires an ingestion_log entry to exist for 'a1b2c3d4-0000-4000-8000-000000000003'
INSERT INTO image (image_id, ingestion_id, capture_timestamp, image_path, resolution_x, resolution_y, checksum, format, confirmed_class)
VALUES (
    'a1b2c3d4-0000-4000-8000-000000000004', 
    '4bb1e26c-b3cb-4ef7-9ec6-ef54b7d956b7', -- FK: ingestion_log_id
    '2025-12-09 15:35:00 EST', 
    's3://waste-data-bucket/raw/img_0004.jpg', 
    224, 
    224, 
    '0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2a3b4c5d6e7f8', -- Unique hash
    'jpeg', 
    NULL
);


-- D. PREDICTION
INSERT INTO prediction (prediction_id, image_id, predicted_class, probability, predicted_json, predicted_at)
VALUES (
    'a1b2c3d4-0000-4000-8000-000000000005', 
    'a1b2c3d4-0000-4000-8000-000000000004', -- FK: image_id
    'plastic', 
    0.9850, 
    '{"top_3": [{"class": "plastic", "prob": 0.985}, {"class": "metal", "prob": 0.010}]}', 
    '2025-12-09 15:35:15 EST'
);


-- E. ETL_JOB_LOG
INSERT INTO etl_job_log (etl_id, job_name, started_at, ended_at, status, total_records_processed)
VALUES (
    'a1b2c3d4-0000-4000-8000-000000000006', 
    'Daily_Image_Ingest_Cleanup', 
    '2025-12-09 01:00:00 EST', 
    '2025-12-09 01:05:30 EST', 
    'success', 
    4500
);





SELECT * FROM device;
SELECT * FROM location;
SELECT * FROM etl_job_log;
SELECT * FROM ingestion_log;
SELECT * FROM image;
SELECT * FROM prediction;





-- CREATE TABLE ingestion_log (
--     ingestion_id   UUID PRIMARY KEY,
--     device_id      UUID NOT NULL,
--     raw_json       JSONB NOT NULL,
--     received_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
--     process_status VARCHAR(20) NOT NULL CHECK (process_status IN ('pending', 'success', 'failure')),
--     error_message  TEXT
-- );

ALTER TABLE ingestion_log
ADD COLUMN predicted_class VARCHAR(50);

ALTER TABLE ingestion_log
ADD COLUMN confidence DOUBLE PRECISION;

SELECT *
FROM ingestion_log;

