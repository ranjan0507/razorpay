import React, { useState, useEffect } from 'react';
import { Shield, ChevronDown, RefreshCw, Activity, Building2, TrendingUp, Layers, Clock, HelpCircle, AlertCircle } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import './index.css';

const API_BASE_URL = window.location.origin.includes('5173') ? 'http://localhost:8000' : '';

const MERCHANTS = [
  { id: 1, name: 'Healthy E-commerce', type: 'ecommerce' },
  { id: 2, name: 'Escalating E-commerce', type: 'ecommerce' },
  { id: 3, name: 'Healthy Subscription', type: 'subscription' },
  { id: 4, name: 'Escalating Subscription', type: 'subscription' },
];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="chart-tooltip">
        <div className="chart-tooltip-month">Cohort Month: {data.month}</div>
        <div className="chart-tooltip-rate">{data.display_rate}</div>
        <div className="chart-tooltip-meta">
          {data.dispute_count} disputes out of {data.transaction_count.toLocaleString()} transactions
        </div>
      </div>
    );
  }
  return null;
};

export default function App() {
  const [selectedMerchantId, setSelectedMerchantId] = useState(1);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAnalytics = async (merchantId) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/merchants/${merchantId}/analytics`);
      if (!response.ok) {
        throw new Error(`Failed to load merchant analytics (HTTP ${response.status})`);
      }
      const data = await response.json();
      setAnalyticsData(data);
    } catch (err) {
      setError(err.message || 'Error connecting to DisputeGuard backend API');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics(selectedMerchantId);
  }, [selectedMerchantId]);

  // Helper to format dispute rates as standard percentage strings (e.g. 0.835%)
  const formatPercent = (val) => {
    if (val === undefined || val === null) return '0.000%';
    return `${(val * 100).toFixed(3)}%`;
  };

  // Map backend monthly_metrics into percentage data points for recharts
  const chartData = (analyticsData?.monthly_metrics || []).map((m) => ({
    month: m.month,
    dispute_rate: +(m.dispute_rate * 100).toFixed(3),
    display_rate: formatPercent(m.dispute_rate),
    transaction_count: m.transaction_count,
    dispute_count: m.dispute_count,
  }));

  const thresholdPercent = +(
    (analyticsData?.merchant?.risk_threshold ?? 0.02) * 100
  ).toFixed(3);

  // Top 3 segment drivers directly from backend ranking
  const topDrivers = (analyticsData?.segment_drivers || []).slice(0, 3);

  // Forecast state directly from backend
  const forecast = analyticsData?.forecast;

  return (
    <div className="app-container">
      {/* Header & Merchant Selector */}
      <header className="header">
        <div className="brand">
          <Shield className="brand-icon" />
          <div>
            <h1 className="brand-title">DisputeGuard</h1>
            <p className="brand-subtitle">Deterministic Chargeback Risk Engine</p>
          </div>
        </div>

        <div className="selector-container">
          <label htmlFor="merchant-select" className="selector-label">
            Active Merchant:
          </label>
          <div className="select-wrapper">
            <select
              id="merchant-select"
              value={selectedMerchantId}
              onChange={(e) => setSelectedMerchantId(Number(e.target.value))}
              className="merchant-select"
            >
              {MERCHANTS.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.type})
                </option>
              ))}
            </select>
            <ChevronDown className="select-icon" />
          </div>
        </div>
      </header>

      {/* Main Content State Handling */}
      <main>
        {loading && (
          <div className="status-card">
            <div className="spinner"></div>
            <p style={{ color: 'var(--text-secondary)' }}>
              Fetching real-time risk analytics from backend...
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="status-card" style={{ borderColor: 'rgba(239, 68, 68, 0.3)' }}>
            <h3 className="error-title">Unable to Fetch Analytics</h3>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '400px' }}>{error}</p>
            <button
              onClick={() => fetchAnalytics(selectedMerchantId)}
              className="retry-btn"
            >
              <RefreshCw style={{ width: '1rem', height: '1rem' }} /> Retry Request
            </button>
          </div>
        )}

        {!loading && !error && analyticsData && (
          <>
            {/* Top-Level Summary Grid */}
            <div className="summary-grid">
              {/* Primary Prominent Numerical Risk Score Card */}
              {(() => {
                const riskScore = analyticsData.risk_assessment?.risk_score ?? 0;
                return (
                  <div className="card risk-card">
                    <div className="card-header">
                      <span className="card-title">Overall Risk Score</span>
                      <Shield className="card-icon" />
                    </div>

                    <div className="score-display">
                      <span className="score-number">
                        {riskScore.toFixed(2)}
                      </span>
                      <span className="score-max">/ 100</span>
                    </div>

                    <div className="gauge-container">
                      <div className="gauge-track">
                        <div
                          className="gauge-fill"
                          style={{ width: `${Math.min(100, Math.max(0, riskScore))}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Merchant Identity Card */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Merchant Profile</span>
                  <Building2 className="card-icon" />
                </div>

                <div>
                  <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {analyticsData.merchant?.name}
                  </h2>
                  <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem' }}>
                    <span className="type-pill">ID #{analyticsData.merchant?.id}</span>
                    <span className="type-pill">{analyticsData.merchant?.type}</span>
                  </div>
                </div>

                <div className="metric-meta">
                  <span>Baseline Dispute Rate</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {formatPercent(analyticsData.merchant?.historical_baseline)}
                  </span>
                </div>
              </div>

              {/* Dispute Rate & Threshold Card */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Dispute Rate & Threshold</span>
                  <Activity className="card-icon" />
                </div>

                <div>
                  <div className="metric-value">
                    {formatPercent(analyticsData.overall_metrics?.current_dispute_rate)}
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Current Month Cohort Rate
                  </p>
                </div>

                <div className="metric-meta">
                  <span>Configured Risk Threshold</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {formatPercent(analyticsData.merchant?.risk_threshold)}
                  </span>
                </div>
              </div>
            </div>

            {/* Risk Trajectory Section */}
            <div className="section-card">
              <div className="section-header">
                <h2 className="section-title">
                  <TrendingUp style={{ width: '1.25rem', height: '1.25rem', color: 'var(--accent-blue)' }} />
                  Risk Trajectory
                </h2>
              </div>

              {chartData.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                  No monthly metrics available.
                </p>
              ) : (
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 15, right: 30, left: 10, bottom: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
                      <XAxis
                        dataKey="month"
                        stroke="var(--text-muted)"
                        fontSize={12}
                        tickLine={false}
                      />
                      <YAxis
                        stroke="var(--text-muted)"
                        fontSize={12}
                        tickLine={false}
                        tickFormatter={(val) => `${val.toFixed(2)}%`}
                        domain={[0, 'auto']}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      {thresholdPercent > 0 && (
                        <ReferenceLine
                          y={thresholdPercent}
                          stroke="#ef4444"
                          strokeDasharray="5 5"
                          label={{
                            value: `Threshold (${thresholdPercent.toFixed(3)}%)`,
                            fill: '#ef4444',
                            fontSize: 11,
                            position: 'top',
                          }}
                        />
                      )}
                      <Line
                        type="monotone"
                        dataKey="dispute_rate"
                        stroke="var(--accent-blue)"
                        strokeWidth={3}
                        dot={{ r: 5, fill: 'var(--accent-blue)', stroke: '#0b0f19', strokeWidth: 2 }}
                        activeDot={{ r: 7, fill: '#60a5fa' }}
                        name="Cohort Dispute Rate"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Strongest Observed Drivers Section */}
            <div className="section-card">
              <div className="section-header">
                <h2 className="section-title">
                  <Layers style={{ width: '1.25rem', height: '1.25rem', color: 'var(--accent-blue)' }} />
                  Strongest Observed Drivers
                </h2>
              </div>

              {topDrivers.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                  No significant positive segment drivers detected.
                </p>
              ) : (
                <div className="drivers-list">
                  {topDrivers.map((driver, idx) => {
                    const isTop = idx === 0;
                    return (
                      <div
                        key={idx}
                        className={`driver-card ${isTop ? 'top-driver' : ''}`}
                      >
                        <div className="driver-header">
                          <span
                            className={`driver-rank-badge ${
                              isTop ? 'rank-1' : 'rank-secondary'
                            }`}
                          >
                            {isTop
                              ? '#1 Strongest Observed Driver'
                              : `#${idx + 1} Observed Driver`}
                          </span>

                          <div className="driver-dimensions">
                            {Object.entries(driver.values || {}).map(([key, val]) => (
                              <span key={key} className="dimension-tag">
                                <span className="dim-name">{key}:</span>
                                <span className="dim-value">{val}</span>
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="driver-metrics-grid">
                          <div className="driver-metric-item">
                            <span className="driver-metric-label">Dispute Rate</span>
                            <span className="driver-metric-val highlight">
                              {formatPercent(driver.dispute_rate)}
                            </span>
                          </div>

                          <div className="driver-metric-item">
                            <span className="driver-metric-label">Observed Lift</span>
                            <span className="driver-metric-val lift">
                              {driver.lift.toFixed(2)}×
                            </span>
                          </div>

                          <div className="driver-metric-item">
                            <span className="driver-metric-label">Excess Disputes</span>
                            <span className="driver-metric-val excess">
                              +{driver.excess_disputes.toFixed(1)}
                            </span>
                          </div>

                          <div className="driver-metric-item">
                            <span className="driver-metric-label">Disputes</span>
                            <span className="driver-metric-val">
                              {driver.dispute_count.toLocaleString()}
                            </span>
                          </div>

                          <div className="driver-metric-item">
                            <span className="driver-metric-label">Transactions</span>
                            <span className="driver-metric-val">
                              {driver.transaction_count.toLocaleString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Threshold Forecast Section */}
            <div className="section-card">
              <div className="section-header">
                <h2 className="section-title">
                  <Clock style={{ width: '1.25rem', height: '1.25rem', color: 'var(--accent-blue)' }} />
                  Threshold Forecast
                </h2>
              </div>

              {!forecast ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                  Forecast data unavailable.
                </p>
              ) : (
                <div className="forecast-card">
                  <div className="forecast-header-row">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                      <span className={`forecast-state-badge ${forecast.status}`}>
                        {forecast.status === 'projected_breach' && 'Projected Breach'}
                        {forecast.status === 'already_breached' && 'Threshold Already Breached'}
                        {forecast.status === 'no_breach_projected' && 'No Threshold Breach Projected Under Current Trend'}
                        {forecast.status !== 'projected_breach' &&
                         forecast.status !== 'already_breached' &&
                         forecast.status !== 'no_breach_projected' &&
                         'Forecast Unavailable'}
                      </span>

                      {forecast.status === 'projected_breach' && forecast.is_highly_uncertain && (
                        <span className="uncertainty-badge">
                          <AlertCircle style={{ width: '0.85rem', height: '0.85rem' }} />
                          High Uncertainty
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Current Dispute Rate: <strong style={{ color: 'var(--text-primary)' }}>{formatPercent(forecast.current_rate)}</strong> | Threshold: <strong style={{ color: 'var(--text-primary)' }}>{formatPercent(forecast.risk_threshold)}</strong>
                    </div>
                  </div>

                  <div className="forecast-grid">
                    <div className="forecast-metric-item">
                      <span className="forecast-metric-label">Forecast Status</span>
                      <span className="forecast-metric-val" style={{ fontSize: '1.05rem' }}>
                        {forecast.status === 'projected_breach' && 'Projected Breach'}
                        {forecast.status === 'already_breached' && 'Already Breached'}
                        {forecast.status === 'no_breach_projected' && 'No Breach Projected'}
                        {forecast.status !== 'projected_breach' &&
                         forecast.status !== 'already_breached' &&
                         forecast.status !== 'no_breach_projected' &&
                         'Unavailable'}
                      </span>
                    </div>

                    <div className="forecast-metric-item">
                      <span className="forecast-metric-label">
                        {forecast.status === 'already_breached'
                          ? 'Observed Breach Month'
                          : 'Estimated Crossing Month'}
                      </span>
                      <span className="forecast-metric-val">
                        {forecast.status === 'projected_breach'
                          ? forecast.estimated_crossing_month || 'N/A'
                          : forecast.status === 'already_breached'
                          ? forecast.estimated_crossing_month || 'N/A'
                          : 'N/A'}
                      </span>
                    </div>

                    <div className="forecast-metric-item">
                      <span className="forecast-metric-label">Forecast Window</span>
                      <span className="forecast-metric-val" style={{ fontSize: '1.05rem' }}>
                        {forecast.status === 'projected_breach' && forecast.forecast_start && forecast.forecast_end
                          ? `${forecast.forecast_start} → ${forecast.forecast_end}`
                          : 'N/A'}
                      </span>
                    </div>

                    <div className="forecast-metric-item">
                      <span className="forecast-metric-label">Uncertainty State</span>
                      <span className="forecast-metric-val" style={{ fontSize: '1.05rem' }}>
                        {forecast.is_highly_uncertain ? 'High Uncertainty' : 'Standard Variance'}
                      </span>
                    </div>
                  </div>

                  <div className="explanatory-note">
                    <HelpCircle style={{ width: '1.1rem', height: '1.1rem', flexShrink: 0, marginTop: '0.1rem', color: 'var(--accent-blue)' }} />
                    <div>
                      <strong>Methodology Note:</strong> Threshold projections are derived from simple linear regression fitted to monthly cohort dispute rates combined with historical residual variability. Projections reflect mathematical trajectory under current trends and are not guaranteed predictions or formal statistical confidence intervals.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
