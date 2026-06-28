import uuid
import time
import numpy as np
import logging
from typing import Optional, List, Dict
from redis.asyncio import Redis
from app.config import settings
from app.models.log import LogPayload
from app.models.alert import AlertEvent

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.min_samples = settings.DETECTION_MIN_SAMPLES
        self.z_threshold = settings.LATENCY_Z_SCORE_THRESHOLD
        self.error_spike_threshold = settings.ERROR_SPIKE_THRESHOLD
        self.brute_force_threshold = settings.BRUTE_FORCE_THRESHOLD

    async def process_log(self, log: LogPayload) -> List[AlertEvent]:
        """
        Processes a log line:
        1. Records metrics to Redis (latencies, status codes, login attempts).
        2. Prunes old metrics.
        3. Evaluates detection rules and returns any triggered Alerts.
        """
        # Use the log's own timestamp as the time anchor. This ensures
        # event-time consistency and makes unit testing deterministic.
        now = log.timestamp.timestamp()
        log_ts = now
        
        alerts: List[AlertEvent] = []

        # 1. Record metrics
        uid = str(uuid.uuid4())
        
        # Add latency
        latency_key = f"opspulse:latency:{log.service}"
        await self.redis.zadd(latency_key, {f"{log.response_time_ms}:{uid}": log_ts})
        
        # Add request status (for error rate and traffic volume)
        request_key = f"opspulse:requests:{log.service}"
        is_error = 1 if (log.status_code >= 500 or log.level == "ERROR") else 0
        await self.redis.zadd(request_key, {f"{is_error}:{uid}": log_ts})

        # Prune old data outside window
        prune_ts = now - settings.DETECTION_WINDOW_SECONDS
        await self.redis.zremrangebyscore(latency_key, "-inf", prune_ts)
        await self.redis.zremrangebyscore(request_key, "-inf", prune_ts)

        # 2. Run Detectors
        # A. Latency Z-Score Anomaly
        latency_alert = await self._detect_latency_anomaly(log, now)
        if latency_alert:
            alerts.append(latency_alert)

        # B. Error Spike Detection
        error_alert = await self._detect_error_spike(log, now)
        if error_alert:
            alerts.append(error_alert)

        # C. Brute Force Detection
        brute_alert = await self._detect_brute_force(log, now)
        if brute_alert:
            alerts.append(brute_alert)

        return alerts

    async def _detect_latency_anomaly(self, log: LogPayload, now: float) -> Optional[AlertEvent]:
        latency_key = f"opspulse:latency:{log.service}"
        start_ts = now - settings.DETECTION_WINDOW_SECONDS

        # Get all latencies in the rolling window
        members = await self.redis.zrangebyscore(latency_key, start_ts, "+inf")
        if len(members) < self.min_samples:
            return None

        # Extract numerical latencies
        latencies = []
        for m in members:
            try:
                # members are stored as "latency:uuid"
                latencies.append(float(m.decode().split(':')[0]))
            except (ValueError, IndexError):
                continue

        if len(latencies) < self.min_samples:
            return None

        latencies_arr = np.array(latencies)
        mean_val = np.mean(latencies_arr)
        std_val = np.std(latencies_arr)

        if std_val == 0:
            return None

        # Calculate Z-score for the current log response time
        z_score = (log.response_time_ms - mean_val) / std_val

        if z_score > self.z_threshold:
            logger.warning(f"Latency anomaly detected in {log.service}: {log.response_time_ms}ms (Z-score: {z_score:.2f})")
            return AlertEvent(
                type="latency_anomaly",
                severity="WARNING" if z_score < 5.0 else "CRITICAL",
                message=f"Latency spike in {log.service} on {log.endpoint}. Current: {log.response_time_ms:.1f}ms. Rolling Mean: {mean_val:.1f}ms (StdDev: {std_val:.1f}ms). Z-score: {z_score:.2f}.",
                service=log.service,
                metric_value=log.response_time_ms,
                threshold_value=mean_val + (self.z_threshold * std_val)
            )

        return None

    async def _detect_error_spike(self, log: LogPayload, now: float) -> Optional[AlertEvent]:
        request_key = f"opspulse:requests:{log.service}"
        
        # 1-minute window for current error rate
        current_start = now - settings.ERROR_SPIKE_WINDOW_SECONDS
        current_members = await self.redis.zrangebyscore(request_key, current_start, "+inf")
        
        # 5-minute rolling window for baseline
        baseline_start = now - settings.DETECTION_WINDOW_SECONDS
        baseline_members = await self.redis.zrangebyscore(request_key, baseline_start, "+inf")

        if len(baseline_members) < 20: # Require a reasonable base traffic volume
            return None

        def calculate_error_rate(members_list: List[bytes]) -> tuple[int, float]:
            total = len(members_list)
            if total == 0:
                return 0, 0.0
            errors = 0
            for m in members_list:
                try:
                    # members are stored as "is_error:uuid"
                    if int(m.decode().split(':')[0]) == 1:
                        errors += 1
                except (ValueError, IndexError):
                    continue
            return total, errors / total

        curr_total, curr_error_rate = calculate_error_rate(current_members)
        base_total, base_error_rate = calculate_error_rate(baseline_members)

        # Trigger if current error rate is significantly higher than baseline
        # Avoid triggering alerts for 1 error on 1 request (require min requests)
        if curr_total >= 5 and curr_error_rate > 0.05:
            # If baseline has 0 errors, set baseline to 1% to avoid division by zero
            adjusted_base_rate = max(base_error_rate, 0.01)
            increase_factor = curr_error_rate / adjusted_base_rate

            if increase_factor > self.error_spike_threshold:
                logger.warning(f"Error spike detected in {log.service}: Current error rate: {curr_error_rate*100:.1f}%")
                return AlertEvent(
                    type="error_spike",
                    severity="CRITICAL" if curr_error_rate > 0.20 else "WARNING",
                    message=f"Error rate surge in {log.service}. Current: {curr_error_rate*100:.1f}% (over 1 min). Baseline: {base_error_rate*100:.1f}% (over 5 min). Increase: {increase_factor:.1f}x.",
                    service=log.service,
                    metric_value=curr_error_rate * 100.0,
                    threshold_value=adjusted_base_rate * self.error_spike_threshold * 100.0
                )

        return None

    async def _detect_brute_force(self, log: LogPayload, now: float) -> Optional[AlertEvent]:
        # Define brute-force sensitive endpoints
        is_auth_endpoint = any(kw in log.endpoint.lower() for kw in ["login", "auth", "signin", "register"])
        is_failure = log.status_code in [401, 403] or "fail" in log.message.lower()

        if not (is_auth_endpoint and is_failure):
            return None

        brute_key = f"opspulse:brute_force:{log.ip}"
        uid = str(uuid.uuid4())
        
        # Log this failure timestamp in a ZSET
        await self.redis.zadd(brute_key, {uid: now})
        
        # Prune old logs outside the brute force window
        prune_ts = now - settings.BRUTE_FORCE_WINDOW_SECONDS
        await self.redis.zremrangebyscore(brute_key, "-inf", prune_ts)
        
        # Set expiration to ensure key doesn't live indefinitely in Redis
        await self.redis.expire(brute_key, settings.BRUTE_FORCE_WINDOW_SECONDS * 2)

        # Count failures in window
        failure_count = await self.redis.zcard(brute_key)

        if failure_count >= self.brute_force_threshold:
            logger.warning(f"Brute force attempt detected from IP {log.ip} (failures: {failure_count})")
            return AlertEvent(
                type="brute_force",
                severity="CRITICAL",
                message=f"Brute-force login pattern detected from IP {log.ip}. Detected {failure_count} authentication failures within {settings.BRUTE_FORCE_WINDOW_SECONDS} seconds.",
                service=log.service,
                metric_value=float(failure_count),
                threshold_value=float(self.brute_force_threshold)
            )

        return None
