from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class LogPayload(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str
    service: str
    endpoint: str
    status_code: int
    response_time_ms: float
    ip: str
    message: str

class LogRecord(LogPayload):
    id: Optional[str] = Field(None, alias="_id")
