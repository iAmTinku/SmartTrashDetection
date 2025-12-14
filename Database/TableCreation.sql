CREATE TABLE request_log_rejects (
    request_id SERIAL PRIMARY KEY,
    request_blob JSONB, 
    log_timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

 CREATE TABLE IF NOT EXISTS device (
      device_id VARCHAR(255) PRIMARY KEY,
      device_name VARCHAR(255) NOT NULL,
      device_type VARCHAR(255) NOT NULL
  );

  CREATE TABLE IF NOT EXISTS image_data (
      ingestion_id UUID PRIMARY KEY,
      device_id VARCHAR(255) NOT NULL,
      timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      image_data BYTEA,
      created_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      created_by VARCHAR(255) DEFAULT 'system',
      CONSTRAINT fk_device_id_data
        FOREIGN KEY (device_id)
        REFERENCES device (device_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
  );

  CREATE TABLE IF NOT EXISTS image (
      image_id UUID PRIMARY KEY,
      ingestion_id UUID,
      image_location VARCHAR(255) NOT NULL,
	  predicted_value VARCHAR(255),
      predicted_weightage FLOAT,
	  predicted_probabilities_all DOUBLE PRECISION[],
	  actual_value VARCHAR(255),
      created_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      created_by VARCHAR(255) DEFAULT 'system', 
      modified_date TIMESTAMP WITHOUT TIME ZONE,
      modified_by VARCHAR(255) DEFAULT 'system',
      CONSTRAINT fk_ingestion
        FOREIGN KEY (ingestion_id)
        REFERENCES image_data (ingestion_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
  );


INSERT INTO device (device_id, device_name, device_type)
VALUES ('CAM-439-EAST', 'Assembly Line Camera 1', 'Image Capture');


INSERT INTO image_data (ingestion_id, device_id, timestamp, image_data, created_by)
VALUES ('43a5e9b7-6c2d-4f1e-8a0b-9c3f4d5e6f7a', 'CAM-439-EAST', CURRENT_TIMESTAMP, E'\\x89504e470d0a1a0a', 'ingestion_script_v2.1');

INSERT INTO image (image_id, ingestion_id, image_location, predicted_value, predicted_weightage, predicted_probabilities_all, actual_value, created_by)
VALUES (
    '22c1b4d0-a7e8-4b9c-c0d1-e2f3a4b5c6d7',
    '43a5e9b7-6c2d-4f1e-8a0b-9c3f4d5e6f7a',
    's3://img-bucket/cam439/2025/22c1b4d0.jpg',
    'Defective_Part',
    0.985,
    '{0.985, 0.010, 0.005}',
    NULL,
    'Predictor'
);

INSERT INTO request_log_rejects (request_blob)
VALUES ('{"error_code": 400, "message": "Invalid device ID format.", "received_payload": {"dev_id": "bad_format", "data": "..."}}');




SELECT * FROM request_log_rejects;
SELECT * FROM device;
SELECT * FROM image_data;
SELECT * FROM image;