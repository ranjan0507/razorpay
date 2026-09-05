# RiskWatch
### AI-Powered Chargeback Risk Early Warning System

RiskWatch is an intelligent risk-monitoring system designed to help online merchants detect, explain, forecast, and mitigate chargeback risks before they breach payment network thresholds. By combining a mathematically deterministic analytics engine with a strictly fact-grounded Gemini AI explanation layer, RiskWatch transforms raw payment transaction data into early risk warnings and actionable operational insights.

---

## Problem

E-commerce and subscription merchants face severe penalties, increased processing fees, and payment gateway account suspensions when their chargeback rates exceed card network thresholds (typically 0.9%–2.0% of monthly transactions). 

Traditional risk-monitoring approaches present critical challenges:
- **Late Discovery**: Merchants often discover chargeback spikes weeks after root-cause operational issues occur, after thresholds have already been breached.
- **Hidden Segment Drivers**: Overall chargeback rates mask localized operational failures across specific delivery partners, product lines, or customer segments.
- **Unclear Trajectory**: Merchants lack objective mathematical forecasting to know *when* current dispute trends will cross critical thresholds.
- **Unmeasured Interventions**: Operational fixes (e.g., changing shipping partners) are rarely evaluated against a baseline to measure actual pre- vs. post-intervention dispute reduction.

RiskWatch solves this by providing early detection, dimension-agnostic root-cause identification, threshold forecasting, and closed-loop intervention measurement.

---

## What RiskWatch Does

RiskWatch implements a complete closed-loop risk management workflow:

```text
Detect ──> Explain ──> Forecast ──> Recommend ──> Act ──> Measure
```

1. **Detect**: Continuously calculates monthly cohort dispute rates, baseline rates, and trend slopes from raw transaction and dispute records.
2. **Explain**: Identifies high-lift multi-dimensional segment drivers and generates fact-grounded natural language risk explanations via Gemini AI.
3. **Forecast**: Fits ordinary least-squares (OLS) linear regressions with residual variance windows to project threshold-crossing dates.
4. **Recommend**: Directs merchants to specific, high-risk operational segments and dominant dispute reasons requiring immediate review.
5. **Act**: Records targeted merchant mitigation interventions (e.g., fulfillment workflow updates, policy changes) with exact timestamps.
6. **Measure**: Runs deterministic 14-day pre- vs. post-intervention evaluations to calculate absolute and relative dispute rate reductions in target segments.

---

## Key Features

- **Deterministic Analytics Engine**: Evaluates cohort dispute rates, baseline averages, and trend persistence strictly from raw database records.
- **Transparent 0–100 Risk Score**: Computes a multi-factor numerical risk score composed of threshold proximity, trend slope, trend persistence, and segment anomaly lift.
- **Dimension-Agnostic Segment Driver Analysis**: Dynamically evaluates single-dimension and 2-way dimension combinations (e.g., `Product Category + Delivery Partner`) to pinpoint drivers with highest lift and excess dispute volume.
- **Linear Trend & Crossing Forecast**: Projects estimated threshold-crossing months and flags high-uncertainty forecasts based on residual standard deviations.
- **Gemini-Powered Grounded Explanations**: Generates natural language summaries, trend breakdowns, and segment focus areas strictly bound to analytical facts.
- **Facts-Only Risk Q&A**: Answers merchant questions using verified analytical outputs with explicit grounding validation (`grounded: true/false`).
- **Intervention Tracking**: Logs merchant remediation actions, start dates, and target segments.
- **Deterministic 14-Day Intervention Evaluation**: Compares 14-day pre- and post-intervention dispute rates for targeted segments with sample size and date sufficiency checks.
- **AI Intervention Narrative**: Generates structured explanations of intervention outcomes, rate changes, and data sufficiency assessments.
- **Multi-Merchant Demo Scenarios**: Pre-configured e-commerce and subscription scenarios showcasing low-risk, escalating-risk, and post-intervention recovery paths.

---

## Core Design Principle

> **"The analytics engine calculates metrics and makes risk determinations. AI does not calculate metrics or make decisions; it explains structured analytical findings."**

### Why This Separation Matters

1. **Eliminates LLM Hallucination in Financial Risk**: Language models are prone to arithmetic errors and hallucinated statistics. In RiskWatch, all math (rates, lift, slopes, risk scores, sample sufficiency) is computed deterministically in Python/SQL.
2. **Traceability & Auditability**: Every risk score breakdown point and segment lift factor can be verified against raw database rows.
3. **Strict Fact-Grounding**: Gemini AI is constrained via schema enforcement and prompt rules to explain only pre-computed JSON facts, refusing to invent causes or ungrounded statistics.

---

## Architecture

```text
+-------------------------------------------------------------------+
|               Synthetic Transaction & Dispute Data                |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                SQLite Database (SQLAlchemy ORM)                   |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                  Deterministic Analytics Engine                   |
|  • Cohort Dispute Rates   • OLS Trend Regression & Persistence    |
|  • Segment Driver Lift    • 0–100 Multi-Factor Risk Score         |
|  • Threshold Forecasting  • 14-Day Intervention Pre/Post Eval     |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                  Structured Analytical Findings                   |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|               Gemini AI Explanation Layer (google-genai)          |
|  • Fact-Grounded Risk Summaries  • Structured Schema Output       |
|  • Grounded Q&A Validation       • Intervention AI Narratives     |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                   RiskWatch React/Vite Frontend                   |
|  • Executive Risk Dashboard      • Risk Trajectory Recharts Chart |
|  • Driver Breakdown Cards        • Interactive Grounded Q&A       |
|  • Intervention Evaluation Card  • Light SaaS Visual Design System  |
+-------------------------------------------------------------------+
```

### Layer Responsibilities

- **Storage Layer (`database.py`, `models.py`)**: Manages SQLite transactions, disputes, merchant profiles, and intervention logs using SQLAlchemy.
- **Analytics Engine (`analytics.py`)**: Executes deterministic queries and linear regression models to derive rates, trends, drivers, forecasts, risk scores, and pre/post intervention evaluations.
- **AI Explanation Layer (`ai.py`)**: Formats analytical findings into JSON prompts sent to Google Gemini (`gemini-2.5-flash`), enforcing Pydantic response models. Includes a deterministic fallback generator if the API key is unconfigured.
- **API Server (`main.py`)**: Serves RESTful FastAPI endpoints for analytics, explanations, Q&A, and intervention lifecycle management.
- **Dashboard UI (`App.jsx`, `index.css`)**: Built with React 19, Recharts, and Lucide React, styled in a minimal SaaS light theme inspired by modern financial interfaces.

---

## Analytics Methodology

### 1. Cohort Dispute Rate
Dispute rates are calculated on a transaction monthly cohort basis:

$$\text{Dispute Rate} = \frac{\text{Unique Disputed Transactions in Cohort}}{\text{Total Transactions in Cohort}}$$

### 2. Trend Detection
Trend slope is calculated using Ordinary Least-Squares (OLS) linear regression across monthly dispute rate observations $r_t = a + b \cdot t$:

$$b = \frac{n \sum (t \cdot r_t) - (\sum t)(\sum r_t)}{n \sum t^2 - (\sum t)^2}$$

The trend direction is classified as:
- **Upward**: Slope $b > 0$ and recent period average > historical period average.
- **Downward**: Slope $b < 0$ and recent period average < historical period average.
- **Stable**: Negligible slope or conflicting window averages.

**Trend Persistence** measures the proportion of recent cohort months where the dispute rate exceeds the historical average rate.

### 3. Risk Score (0–100 Weighting)
The composite risk score is a deterministic sum of four components:

| Component | Weight | Formula / Logic |
| :--- | :--- | :--- |
| **Threshold Proximity** | Max 30 pts | $\min\left(30.0, 30.0 \times \frac{\text{Current Rate}}{\text{Risk Threshold}}\right)$ |
| **Trend Slope & Direction** | Max 30 pts | $\min\left(30.0, 30.0 \times \frac{\text{Trend Strength}}{1.0 + \text{Trend Strength}}\right)$ for upward trends |
| **Trend Persistence** | Max 20 pts | $\min\left(20.0, 20.0 \times \text{Trend Persistence}\right)$ |
| **Segment Anomaly** | Max 20 pts | $\min\left(20.0, 20.0 \times \frac{\text{Lift} - 1.0}{\text{Lift}}\right)$ for top observed driver |

### 4. Segment Driver Analysis
The engine evaluates single-dimension attributes (`payment_method`, `product_category`, `delivery_partner`, `geography`, `customer_segment`, `subscription_type`, `transaction_type`) and 2-way dimension combinations:

- **Segment Dispute Rate**: $R_{\text{seg}} = \frac{\text{Disputed Transactions in Segment}}{\text{Total Transactions in Segment}}$
- **Observed Lift**: $\text{Lift} = \frac{R_{\text{seg}}}{\text{Baseline Merchant Rate}}$
- **Excess Disputes**: $\text{Excess} = \text{Segment Disputes} - (\text{Segment Transactions} \times \text{Baseline Merchant Rate})$

Drivers are ranked by **Observed Lift** (requiring positive excess disputes and minimum sample size limits). Dominant dispute reasons within qualifying segments are aggregated to identify specific dispute patterns (e.g., `product_not_received`).

*Note: Segment drivers represent statistical correlations within cohort data and do not establish direct causal proof.*

### 5. Threshold Forecasting
Using OLS regression $r(t) = a + b \cdot t$, RiskWatch estimates the continuous time index $t_{\text{cross}}$ where $r(t) = \text{Risk Threshold}$. 

Residual standard deviation is calculated via:

$$s_{\text{res}} = \sqrt{\frac{\sum (r_i - \hat{r}_i)^2}{n - 2}}$$

If the residual standard deviation exceeds $0.5 \times \text{Risk Threshold}$, the forecast is flagged with `is_highly_uncertain = True`.

### 6. Deterministic Intervention Evaluation
Evaluates recorded remediation actions over fixed 14-day pre- and post-intervention windows:
- **Pre-Period**: $[t_{\text{start}} - 14\text{d}, t_{\text{start}})$
- **Post-Period**: $[t_{\text{start}}, t_{\text{start}} + 14\text{d})$

**Data Sufficiency Checks**:
- Database timestamps must cover the complete 28-day range.
- Target segment must contain $\ge 30$ transactions in both pre- and post-periods.

**Classification Logic** (with absolute tolerance $\epsilon = 0.5\%$):
- **Improved**: $\text{Post Rate} - \text{Pre Rate} < -0.005$
- **Worsened**: $\text{Post Rate} - \text{Pre Rate} > +0.005$
- **No Material Change**: $|\text{Post Rate} - \text{Pre Rate}| \le 0.005$
- **Insufficient Data**: Failed sample size or date range checks.

---

## AI Layer

RiskWatch uses Google Gemini via the official `google-genai` SDK to convert complex analytical payloads into human-readable narratives.

### Key AI Characteristics:
- **Model**: `gemini-2.5-flash` (configurable via environment variable).
- **Structured Schema Enforcement**: Outputs strict JSON matching Pydantic response models (`RiskExplanationResponse`, `RiskQAResponse`, `InterventionExplanationResponse`).
- **Strict Prompt Guardrails**: AI is forbidden from recalculating metrics, creating ungrounded numbers, claiming unproven operational causes, or providing advice outside the provided JSON facts.
- **Grounded Q&A**: Answers merchant questions using pre-computed analytics. Questions outside the dataset return `grounded: false`.
- **Offline Fallback**: If `GEMINI_API_KEY` is not present, RiskWatch defaults to a local deterministic text generator, ensuring 100% application uptime.

---

## Demo Scenarios

RiskWatch provides four pre-configured merchant scenarios:

| ID | Merchant Name | Business Model | Status | Key Characteristics |
| :---: | :--- | :--- | :--- | :--- |
| **1** | Healthy E-commerce | E-commerce | Low Risk | Stable dispute rate (~0.50%) safely below 2.00% threshold. |
| **2** | **Escalating E-commerce** | **E-commerce** | **Escalating / Recovery** | **Primary Demo Path**: Rising dispute rate (1.97% vs 2.00% threshold), strong driver in `Electronics + Partner_C` (8.62% rate, 4.39× lift, `product_not_received`), recorded intervention, and measured 14-day improvement. |
| **3** | Healthy Subscription | Subscription | Low Risk | Low, consistent renewal dispute rate (~0.45%). |
| **4** | Escalating Subscription | Subscription | Warning | Rising dispute rate approaching threshold driven by subscription renewal cohorts. |

### Primary Demonstration Journey: Merchant 2 (Escalating E-commerce)
1. **Detect**: Current dispute rate of **1.97%** approaches the **2.00%** configured risk threshold (Overall Risk Score: **78.47 / 100**).
2. **Explain**: AI explanation highlights an upward trend slope (+0.25% / month) and identifies the top segment driver.
3. **Forecast**: OLS trend projects threshold breach in **2026-03** under current trajectory.
4. **Recommend**: Directs merchant to review `product_category=electronics, delivery_partner=Partner_C` where dispute rate is **8.62%** (4.39× lift, 57.0 excess disputes) dominated by `product_not_received`.
5. **Act**: Recorded intervention: *"Reviewed Partner_C delivery handling for electronics orders"* starting 2026-02-15.
6. **Measure**: Deterministic 14-day pre/post evaluation shows target segment dispute rate dropped from **10.53%** to **2.50%** (-8.03 percentage points), classified as **Improved**.

---

## Tech Stack

### Backend
- **Python**: 3.10+
- **FastAPI**: `0.110.0+` (REST API framework)
- **Uvicorn**: `0.28.0+` (ASGI web server)
- **SQLAlchemy**: `2.0.0+` (ORM & SQLite database interface)
- **Google GenAI SDK**: `google-genai >= 0.1.1` (Gemini API client)
- **Pydantic**: `v2` (Data validation and schema definition)
- **python-dotenv**: `1.0.0+` (Environment variable management)

### Frontend
- **React**: `19.2.8`
- **Vite**: `8.2.2` (Build tool and dev server)
- **Recharts**: `3.10.1` (Data visualization and chart rendering)
- **Lucide React**: `1.41.0` (Icon library)
- **Vanilla CSS**: CSS Custom Properties light design system

---

## Project Structure

```text
riskwatch/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── ai.py                       # Gemini AI prompts, schema & fallback logic
│   │   ├── analytics.py                # Core deterministic analytics & evaluation engine
│   │   ├── database.py                 # SQLite connection & session management
│   │   ├── generate_data.py            # Synthetic transaction & dispute data seed script
│   │   ├── main.py                     # FastAPI routes, schemas & static mount
│   │   └── models.py                   # SQLAlchemy ORM models (Merchant, Transaction, etc.)
│   ├── .env                            # Backend environment file (API keys)
│   ├── disputeguard.db                 # SQLite database file
│   ├── requirements.txt                # Backend Python dependencies
│   ├── test_ai_layer.py                # AI layer unit tests
│   ├── test_intervention_api.py        # Intervention API endpoint tests
│   ├── test_qa_endpoint.py             # Grounded Q&A endpoint tests
│   ├── test_qa_layer.py                # Q&A prompt & schema tests
│   ├── verify_forecast.py              # Forecast calculation verification script
│   ├── verify_frontend_qa_integration.py
│   └── verify_frontend_rec_action.py
└── frontend/
    ├── src/
    │   ├── App.jsx                     # Main React dashboard component
    │   ├── index.css                   # Global light design system CSS
    │   ├── main.jsx                    # React entrypoint
    │   └── assets/
    ├── index.html                      # HTML template
    ├── package.json                    # Frontend npm dependencies and scripts
    └── vite.config.js                  # Vite build configuration
```

---

## Setup & Installation

### Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.0 or higher
- **npm**: 9.0 or higher

### 1. Backend Setup

Navigate to the `backend` directory:
```bash
cd backend
```

Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

Create a `.env` file inside `backend/`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```
*(Note: If `GEMINI_API_KEY` is omitted or left as a placeholder, RiskWatch automatically uses its deterministic fallback engine.)*

Initialize the SQLite database with seed data:
```bash
python -m app.generate_data
```

### 2. Frontend Setup

Navigate to the `frontend` directory:
```bash
cd ../frontend
```

Install npm dependencies:
```bash
npm install
```

---

## Running the Demo

### Step 1: Start Backend Server
From the `backend` directory:
```bash
python -m uvicorn app.main:app --reload --port 8000
```
The FastAPI backend will start at `http://localhost:8000`. You can inspect interactive API documentation at `http://localhost:8000/docs`.

### Step 2: Start Frontend Development Server
From the `frontend` directory in a separate terminal:
```bash
npm run dev
```
The React frontend will start at `http://localhost:5173`.

### Step 3: Explore the Merchant 2 Demo Journey
1. Open `http://localhost:5173` in your browser.
2. Select **Escalating E-commerce (ecommerce)** from the top-right merchant dropdown selector.
3. Observe the **Overall Risk Score (78.47 / 100)**, current dispute rate (**1.97%**), and threshold line on the **Risk Trajectory** chart.
4. Review the **AI Risk Explanation** card to see the Gemini summary, focus area, and recommended action.
5. Inspect the **Strongest Observed Drivers** card to view the `Electronics + Partner_C` lift (**4.39×**) and dominant reason (`product_not_received`).
6. Scroll to **Intervention Impact Evaluation** to review the 14-day pre- vs. post-intervention rate drop (**10.53% → 2.50%**, status: **Improved**).
7. Test the **Ask RiskWatch** section by clicking sample questions or asking custom queries about merchant analytics.

---

## API Endpoints

| Method | Endpoint | Description |
| :---: | :--- | :--- |
| `GET` | `/health` | Server health check (`{"status": "ok"}`). |
| `GET` | `/merchants/{merchant_id}/analytics` | Runs deterministic analytics pipeline (metrics, trend, drivers, risk score, forecast). |
| `GET` | `/merchants/{merchant_id}/explanation` | Generates structured Gemini AI risk explanation narrative from pre-computed analytics. |
| `POST` | `/merchants/{merchant_id}/ask` | Accepts a merchant question JSON (`{"question": "..."}`) and returns a grounded AI response. |
| `GET` | `/merchants/{merchant_id}/interventions` | Retrieves all recorded remediation interventions for a merchant ordered by date descending. |
| `POST` | `/merchants/{merchant_id}/interventions` | Records a new merchant intervention action in the database. |
| `GET` | `/merchants/{merchant_id}/interventions/{intervention_id}/evaluation` | Evaluates deterministic 14-day pre- vs. post-intervention performance for a target segment. |
| `GET` | `/merchants/{merchant_id}/interventions/{intervention_id}/explanation` | Generates structured Gemini AI explanation for an intervention evaluation result. |

---

## Limitations & Design Tradeoffs

RiskWatch is designed as a robust hackathon prototype. The following intentional tradeoffs apply:

1. **Synthetic Demonstration Data**: Database records are generated via `generate_data.py` to model specific risk and recovery scenarios rather than live payment gateway feeds.
2. **Heuristic Risk Scoring**: The 0–100 risk score uses a weighted multi-factor heuristic rather than a machine-learned probabilistic risk model.
3. **Linear Extrapolation Forecasting**: Threshold crossing estimates rely on OLS linear regression over monthly cohorts. While effective for short-term trend projection, linear models do not capture seasonal non-linear shifts.
4. **Observational Segment Driver Analysis**: Segment drivers represent statistical lift and excess dispute volume within historical cohorts. They represent strong observational correlations rather than formal causal proofs.
5. **Fixed Evaluation Window**: Intervention evaluation defaults to a 14-day pre/post window around the recorded intervention start date.

---

## Why This Architecture

RiskWatch deliberately maintains a clear separation between quantitative analytics, AI explanations, and user interface:

- **Deterministic Math Engine**: Guarantees consistency, zero math errors, and 100% reproducible evaluations across runs.
- **Explanatory AI**: Harnesses LLMs for their core strength—natural language synthesis and structured explanation—without exposing financial analytics to LLM instability.
- **Lightweight Stack (FastAPI + SQLite + React)**: Enables zero-overhead deployment, rapid local execution, and effortless auditability for technical reviewers.

---

## Demo Story

When an online merchant's chargeback risk begins escalating, RiskWatch detects the upward trajectory before card network threshold breaches occur. The engine identifies the exact segment driving the anomaly (`Electronics + Partner_C`), while Gemini AI translates the findings into an executive narrative and actionable focus area. When the merchant executes a corrective intervention, RiskWatch measures the subsequent 14-day performance, deterministically confirming an 8.03 percentage point dispute rate reduction and validating that risk has been brought back under control.
