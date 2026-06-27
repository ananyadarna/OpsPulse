import React, { useState, useEffect, useRef } from 'react';
import { Activity, Flame, ShieldAlert, Cpu } from 'lucide-react';
import MetricCard from './components/MetricCard';
import LiveLogsList from './components/LiveLogsList';
import AlertsPanel from './components/AlertsPanel';
import TrendsChart from './components/TrendsChart';

const WS_URL = 'ws://localhost:8000/ws';
const API_URL = 'http://localhost:8000/api';

export default function App() {
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [chartData, setChartData] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected'
  
  // Real-time calculated metrics
  const [metrics, setMetrics] = useState({
    reqRate: 0,
    errorRate: 0,
    avgLatency: 0,
    totalAlerts: 0
  });

  const ws = useRef(null);
  const logsRef = useRef([]);

  // Fetch initial alert history from DB
  useEffect(() => {
    fetch(`${API_URL}/alerts`)
      .then(res => {
        if (res.ok) return res.json();
        throw new Error("HTTP error");
      })
      .then(data => {
        setAlerts(data);
      })
      .catch(err => console.error("Error fetching historical alerts:", err));
  }, []);

  // WebSockets Connection & Reconnect Loop
  useEffect(() => {
    function connect() {
      setConnectionStatus('connecting');
      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        setConnectionStatus('connected');
        console.log("WebSocket connected to OpsPulse backend.");
      };

      ws.current.onmessage = (event) => {
        try {
          const packet = JSON.parse(event.data);
          
          if (packet.event === 'log') {
            const newLog = packet.data;
            
            // Add to logs list (keep last 50)
            setLogs(prev => {
              const updated = [...prev, newLog];
              if (updated.length > 50) updated.shift();
              logsRef.current = updated;
              return updated;
            });

            // Update chart data
            setChartData(prev => {
              const timeString = new Date(newLog.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
              const newPoint = {
                time: timeString,
                [newLog.service]: newLog.response_time_ms
              };
              const updated = [...prev, newPoint];
              if (updated.length > 20) updated.shift();
              return updated;
            });

          } else if (packet.event === 'alert') {
            const newAlert = packet.data;
            setAlerts(prev => [...prev, newAlert]);
          }
        } catch (e) {
          console.error("Error handling WebSocket message:", e);
        }
      };

      ws.current.onclose = () => {
        setConnectionStatus('disconnected');
        console.log("WebSocket connection closed. Retrying in 3 seconds...");
        setTimeout(connect, 3000);
      };

      ws.current.onerror = (err) => {
        console.error("WebSocket error observed:", err);
        ws.current.close();
      };
    }

    connect();

    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  // Calculate sliding-window stats every 2 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      const currentLogs = logsRef.current;
      if (currentLogs.length === 0) {
        setMetrics(prev => ({ ...prev, reqRate: 0, errorRate: 0, avgLatency: 0 }));
        return;
      }

      // Filter logs in the last 15 seconds to simulate a live sliding window
      const now = new Date();
      const windowCutoff = new Date(now.getTime() - 15 * 1000);
      const recentLogs = currentLogs.filter(log => new Date(log.timestamp) > windowCutoff);
      
      const reqCount = recentLogs.length;
      const ratePerSec = reqCount / 15;

      const errorCount = recentLogs.filter(log => log.status_code >= 500 || log.level === 'ERROR').length;
      const errorPct = reqCount > 0 ? (errorCount / reqCount) * 100 : 0;

      const totalLatency = recentLogs.reduce((sum, log) => sum + log.response_time_ms, 0);
      const avgLat = reqCount > 0 ? totalLatency / reqCount : 0;

      setMetrics({
        reqRate: parseFloat(ratePerSec.toFixed(1)),
        errorRate: parseFloat(errorPct.toFixed(1)),
        avgLatency: parseFloat(avgLat.toFixed(1)),
        totalAlerts: alerts.length
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [alerts]);

  return (
    <div className="app-container">
      <header>
        <div className="logo-section">
          <div className="logo-icon">
            <Cpu size={24} color="#fff" />
          </div>
          <div>
            <h1>OpsPulse</h1>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Real-Time System Monitoring & Statistics Engine</p>
          </div>
        </div>

        <div className="connection-badge">
          <span className={`badge-dot ${connectionStatus}`}></span>
          <span style={{ textTransform: 'capitalize' }}>
            {connectionStatus === 'connected' ? 'Live Connection' : connectionStatus === 'connecting' ? 'Reconnecting...' : 'Offline'}
          </span>
        </div>
      </header>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <MetricCard 
          title="Throughput (15s Window)" 
          value={`${metrics.reqRate} req/sec`} 
          icon={Activity} 
          trend={metrics.reqRate > 2.0 ? 'up' : metrics.reqRate > 0 ? 'neutral' : 'down'}
          trendValue="Live traffic rate"
          color="info"
        />
        <MetricCard 
          title="Error Rate" 
          value={`${metrics.errorRate}%`} 
          icon={Flame} 
          trend={metrics.errorRate > 5.0 ? 'up' : 'down'}
          trendValue={metrics.errorRate > 5.0 ? 'Elevated errors' : 'Within normal limits'}
          color={metrics.errorRate > 10.0 ? 'danger' : metrics.errorRate > 0 ? 'warning' : 'success'}
        />
        <MetricCard 
          title="Average Latency" 
          value={`${metrics.avgLatency} ms`} 
          icon={Activity} 
          trend={metrics.avgLatency > 500.0 ? 'up' : 'down'}
          trendValue="Rolling 15s avg"
          color={metrics.avgLatency > 600.0 ? 'danger' : metrics.avgLatency > 300.0 ? 'warning' : 'success'}
        />
        <MetricCard 
          title="Total Incidents" 
          value={metrics.totalAlerts} 
          icon={ShieldAlert} 
          trend={metrics.totalAlerts > 0 ? 'up' : 'neutral'}
          trendValue="Saved to database"
          color={metrics.totalAlerts > 0 ? 'danger' : 'success'}
        />
      </div>

      {/* Main Sections */}
      <div className="main-content">
        <TrendsChart chartData={chartData} />
        <AlertsPanel alerts={alerts} />
        <LiveLogsList logs={logs} />
      </div>
    </div>
  );
}
