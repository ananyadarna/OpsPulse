import React from 'react';
import { BellRing, ShieldAlert, CheckCircle } from 'lucide-react';

export default function AlertsPanel({ alerts }) {
  const formatTime = (isoString) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="glass-panel dashboard-block">
      <div className="block-title">
        <BellRing size={18} style={{ color: alerts.length > 0 ? 'var(--color-danger)' : 'var(--color-success)' }} />
        <span>Active Alerts</span>
      </div>
      
      <div className="alerts-list">
        {alerts.length === 0 ? (
          <div className="no-data" style={{ height: '300px' }}>
            <CheckCircle size={48} style={{ color: 'var(--color-success)', marginBottom: '8px' }} />
            <span style={{ color: 'var(--color-success)', fontWeight: '600' }}>All Systems Operational</span>
            <span style={{ fontSize: '12px' }}>No anomalies detected in active windows.</span>
          </div>
        ) : (
          [...alerts].reverse().map((alert, index) => (
            <div 
              className={`alert-item ${alert.severity === 'CRITICAL' ? 'critical' : 'warning'}`} 
              key={index}
            >
              <div className="alert-meta">
                <span className="alert-time">{formatTime(alert.timestamp)}</span>
                <span className={`alert-badge ${alert.severity === 'CRITICAL' ? 'critical' : 'warning'}`}>
                  {alert.severity}
                </span>
              </div>
              <div className="alert-message" style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                <ShieldAlert 
                  size={16} 
                  style={{ 
                    color: alert.severity === 'CRITICAL' ? 'var(--color-danger)' : 'var(--color-warning)',
                    flexShrink: 0,
                    marginTop: '2px'
                  }} 
                />
                <div>
                  <strong>{alert.type.replace('_', ' ').toUpperCase()}:</strong> {alert.message}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
