import React, { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

export default function LiveLogsList({ logs }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef.current) {
      // Auto-scroll to bottom of log terminal
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const formatTimestamp = (isoString) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour12: false, fractionalSecondDigits: 3 });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="glass-panel dashboard-block" style={{ gridColumn: 'span 2', minHeight: '350px' }}>
      <div className="block-title">
        <Terminal size={18} style={{ color: 'var(--color-primary)' }} />
        <span>Live Log Stream</span>
      </div>
      
      <div className="logs-terminal" ref={containerRef}>
        {logs.length === 0 ? (
          <div className="no-data">
            <span>No log activity detected. Waiting for logs...</span>
          </div>
        ) : (
          logs.map((log, index) => (
            <div className="log-line" key={index}>
              <span className="log-time">[{formatTimestamp(log.timestamp)}]</span>
              <span className={`log-level ${log.level}`}>{log.level.padEnd(5)}</span>
              <span className="log-svc">[{log.service}]</span>
              <span className="log-msg">
                {log.endpoint} - {log.status_code} ({log.response_time_ms}ms) - {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
