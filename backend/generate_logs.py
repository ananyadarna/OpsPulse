import time
import json
import random
import argparse
import urllib.request
import urllib.error
from datetime import datetime

# Setup services metadata
SERVICES = {
    "frontend-api": {
        "endpoints": ["/api/v1/home", "/api/v1/products", "/api/v1/profile"],
        "mean_latency": 35.0,
        "std_latency": 8.0,
        "error_chance": 0.01 # 1% error rate
    },
    "auth-service": {
        "endpoints": ["/api/v1/auth/login", "/api/v1/auth/signup", "/api/v1/auth/logout"],
        "mean_latency": 110.0,
        "std_latency": 25.0,
        "error_chance": 0.02
    },
    "payment-gateway": {
        "endpoints": ["/api/v1/charge", "/api/v1/refund", "/api/v1/billing-info"],
        "mean_latency": 450.0,
        "std_latency": 120.0,
        "error_chance": 0.03
    }
}

IPS = ["192.168.1.10", "203.0.113.5", "198.51.100.8", "54.210.23.85", "8.8.8.8"]

def send_log_to_backend(log_data: dict, url: str):
    """
    Sends log event to FastAPI backend via urllib.
    """
    data = json.dumps(log_data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=2.0) as response:
            return response.read()
    except urllib.error.URLError as e:
        print(f"[ERROR] Failed to send log to backend: {e.reason}")
        return None

def generate_normal_log(service_name: str) -> dict:
    svc = SERVICES[service_name]
    endpoint = random.choice(svc["endpoints"])
    
    # Latency (normally distributed)
    latency = max(5.0, random.normalvariate(svc["mean_latency"], svc["std_latency"]))
    
    # Error code selection
    if random.random() < svc["error_chance"]:
        status_code = random.choice([500, 502, 503])
        level = "ERROR"
        message = f"Internal server error occurred on {endpoint}"
    else:
        status_code = 200
        level = "INFO"
        message = f"Successfully processed request on {endpoint}"
        
        # Account for typical client issues
        if service_name == "auth-service" and random.random() < 0.05:
            status_code = 401
            level = "WARNING"
            message = "Authentication failed: invalid credentials"

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "service": service_name,
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time_ms": round(latency, 2),
        "ip": random.choice(IPS),
        "message": message
    }

def inject_latency_spike(url: str):
    print("\n>>> INJECTING LATENCY SPIKE (payment-gateway) <<<")
    # Generate 15 logs with extremely high latency
    for i in range(15):
        log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "INFO",
            "service": "payment-gateway",
            "endpoint": "/api/v1/charge",
            "status_code": 200,
            "response_time_ms": round(random.uniform(2500.0, 4800.0), 2),
            "ip": random.choice(IPS),
            "message": "Processing large transaction batch"
        }
        send_log_to_backend(log, url)
        print(f"Sent latency spike log: {log['response_time_ms']}ms")
        time.sleep(0.1)

def inject_error_spike(url: str):
    print("\n>>> INJECTING ERROR SPIKE (frontend-api) <<<")
    # Generate 20 logs with 500 status code
    for i in range(20):
        log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "ERROR",
            "service": "frontend-api",
            "endpoint": "/api/v1/products",
            "status_code": 500,
            "response_time_ms": round(random.normalvariate(40.0, 10.0), 2),
            "ip": random.choice(IPS),
            "message": "CRITICAL: Database connection lost"
        }
        send_log_to_backend(log, url)
        print("Sent 500 Error log")
        time.sleep(0.1)

def inject_brute_force(url: str):
    print("\n>>> INJECTING BRUTE-FORCE PATTERN (auth-service) <<<")
    attacker_ip = "198.51.100.42"
    # Send 7 rapid authentication failures from same IP
    for i in range(7):
        log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "WARNING",
            "service": "auth-service",
            "endpoint": "/api/v1/auth/login",
            "status_code": 401,
            "response_time_ms": round(random.uniform(90.0, 140.0), 2),
            "ip": attacker_ip,
            "message": f"Login attempt failed. Username: admin. Try {i+1} of 5."
        }
        send_log_to_backend(log, url)
        print(f"Sent failed login log {i+1} from IP {attacker_ip}")
        time.sleep(0.2)

def main():
    parser = argparse.ArgumentParser(description="OpsPulse Log Generator Simulator")
    parser.add_argument("--url", default="http://localhost:8000/api/logs", help="FastAPI logs ingest URL")
    parser.add_argument("--spike", action="store_true", help="Inject database latency spike")
    parser.add_argument("--errors", action="store_true", help="Inject database error spike")
    parser.add_argument("--brute-force", action="store_true", help="Inject brute-force authentication logs")
    parser.add_argument("--interval", type=float, default=0.5, help="Interval between normal logs (seconds)")
    args = parser.parse_args()

    # Immediate injections
    if args.spike:
        inject_latency_spike(args.url)
        return
    if args.errors:
        inject_error_spike(args.url)
        return
    if args.brute_force:
        inject_brute_force(args.url)
        return

    print(f"Starting OpsPulse live log stream to {args.url} (Interval: {args.interval}s)")
    print("Press Ctrl+C to terminate.")

    while True:
        try:
            # Pick a random service
            service = random.choice(list(SERVICES.keys()))
            log = generate_normal_log(service)
            send_log_to_backend(log, args.url)
            print(f"[{log['level']}] {log['service']} - {log['endpoint']} ({log['status_code']}) in {log['response_time_ms']}ms")
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nLog simulation stopped.")
            break
        except Exception as e:
            print(f"Error in simulation loop: {e}")
            time.sleep(2.0)

if __name__ == "__main__":
    main()
