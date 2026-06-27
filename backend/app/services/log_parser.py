import json
import re
from datetime import datetime
from typing import Optional
from app.models.log import LogPayload

# Sample unstructured string regex: [2026-06-27T12:00:00.123Z] ERROR service /endpoint status latency_ms ip - message
UNSTRUCTURED_LOG_REGEX = re.compile(
    r'^\[(?P<timestamp>[^\]]+)\]\s+(?P<level>\w+)\s+(?P<service>[\w\-]+)\s+(?P<endpoint>\S+)\s+(?P<status_code>\d+)\s+(?P<response_time>\d+(?:\.\d+)?)(?:ms)?\s+(?P<ip>\S+)\s+-\s+(?P<message>.*)$'
)

def parse_log_line(line: str) -> Optional[LogPayload]:
    """
    Parses a log line. First attempts JSON parsing, and falls back to Regex parsing for custom text logs.
    Returns None if parsing fails.
    """
    line = line.strip()
    if not line:
        return None

    # Try JSON parsing
    if line.startswith('{') and line.endswith('}'):
        try:
            return LogPayload.model_validate_json(line)
        except Exception:
            # Fall through to text regex if JSON validation failed but we want to try text matching
            pass

    # Try Regex fallback
    match = UNSTRUCTURED_LOG_REGEX.match(line)
    if match:
        try:
            data = match.groupdict()
            # Clean up timestamp
            ts_str = data['timestamp']
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except ValueError:
                ts = datetime.utcnow()

            return LogPayload(
                timestamp=ts,
                level=data['level'].upper(),
                service=data['service'],
                endpoint=data['endpoint'],
                status_code=int(data['status_code']),
                response_time_ms=float(data['response_time']),
                ip=data['ip'],
                message=data['message']
            )
        except Exception:
            return None

    return None
