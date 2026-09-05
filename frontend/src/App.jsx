import React, { useState, useEffect } from 'react';
import { Shield, ChevronDown, RefreshCw, Activity, Building2 } from 'lucide-react';
import './index.css';

const API_BASE_URL = window.location.origin.includes('5173') ? 'http://localhost:8000' : '';

const MERCHANTS = [
  { id: 1, name: 'Healthy E-commerce', type: 'ecommerce' },
  { id: 2, name: 'Escalating E-commerce', type: 'ecommerce' },
  { id: 3, name: 'Healthy Subscription', type: 'subscription' },
  { id: 4, name: 'Escalating Subscription', type: 'subscription' },
];

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
        )}
      </main>
    </div>
  );
}
