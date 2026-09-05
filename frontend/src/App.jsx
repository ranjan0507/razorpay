import React, { useState, useEffect } from 'react';
import { Shield, ChevronDown, RefreshCw, Activity, Building2, TrendingUp, Layers, Clock, HelpCircle, AlertCircle, Sparkles } from 'lucide-react';
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

  // AI Explanation state
  const [explanationData, setExplanationData] = useState(null);
  const [explanationLoading, setExplanationLoading] = useState(true);
  const [explanationError, setExplanationError] = useState(null);

  // Q&A state
  const [qaQuestion, setQaQuestion] = useState('');
  const [qaResponse, setQaResponse] = useState(null);
  const [qaLoading, setQaLoading] = useState(false);
  const [qaError, setQaError] = useState(null);

  // Intervention evaluation & AI explanation state
  const [evaluationData, setEvaluationData] = useState(null);
  const [evaluationLoading, setEvaluationLoading] = useState(false);
  const [evaluationError, setEvaluationError] = useState(null);
  const [interventionAction, setInterventionAction] = useState(null);

  const [interventionExplanationData, setInterventionExplanationData] = useState(null);
  const [interventionExplanationLoading, setInterventionExplanationLoading] = useState(false);
  const [interventionExplanationError, setInterventionExplanationError] = useState(null);

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

  const fetchExplanation = async (merchantId) => {
    setExplanationLoading(true);
    setExplanationError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/merchants/${merchantId}/explanation`);
      if (!response.ok) {
        throw new Error(`AI explanation request failed (HTTP ${response.status})`);
      }
      const data = await response.json();
      setExplanationData(data);
    } catch (err) {
      setExplanationError('AI explanation unavailable');
    } finally {
      setExplanationLoading(false);
    }
  };

  const fetchInterventionData = async (merchantId) => {
    setEvaluationLoading(true);
    setEvaluationError(null);
    setEvaluationData(null);
    setInterventionAction(null);

    setInterventionExplanationLoading(false);
    setInterventionExplanationError(null);
    setInterventionExplanationData(null);

    try {
      const listResp = await fetch(`${API_BASE_URL}/merchants/${merchantId}/interventions`);
      if (!listResp.ok) {
        throw new Error(`Failed to fetch merchant interventions (HTTP ${listResp.status})`);
      }
      const interventions = await listResp.json();

      if (!interventions || interventions.length === 0) {
        setEvaluationLoading(false);
        return;
      }

      setInterventionAction(interventions[0].action_description || null);
      const targetInterventionId = interventions[0].id;

      // 1. Fetch deterministic evaluation
      try {
        const evalResp = await fetch(`${API_BASE_URL}/merchants/${merchantId}/interventions/${targetInterventionId}/evaluation`);
        if (!evalResp.ok) {
          throw new Error(`Intervention evaluation request failed (HTTP ${evalResp.status})`);
        }
        const evalData = await evalResp.json();
        setEvaluationData(evalData);
      } catch (evalErr) {
        setEvaluationError(evalErr.message || 'Intervention evaluation unavailable');
        setEvaluationLoading(false);
        return;
      } finally {
        setEvaluationLoading(false);
      }

      // 2. Fetch AI intervention explanation
      setInterventionExplanationLoading(true);
      setInterventionExplanationError(null);
      try {
        const expResp = await fetch(`${API_BASE_URL}/merchants/${merchantId}/interventions/${targetInterventionId}/explanation`);
        if (!expResp.ok) {
          throw new Error(`AI intervention explanation request failed (HTTP ${expResp.status})`);
        }
        const expData = await expResp.json();
        setInterventionExplanationData(expData);
      } catch (expErr) {
        setInterventionExplanationError('AI intervention explanation unavailable');
      } finally {
        setInterventionExplanationLoading(false);
      }
    } catch (err) {
      setEvaluationError(err.message || 'Intervention data unavailable');
      setEvaluationLoading(false);
    }
  };

  const handleAskQuestion = async (overrideQuestion) => {
    const textToAsk = overrideQuestion !== undefined ? overrideQuestion : qaQuestion;
    if (!textToAsk || !textToAsk.trim() || qaLoading) return;

    setQaLoading(true);
    setQaError(null);
    setQaResponse(null);

    try {
      const response = await fetch(`${API_BASE_URL}/merchants/${selectedMerchantId}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: textToAsk.trim() }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Q&A request failed (HTTP ${response.status})`);
      }

      const data = await response.json();
      setQaResponse(data);
    } catch (err) {
      setQaError(err.message || 'Failed to submit question');
    } finally {
      setQaLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics(selectedMerchantId);
    fetchExplanation(selectedMerchantId);
    fetchInterventionData(selectedMerchantId);
    setQaResponse(null);
    setQaError(null);
  }, [selectedMerchantId]);

  // Helper to format dispute rates as standard percentage strings (e.g. 1.97%)
  const formatPercent = (val) => {
    if (val === undefined || val === null) return '0.00%';
    return `${(val * 100).toFixed(2)}%`;
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
              onClick={() => {
                fetchAnalytics(selectedMerchantId);
                fetchExplanation(selectedMerchantId);
              }}
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

            {/* AI Risk Explanation Section */}
            <div className="ai-section-card">
              <div className="section-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <h2 className="section-title">
                    <Sparkles style={{ width: '1.25rem', height: '1.25rem', color: '#c084fc' }} />
                    AI Risk Explanation
                  </h2>
                  <span className="ai-badge">Gemini Powered</span>
                </div>
              </div>

              {explanationLoading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1.5rem 0', color: 'var(--text-secondary)' }}>
                  <div className="spinner" style={{ width: '1.5rem', height: '1.5rem', borderWidth: '2px' }}></div>
                  <span>Generating fact-grounded AI risk narrative...</span>
                </div>
              )}

              {explanationError && !explanationLoading && (
                <div className="ai-error-box">
                  <strong>AI Explanation Unavailable:</strong> {explanationError}
                </div>
              )}

              {!explanationLoading && !explanationError && explanationData && (
                <div className="ai-explanation-grid">
                  <div className="ai-explanation-box ai-explanation-full">
                    <span className="ai-explanation-label">Executive Summary</span>
                    <p className="ai-explanation-text">{explanationData.summary}</p>
                  </div>

                  <div className="ai-explanation-box">
                    <span className="ai-explanation-label">Trend Trajectory</span>
                    <p className="ai-explanation-text">{explanationData.trend_explanation}</p>
                  </div>

                  <div className="ai-explanation-box">
                    <span className="ai-explanation-label">Strongest Observed Driver</span>
                    <p className="ai-explanation-text">{explanationData.driver_explanation}</p>
                  </div>

                  <div className="ai-explanation-box">
                    <span className="ai-explanation-label">Threshold Forecast</span>
                    <p className="ai-explanation-text">{explanationData.forecast_explanation}</p>
                  </div>

                  <div className="ai-explanation-box ai-focus-box">
                    <span className="ai-explanation-label" style={{ color: '#c084fc' }}>Merchant Focus Area</span>
                    <p className="ai-explanation-text" style={{ fontWeight: 500 }}>{explanationData.focus_area}</p>
                  </div>

                  {explanationData.recommended_action && (
                    <div className="ai-explanation-box ai-recommended-box ai-explanation-full">
                      <span className="ai-explanation-label" style={{ color: '#60a5fa' }}>Recommended Action</span>
                      <p className="ai-explanation-text" style={{ fontWeight: 500 }}>{explanationData.recommended_action}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Ask DisputeGuard Section */}
            <div className="section-card qa-section-card">
              <div className="section-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <h2 className="section-title">
                    <HelpCircle style={{ width: '1.25rem', height: '1.25rem', color: 'var(--accent-blue)' }} />
                    Ask DisputeGuard
                  </h2>
                  <span className="type-pill" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa' }}>
                    Fact-Grounded Q&A
                  </span>
                </div>
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleAskQuestion();
                }}
                className="qa-form"
              >
                <div className="qa-input-wrapper">
                  <input
                    type="text"
                    value={qaQuestion}
                    onChange={(e) => setQaQuestion(e.target.value)}
                    placeholder="Ask a question about your merchant risk analytics (e.g. Why is my risk increasing?)..."
                    className="qa-input"
                    disabled={qaLoading}
                  />
                  <button
                    type="submit"
                    disabled={qaLoading || !qaQuestion.trim()}
                    className="qa-submit-btn"
                  >
                    {qaLoading ? (
                      <>
                        <div className="spinner" style={{ width: '1rem', height: '1rem', borderWidth: '2px' }}></div>
                        <span>Asking...</span>
                      </>
                    ) : (
                      <span>Ask</span>
                    )}
                  </button>
                </div>
              </form>

              <div className="qa-suggestions">
                <span className="qa-suggestions-label">Suggested Questions:</span>
                <div className="qa-chips">
                  {[
                    'Why is my risk increasing?',
                    'Which segment is driving the increase?',
                    'When am I projected to cross the threshold?',
                  ].map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      disabled={qaLoading}
                      onClick={() => {
                        setQaQuestion(q);
                        handleAskQuestion(q);
                      }}
                      className="qa-chip-btn"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {qaLoading && (
                <div className="qa-response-box qa-loading-box">
                  <div className="spinner" style={{ width: '1.25rem', height: '1.25rem', borderWidth: '2px' }}></div>
                  <span>Consulting DisputeGuard analytics facts...</span>
                </div>
              )}

              {qaError && !qaLoading && (
                <div className="ai-error-box" style={{ marginTop: '1rem' }}>
                  <strong>Q&A Request Error:</strong> {qaError}
                </div>
              )}

              {!qaLoading && !qaError && qaResponse && (
                <div className="qa-response-box">
                  <div className="qa-response-header">
                    {qaResponse.grounded ? (
                      <span className="grounded-badge grounded-true">
                        ✓ Grounded in DisputeGuard analytics
                      </span>
                    ) : (
                      <span className="grounded-badge grounded-false">
                        Information not available in current analytics
                      </span>
                    )}
                  </div>
                  <p className="qa-response-text">{qaResponse.answer}</p>
                </div>
              )}
            </div>

            {/* Deterministic Intervention Evaluation Section */}
            {(evaluationLoading || evaluationError || evaluationData) && (
              <div className="section-card">
                <div className="section-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <h2 className="section-title">
                      <Activity style={{ width: '1.25rem', height: '1.25rem', color: 'var(--accent-blue)' }} />
                      Intervention Impact Evaluation
                    </h2>
                    <span className="type-pill" style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa' }}>
                      14-Day Deterministic Window
                    </span>
                  </div>
                </div>

                {evaluationLoading && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1.5rem 0', color: 'var(--text-secondary)' }}>
                    <div className="spinner" style={{ width: '1.5rem', height: '1.5rem', borderWidth: '2px' }}></div>
                    <span>Evaluating intervention performance window...</span>
                  </div>
                )}

                {evaluationError && !evaluationLoading && (
                  <div className="ai-error-box">
                    <strong>Intervention Evaluation Error:</strong> {evaluationError}
                  </div>
                )}

                {!evaluationLoading && !evaluationError && evaluationData && (
                  <div className="forecast-card">
                    <div className="forecast-header-row" style={{ marginBottom: '1.25rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                        <span className={`eval-status-badge ${evaluationData.comparison?.evaluation_status}`}>
                          {evaluationData.comparison?.evaluation_status === 'improved' && 'Improved'}
                          {evaluationData.comparison?.evaluation_status === 'worsened' && 'Worsened'}
                          {evaluationData.comparison?.evaluation_status === 'no_material_change' && 'No Material Change'}
                          {evaluationData.comparison?.evaluation_status === 'insufficient_data' && 'Insufficient Data'}
                        </span>
                        <span className="type-pill" style={{ background: 'rgba(139, 92, 246, 0.1)', color: '#c084fc' }}>
                          Evaluating intervention target: {evaluationData.target_segment}
                        </span>
                        <span className="type-pill">
                          Data Sufficient: {evaluationData.comparison?.is_sufficient_data ? 'yes' : 'no'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Target Segment: <strong style={{ color: 'var(--text-primary)' }}>{evaluationData.target_segment}</strong>
                      </div>
                    </div>

                    {interventionAction && (
                      <div style={{ marginBottom: '1.25rem', padding: '0.75rem 1rem', background: 'rgba(30, 41, 59, 0.6)', borderRadius: '0.5rem', border: '1px solid var(--border-color)' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Action Recorded:
                        </span>
                        <p style={{ fontSize: '0.95rem', fontWeight: 500, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                          "{interventionAction}"
                        </p>
                      </div>
                    )}

                    <div className="forecast-grid">
                      <div className="forecast-metric-item">
                        <span className="forecast-metric-label">Target Segment</span>
                        <span className="forecast-metric-val" style={{ fontSize: '1.05rem' }}>
                          {evaluationData.target_segment}
                        </span>
                      </div>

                      <div className="forecast-metric-item">
                        <span className="forecast-metric-label">Pre-Period Window</span>
                        <span className="forecast-metric-val" style={{ fontSize: '0.95rem' }}>
                          {evaluationData.pre_period?.start_time ? evaluationData.pre_period.start_time.split('T')[0] : 'N/A'} → {evaluationData.pre_period?.end_time ? evaluationData.pre_period.end_time.split('T')[0] : 'N/A'}
                        </span>
                      </div>

                      <div className="forecast-metric-item">
                        <span className="forecast-metric-label">Post-Period Window</span>
                        <span className="forecast-metric-val" style={{ fontSize: '0.95rem' }}>
                          {evaluationData.post_period?.start_time ? evaluationData.post_period.start_time.split('T')[0] : 'N/A'} → {evaluationData.post_period?.end_time ? evaluationData.post_period.end_time.split('T')[0] : 'N/A'}
                        </span>
                      </div>

                      <div className="forecast-metric-item">
                        <span className="forecast-metric-label">Pre Target Dispute Rate</span>
                        <span className="forecast-metric-val" style={{ color: '#ef4444' }}>
                          {evaluationData.pre_period?.segment_dispute_rate !== undefined
                            ? `${(evaluationData.pre_period.segment_dispute_rate * 100).toFixed(2)}%`
                            : 'N/A'}
                        </span>
                      </div>

                      <div className="forecast-metric-item">
                        <span className="forecast-metric-label">Post Target Dispute Rate</span>
                        <span className="forecast-metric-val" style={{ color: evaluationData.comparison?.evaluation_status === 'improved' ? '#34d399' : 'var(--text-primary)' }}>
                          {evaluationData.post_period?.segment_dispute_rate !== undefined
                            ? `${(evaluationData.post_period.segment_dispute_rate * 100).toFixed(2)}%`
                            : 'N/A'}
                        </span>
                      </div>

                      <div className="forecast-metric-item">
                        <span className="forecast-metric-label">Absolute Rate Change</span>
                        <span className="forecast-metric-val">
                          {evaluationData.comparison?.absolute_change !== null && evaluationData.comparison?.absolute_change !== undefined
                            ? `${(evaluationData.comparison.absolute_change * 100).toFixed(2)} percentage points`
                            : 'N/A'}
                        </span>
                      </div>

                      <div className="forecast-metric-item">
                        <span className="forecast-metric-label">Relative Rate Change</span>
                        <span className="forecast-metric-val">
                          {evaluationData.comparison?.relative_change !== null && evaluationData.comparison?.relative_change !== undefined
                            ? `${(evaluationData.comparison.relative_change * 100).toFixed(2)}%`
                            : 'N/A'}
                        </span>
                      </div>

                      <div className="forecast-metric-item">
                        <span className="forecast-metric-label">Data Sufficiency</span>
                        <span className="forecast-metric-val">
                          {evaluationData.comparison?.is_sufficient_data ? 'yes' : 'no'}
                        </span>
                      </div>
                    </div>

                    {/* AI Intervention Explanation Narrative Sub-Section */}
                    <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                        <Sparkles style={{ width: '1.1rem', height: '1.1rem', color: '#c084fc' }} />
                        <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          AI Intervention Narrative
                        </span>
                        <span className="ai-badge" style={{ fontSize: '0.7rem', padding: '0.15rem 0.5rem' }}>
                          Fact-Grounded Explanation
                        </span>
                      </div>

                      {interventionExplanationLoading && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem 0', color: 'var(--text-secondary)' }}>
                          <div className="spinner" style={{ width: '1.25rem', height: '1.25rem', borderWidth: '2px' }}></div>
                          <span>Generating fact-grounded intervention explanation...</span>
                        </div>
                      )}

                      {interventionExplanationError && !interventionExplanationLoading && (
                        <div className="ai-error-box" style={{ marginTop: '0.5rem' }}>
                          <strong>AI Narrative Unavailable:</strong> {interventionExplanationError}
                        </div>
                      )}

                      {!interventionExplanationLoading && !interventionExplanationError && interventionExplanationData && (
                        <div className="ai-explanation-grid">
                          <div className="ai-explanation-box ai-explanation-full">
                            <span className="ai-explanation-label">Executive Overview</span>
                            <p className="ai-explanation-text">{interventionExplanationData.summary}</p>
                          </div>

                          <div className="ai-explanation-box">
                            <span className="ai-explanation-label">Pre vs. Post Comparison</span>
                            <p className="ai-explanation-text">{interventionExplanationData.pre_vs_post_explanation}</p>
                          </div>

                          <div className="ai-explanation-box">
                            <span className="ai-explanation-label">Rate Change & Classification</span>
                            <p className="ai-explanation-text">{interventionExplanationData.change_explanation}</p>
                          </div>

                          <div className="ai-explanation-box ai-explanation-full">
                            <span className="ai-explanation-label">Data Sufficiency Assessment</span>
                            <p className="ai-explanation-text">{interventionExplanationData.data_sufficiency_note}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

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

                          {driver.dominant_dispute_reason && (
                            <div className="driver-metric-item">
                              <span className="driver-metric-label">Dominant Reason</span>
                              <span className="driver-metric-val" style={{ fontSize: '0.9rem', color: '#60a5fa' }}>
                                {driver.dominant_dispute_reason}
                              </span>
                            </div>
                          )}
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
