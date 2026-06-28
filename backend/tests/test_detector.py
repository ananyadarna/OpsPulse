import pytest
from datetime import datetime, timedelta
from app.anomaly_detection.detector import AnomalyDetector
from app.models.log import LogPayload

class MockRedis:
    def __init__(self):
        self.data = {} # key -> list of (score, member)

    async def zadd(self, key, mapping):
        if key not in self.data:
            self.data[key] = []
        for member, score in mapping.items():
            val = member.encode() if isinstance(member, str) else member
            self.data[key].append((score, val))
        # Keep sorted by score
        self.data[key].sort(key=lambda x: x[0])
        return len(mapping)

    async def zremrangebyscore(self, key, min_val, max_val):
        if key not in self.data:
            return 0
        original_len = len(self.data[key])

        # Convert boundaries to float
        f_min = -float('inf') if min_val == "-inf" else float(min_val)
        f_max = float('inf') if max_val == "+inf" else float(max_val)

        self.data[key] = [x for x in self.data[key] if not (f_min <= x[0] <= f_max)]
        return original_len - len(self.data[key])

    async def zrangebyscore(self, key, min_val, max_val):
        if key not in self.data:
            return []
        f_min = -float('inf') if min_val == "-inf" else float(min_val)
        f_max = float('inf') if max_val == "+inf" else float(max_val)

        return [x[1] for x in self.data[key] if f_min <= x[0] <= f_max]

    async def zcard(self, key):
        if key not in self.data:
            return 0
        return len(self.data[key])

    async def expire(self, key, ttl):
        return True


@pytest.mark.asyncio
async def test_no_anomaly_on_baseline():
    """
    Ensure normal baseline logs do not trigger latency anomalies.
    """
    redis_mock = MockRedis()
    detector = AnomalyDetector(redis_mock)

    # Ingest 15 baseline logs with normal latency around 100ms
    base_time = datetime.utcnow()
    for i in range(15):
        log = LogPayload(
            timestamp=base_time + timedelta(seconds=i),
            level="INFO",
            service="test-service",
            endpoint="/api/v1/test",
            status_code=200,
            response_time_ms=100.0 + (i % 3), # minor variance
            ip="127.0.0.1",
            message="Request successful"
        )
        alerts = await detector.process_log(log)
        assert len(alerts) == 0


@pytest.mark.asyncio
async def test_latency_anomaly_trigger():
    """
    Ensure a response time that deviates >3 standard deviations triggers an alert.
    """
    redis_mock = MockRedis()
    detector = AnomalyDetector(redis_mock)

    base_time = datetime.utcnow()
    
    # Establish a very stable baseline (mean: 100ms, std: ~1.4ms)
    for i in range(15):
        log = LogPayload(
            timestamp=base_time + timedelta(seconds=i),
            level="INFO",
            service="test-service",
            endpoint="/api/v1/test",
            status_code=200,
            response_time_ms=100.0 if i % 2 == 0 else 102.0,
            ip="127.0.0.1",
            message="Normal request"
        )
        await detector.process_log(log)

    # Spike request (500ms is far beyond mean + 3 * std)
    spike_log = LogPayload(
        timestamp=base_time + timedelta(seconds=20),
        level="INFO",
        service="test-service",
        endpoint="/api/v1/test",
        status_code=200,
        response_time_ms=500.0,
        ip="127.0.0.1",
        message="Spike request"
    )

    alerts = await detector.process_log(spike_log)
    assert len(alerts) == 1
    assert alerts[0].type == "latency_anomaly"
    assert "Latency spike" in alerts[0].message
    assert alerts[0].metric_value == 500.0


@pytest.mark.asyncio
async def test_error_spike_detection():
    """
    Verify error rate spike detection when error rate surges compared to baseline.
    """
    redis_mock = MockRedis()
    detector = AnomalyDetector(redis_mock)

    base_time = datetime.utcnow()

    # 30 baseline logs with status 200 (0% error rate)
    for i in range(30):
        log = LogPayload(
            timestamp=base_time + timedelta(seconds=i),
            level="INFO",
            service="test-service",
            endpoint="/api/v1/test",
            status_code=200,
            response_time_ms=50.0,
            ip="127.0.0.1",
            message="Success"
        )
        await detector.process_log(log)

    # Ingest a burst of 500 errors in a tight window
    # To satisfy `curr_total >= 5` and `curr_error_rate > 0.05`
    for i in range(5):
        err_log = LogPayload(
            timestamp=base_time + timedelta(seconds=100 + i),
            level="ERROR",
            service="test-service",
            endpoint="/api/v1/test",
            status_code=500,
            response_time_ms=60.0,
            ip="127.0.0.1",
            message="Database connection error"
        )
        alerts = await detector.process_log(err_log)
        
        # The first few might not spike yet, but as error density increases, it should trigger.
        if i == 4:
            assert len(alerts) > 0
            assert any(a.type == "error_spike" for a in alerts)


@pytest.mark.asyncio
async def test_brute_force_detection():
    """
    Verify brute force detection alerts when threshold is crossed.
    """
    redis_mock = MockRedis()
    detector = AnomalyDetector(redis_mock)

    base_time = datetime.utcnow()
    attacker_ip = "192.168.1.100"

    # Send 4 authentication failures (no alert yet since threshold is 5)
    for i in range(4):
        log = LogPayload(
            timestamp=base_time + timedelta(seconds=i),
            level="WARNING",
            service="auth-service",
            endpoint="/api/v1/login",
            status_code=401,
            response_time_ms=120.0,
            ip=attacker_ip,
            message="Authentication failed"
        )
        alerts = await detector.process_log(log)
        assert len(alerts) == 0

    # 5th failed login triggers alert
    trigger_log = LogPayload(
        timestamp=base_time + timedelta(seconds=5),
        level="WARNING",
        service="auth-service",
        endpoint="/api/v1/login",
        status_code=401,
        response_time_ms=125.0,
        ip=attacker_ip,
        message="Authentication failed"
    )
    alerts = await detector.process_log(trigger_log)
    assert len(alerts) == 1
    assert alerts[0].type == "brute_force"
    assert attacker_ip in alerts[0].message
