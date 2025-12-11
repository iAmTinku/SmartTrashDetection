import logging
from datetime import datetime
import psycopg2
import json
import uuid
from typing import Any, List, Optional
import numpy as np



logger = logging.getLogger(__name__)


def insert_request_log_rejects(cursor: any, request_blob: any):
    try:
        # request_id (PK) and log_timestamp are SERIAL/DEFAULT
        cursor.execute("""
            INSERT INTO request_log_rejects (
                request_blob
            )
            VALUES (%s)
        """, (json.dumps(request_blob),))
        logger.warning(f"Rejected request logged - query")
    except psycopg2.Error as e:
        logger.error(f"Error inserting request_log_rejects: {e} - query")
        raise

def query_request_log_by_pk(cursor: any, request_id: int):
    try:
        cursor.execute("""
            SELECT 
                request_id, request_blob, log_timestamp
            FROM 
                request_log_rejects
            WHERE 
                request_id = %s;
        """, (request_id,))
        
        record = cursor.fetchone()
        return record
    except psycopg2.Error as e:
        logger.error(f"Error querying request_log_rejects {request_id}: {e}")
        raise





def insert_device(cursor: any, device_id: str, device_name: str, device_type: str):
    try:
        cursor.execute("""
            INSERT INTO device (
                device_id,
                device_name,
                device_type
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (device_id) DO NOTHING;
        """, (
            device_id,
            device_name,
            device_type
        ))
        logger.info(f"Device {device_id} inserted - query")
    except psycopg2.Error as e:
        logger.error(f"Error inserting device {device_id}: {e}")
        raise

def query_device_by_pk(cursor: any, device_id: str):
    try:
        cursor.execute("""
            SELECT 
                device_id, device_name, device_type
            FROM 
                device
            WHERE 
                device_id = %s;
        """, (device_id,))
        
        record = cursor.fetchone()
        return record
    except psycopg2.Error as e:
        logger.error(f"Error querying device {device_id}: {e} - query")
        raise



def insert_image_data(cursor: any, ingestion_id: str, device_id: str, image_data: bytes):
    try:
        # timestamp, created_date, created_by are DEFAULT
        cursor.execute("""
            INSERT INTO image_data (
                ingestion_id,
                device_id,
                image_data
            )
            VALUES (%s, %s, %s);
        """, (
            str(ingestion_id),
            device_id,
            image_data
        ))
        logger.info(f"Raw image data for ingestion {ingestion_id} inserted - query")
    except psycopg2.Error as e:
        logger.error(f"Error inserting image_data {ingestion_id}: {e} - query")
        raise

def query_image_data_by_pk(cursor: any, ingestion_id: str) :
    try:
        cursor.execute("""
            SELECT 
                ingestion_id, device_id, timestamp, image_data, created_date, created_by
            FROM 
                image_data
            WHERE 
                ingestion_id = %s;
        """, (ingestion_id,))
        
        record = cursor.fetchone()
        return record
    except psycopg2.Error as e:
        logger.error(f"Error querying image_data {ingestion_id}: {e} - query")
        raise






def insert_image_metadata(cursor: any, image_id: str, ingestion_id: str, image_location: str, 
                          predicted_value: str, predicted_weightage: float, predicted_probabilities_all: List[float], 
                          actual_value: Optional[str] = None, modified_date: Optional[datetime] = None, modified_by: str = 'system'):
    try:
        # created_date, created_by are DEFAULT
        cursor.execute("""
            INSERT INTO image (
                image_id, ingestion_id, image_location, predicted_value, 
                predicted_weightage, predicted_probabilities_all, actual_value, 
                modified_date, modified_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            str(image_id),
            str(ingestion_id),
            image_location,
            predicted_value,
            predicted_weightage,
            predicted_probabilities_all,
            actual_value,
            modified_date,
            modified_by
        ))
        logger.info(f"Processed image metadata {image_id} inserted - query")
    except psycopg2.Error as e:
        logger.error(f"Error inserting image metadata {image_id}: {e}")
        raise

def query_image_by_pk(cursor: any, image_id: str):
    try:
        cursor.execute("""
            SELECT 
                image_id, ingestion_id, image_location, predicted_value, predicted_weightage, 
                predicted_probabilities_all, actual_value, created_date, created_by, 
                modified_date, modified_by
            FROM 
                image
            WHERE 
                image_id = %s;
        """, (image_id,))
        
        record = cursor.fetchone()
        return record
    except psycopg2.Error as e:
        logger.error(f"Error querying image metadata {image_id}: {e}")
        raise