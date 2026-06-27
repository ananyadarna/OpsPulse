from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AlertEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str # 'latency_anomaly' | 'error_spike' | 'brute_force' | 'traffic_spike'
    severity: str # 'WARNING' | 'CRITICAL'
    message: str
    service: str
    metric_value: float
    threshold_value: float
    resolved: bool = False
    acknowledged: bool = False

class AlertRecord(AlertEvent):
    id: Optional[str] = Field(None, alias="_id")
