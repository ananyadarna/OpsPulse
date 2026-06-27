import React from 'react';
import { Activity } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function TrendsChart({ chartData }) {
  return (
    <div className="glass-panel dashboard-block">
      <div className="block-title">
        <Activity size={18} style={{ color: 'var(--color-primary)' }} />
        <span>Live Performance Latency (ms)</span>
      </div>
      
      <div style={{ width: '100%', height: '320px', marginTop: '10px' }}>
        {chartData.length === 0 ? (
          <div className="no-data">
            <span>Waiting for stream metrics to plot...</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorFrontend" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-success)" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="var(--color-success)" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorAuth" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorPayment" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-warning)" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="var(--color-warning)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis 
                dataKey="time" 
                stroke="var(--text-dark)" 
                fontSize={11}
                tickLine={false}
              />
              <YAxis 
                stroke="var(--text-dark)" 
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(16, 20, 30, 0.95)', 
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  fontFamily: 'var(--font-sans)',
                  fontSize: '12px'
                }} 
              />
              <Area 
                type="monotone" 
                dataKey="frontend-api" 
                name="Frontend API"
                stroke="var(--color-success)" 
                fillOpacity={1} 
                fill="url(#colorFrontend)" 
                strokeWidth={2}
                connectNulls
              />
              <Area 
                type="monotone" 
                dataKey="auth-service" 
                name="Auth Service"
                stroke="var(--color-primary)" 
                fillOpacity={1} 
                fill="url(#colorAuth)" 
                strokeWidth={2}
                connectNulls
              />
              <Area 
                type="monotone" 
                dataKey="payment-gateway" 
                name="Payment Gateway"
                stroke="var(--color-warning)" 
                fillOpacity={1} 
                fill="url(#colorPayment)" 
                strokeWidth={2}
                connectNulls
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
