# OpsPulse ⚡️

### Real-Time Production Monitoring & Intelligent Alerting Platform

OpsPulse is a real-time system monitoring and observability platform. It ingests application log streams, processes them in real time, executes statistical anomaly detection rules (without slow, unexplainable ML models), and broadcasts alerts and parsed logs instantly to a dark, glassmorphic React dashboard over WebSockets.

---

## 🛠️ Architecture

```
                       [ Log Generator (generate_logs.py) ]
                                       │
                                       ▼ (HTTP POST /api/logs)
                             [ FastAPI Ingestion API ]
                                       │
                                       ▼
                         [ Anomaly Detection Engine ]
                        /              │             \
                       /               │              \
                      ▼                ▼               ▼
        [ MongoDB Database ]   [ Redis Pub/Sub ]   [ Redis State (ZSETs) ]
         (Alert History)          (Event Bus)       (Rolling metrics window)
                                       │
                                       ▼
                             [ WebSocket Server ]
                                       │
                                       ▼ (ws://localhost:8000/ws)
                             [ React Dashboard ]
```

### Advanced Observability Design Choices:
* **Redis-Backed State:** Instead of storing rolling metrics in-memory (which breaks horizontal scaling), OpsPulse uses **Redis Sorted Sets (ZSETs)**. The FastAPI workers remain stateless, meaning you can spin up 10 workers behind a load balancer and they will all share the same statistical rolling window.
* **Event-Time Processing:** Anomaly detection uses the log's own timestamp rather than the server's receive time, making the detection deterministic, resistant to network delays, and easily testable.
* **Fallback Log Parser:** Processes structured JSON logs natively with Pydantic validation, and automatically falls back to regex-based parsing for standard Common Log Format (CLF) text logs.

---

## 🚦 Core Anomaly Detection Logic

1. **Latency Anomaly (Z-Score):** Tracks response times in a 5-minute rolling window. If an incoming request's latency deviates by more than $3\sigma$ (standard deviations) from the rolling mean ($\mu$), a warning/critical alert is triggered:
   $$Z = \frac{X - \mu}{\sigma}$$
   *Requires a minimum of 10 samples to avoid cold-start false positives.*
2. **Error Rate Spike:** Compares the error rate (percentage of 5xx / ERROR logs) in the last 1 minute against the 5-minute rolling average. If the current error rate exceeds the baseline by $2.5\text{x}$, a critical alert is raised.
3. **Brute Force Detection:** Monitors authentication endpoints. If a single IP address triggers $\ge 5$ authentication failures (401/403 status codes) within a 30-second sliding window, a critical security alert is emitted.

---

## 🚀 Getting Started

### Option A: Run Locally (Recommended for Development)

#### 1. Prerequisites
Ensure you have **MongoDB** and **Redis** running locally on their default ports (`27017` and `6379`). If you have Docker installed, you can start them with:
```bash
docker compose up -d mongodb redis
```

#### 2. Run the Backend
```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment (Python 3.12 recommended)
py -3.12 -m venv venv
source venv/Scripts/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn app.main:app --reload
```
*The backend will be available at `http://localhost:8000`.*

#### 3. Run the Frontend
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Run Vite development server
npm run dev
```
*Open your browser and navigate to `http://localhost:5173`.*

#### 4. Start the Log Generator
In a new terminal, run the simulator to start streaming logs:
```bash
python backend/generate_logs.py
```

---

### Option B: Run via Docker Compose (Full Stack)

If you have Docker Desktop running, you can spin up the entire multi-container stack with one command:
```bash
docker compose up --build
```
* The React Frontend will be available at `http://localhost:3000`
* The FastAPI Backend will be available at `http://localhost:8000`
* MongoDB runs on port `27017`
* Redis runs on port `6379`

---

## 🧪 Running Unit Tests

OpsPulse includes unit tests that verify the statistical detection algorithms in isolation using a custom async mock Redis client.

To run the test suite, run:
```bash
# From the project root
$env:PYTHONPATH="backend"
.\venv\Scripts\pytest backend/tests/
```

---

## 🎯 Verification & Demo Flow

1. Open the React Dashboard at `http://localhost:5173` (or `http://localhost:3000` if using Docker).
2. Start the log generator in normal mode: `python backend/generate_logs.py`
   * *You will see the throughput charts begin to plot and logs stream in real-time in the terminal.*
3. **Trigger a Latency Anomaly:**
   ```bash
   python backend/generate_logs.py --spike
   ```
   * *A latency spike will be injected, triggering a Z-score alert. The alert will flash in the dashboard's alert panel.*
4. **Trigger an Error Spike:**
   ```bash
   python backend/generate_logs.py --errors
   ```
   * *A sudden burst of 500 status codes will be sent. The error rate metric card will turn red and an Error Spike alert will appear.*
5. **Trigger a Brute-Force Attack:**
   ```bash
   python backend/generate_logs.py --brute-force
   ```
   * *A sequence of rapid 401 login failures from a single IP will trigger a security alert.*
6. **Verify Persistence:** Refresh the dashboard. Historical alerts will reload instantly from MongoDB.

---

## 🧠 Challenges Faced & Technical Decisions

### 1. Stateless Horizontally-Scalable State Management
* **The Challenge:** Observability tools need to calculate metrics over a rolling window. Storing these windows in-memory (e.g., inside a Python `deque` or list) works for single-process setups. However, if the FastAPI application scales horizontally to multiple worker processes (e.g., behind a load balancer), the state becomes split, and restarting any worker wipes out the history.
* **The Solution:** We offloaded the sliding window state to **Redis Sorted Sets (ZSETs)**. Each log record adds a member (`f"{value}:{uuid}"`) with its timestamp as the score. Pruning and querying are done using `ZREMRANGEBYSCORE` and `ZRANGEBYSCORE`. This keeps our FastAPI workers stateless and allows them to scale horizontally.

### 2. Timezone Mismatches in Event-Time Processing
* **The Challenge:** During unit testing, naive datetime objects generated in test payloads were converted to epoch timestamps using the local system timezone. When compared against the server's timezone-neutral `time.time()`, this created a multi-hour offset, causing the sliding window logic to immediately prune all incoming test logs (resulting in empty windows and failing tests).
* **The Solution:** We transitioned the anomaly detection engine from *processing-time* (system time) to *event-time* (log timestamp). Pruning and calculations now reference the incoming log's own timestamp (`log.timestamp.timestamp()`). This eliminated timezone dependencies and made the test suite 100% deterministic.

### 3. Pre-Release Python Compatibility
* **The Challenge:** The local machine's default Python version was Python 3.14 (pre-release). Since Python 3.14 is extremely new, pre-compiled binary wheels for C/Rust-compiled libraries like `numpy` and `pydantic-core` do not yet exist on PyPI. As a result, `pip install` tried to compile them from source, failing due to the absence of the MSVC compiler toolchain.
* **The Solution:** We diagnosed the environment, identified that Python 3.12 was also installed on the system, and rebuilt the virtual environment using `py -3.12 -m venv venv`. This allowed `pip` to pull stable, pre-compiled binary wheels in seconds.

