import React from 'react';

export default function MetricCard({ title, value, icon: Icon, trend, trendValue, color = 'primary' }) {
  const getGlowStyle = () => {
    switch (color) {
      case 'success': return 'rgba(16, 185, 129, 0.15)';
      case 'warning': return 'rgba(245, 158, 11, 0.15)';
      case 'danger': return 'rgba(239, 68, 68, 0.15)';
      case 'info': return 'rgba(6, 182, 212, 0.15)';
      default: return 'rgba(99, 102, 241, 0.15)';
    }
  };

  const getAccentColor = () => {
    switch (color) {
      case 'success': return 'var(--color-success)';
      case 'warning': return 'var(--color-warning)';
      case 'danger': return 'var(--color-danger)';
      case 'info': return 'var(--color-info)';
      default: return 'var(--color-primary)';
    }
  };

  return (
    <div 
      className="glass-panel metric-card"
      style={{ 
        boxShadow: `var(--shadow-md), 0 0 20px 1px ${getGlowStyle()}`,
        borderTop: `3px solid ${getAccentColor()}`
      }}
    >
      <div className="metric-header">
        <span>{title}</span>
        {Icon && <Icon size={18} style={{ color: getAccentColor() }} />}
      </div>
      <div className="metric-value">{value}</div>
      {trend && (
        <div className={`metric-trend trend-${trend}`}>
          <span>{trend === 'up' ? '▲' : trend === 'down' ? '▼' : '■'}</span>
          <span>{trendValue}</span>
        </div>
      )}
    </div>
  );
}
