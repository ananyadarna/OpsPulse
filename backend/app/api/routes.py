from fastapi import APIRouter, Request, status, HTTPException
from typing import List, Union, Optional
import json
import logging
from app.models.log import LogPayload
from app.models.alert import AlertEvent
from app.services.log_parser import parse_log_line
from app.anomaly_detection.detector import AnomalyDetector
from app.database.mongodb import get_database

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/logs", status_code=status.HTTP_202_ACCEPTED)
async def ingest_logs(request: Request, payload: Union[dict, List[dict], str]):
    """
    Ingests logs (single JSON object, bulk list of JSON objects, or plain text string).
    Parses them, runs anomaly detection, saves alerts/logs to MongoDB, 
    and publishes alerts/logs to Redis for real-time WebSocket broadcasting.
    """
    redis_client = request.app.state.redis
    db = get_database()
    detector = AnomalyDetector(redis_client)

    # Standardize input into a list of strings/dicts
    raw_items = payload if isinstance(payload, list) else [payload]
    
    parsed_logs = []
    triggered_alerts = []

    for item in raw_items:
        # Convert to string if dict
        if isinstance(item, dict):
            line = json.dumps(item)
        else:
            line = str(item)

        log_payload = parse_log_line(line)
        if not log_payload:
            continue
        
        parsed_logs.append(log_payload)

    if not parsed_logs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Failed to parse any logs from payload."
        )

    # Process logs
    for log in parsed_logs:
        # 1. Run Anomaly Detection
        try:
            alerts = await detector.process_log(log)
            triggered_alerts.extend(alerts)
        except Exception as e:
            logger.error(f"Error executing anomaly detection on log: {e}")

        # 2. Persist parsed log to MongoDB
        log_dict = log.model_dump()
        log_dict["timestamp"] = log.timestamp.isoformat() # Convert to string for Mongo if needed, or keep as datetime
        await db.logs.insert_one(log_dict)

        # 3. Publish log to Redis channel for live streaming
        await redis_client.publish("opspulse:logs", log.model_dump_json())

    # Process triggered alerts
    for alert in triggered_alerts:
        # 1. Save alert to MongoDB
        alert_dict = alert.model_dump()
        await db.alerts.insert_one(alert_dict)
        
        # 2. Publish alert to Redis channel
        await redis_client.publish("opspulse:alerts", alert.model_dump_json())

    return {
        "status": "processed", 
        "logs_count": len(parsed_logs), 
        "alerts_count": len(triggered_alerts)
    }

@router.get("/alerts", response_model=List[dict])
async def get_alerts(service: Optional[str] = None, limit: int = 100):
    """
    Returns historical alerts from MongoDB, sorted by newest first.
    """
    db = get_database()
    query = {}
    if service:
        query["service"] = service

    cursor = db.alerts.find(query).sort("timestamp", -1).limit(limit)
    alerts = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        alerts.append(document)
        
    return alerts
