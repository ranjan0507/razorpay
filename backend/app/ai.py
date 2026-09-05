import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from backend/.env if present
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

class RiskExplanationResponse(BaseModel):
    summary: str = Field(
        description="High-level factual summary of current dispute risk situation relative to configured threshold"
    )
    trend_explanation: str = Field(
        description="Factual explanation of monthly dispute rate trajectory and trend classification"
    )
    driver_explanation: str = Field(
        description="Factual breakdown of strongest observed segment driver(s), including observed lift and excess disputes"
    )
    forecast_explanation: str = Field(
        description="Factual explanation of deterministic threshold forecast status, estimated crossing month, and uncertainty state"
    )
    focus_area: str = Field(
        description="Concise merchant-facing operational focus area focused on the strongest observed drivers"
    )

def _build_fallback_explanation(analytics_result: Dict[str, Any], reason: str) -> RiskExplanationResponse:
    """Provides a deterministic, fact-grounded fallback explanation when Gemini API is unavailable or unconfigured."""
    merchant = analytics_result.get("merchant", {})
    overall = analytics_result.get("overall_metrics", {})
    trend = analytics_result.get("trend", {})
    drivers = analytics_result.get("segment_drivers", [])
    forecast = analytics_result.get("forecast", {})

    m_name = merchant.get("name", "Merchant")
    curr_rate = overall.get("current_dispute_rate", 0) * 100
    thresh = merchant.get("risk_threshold", 0.02) * 100
    
    top_driver_str = "None detected"
    if drivers:
        d0 = drivers[0]
        dims = " + ".join([f"{k}={v}" for k, v in d0.get("values", {}).items()])
        lift = d0.get("lift", 1.0)
        top_driver_str = f"{dims} (Observed Lift: {lift:.2f}x)"
        
    crossing_str = forecast.get("estimated_crossing_month") or "N/A"
    status_str = forecast.get("status", "N/A")
    trend_dir = trend.get("trend_direction", "neutral")

    return RiskExplanationResponse(
        summary=f"DisputeGuard analytics summary for {m_name}: Current monthly dispute rate is {curr_rate:.3f}% against configured threshold of {thresh:.3f}%. ({reason})",
        trend_explanation=f"Observed trend direction is classified as '{trend_dir}' across {trend.get('recent_month_count', 0)} cohort months based on linear regression fit.",
        driver_explanation=f"Strongest observed driver is {top_driver_str}.",
        forecast_explanation=f"Deterministic threshold forecast status is '{status_str}' with estimated crossing month '{crossing_str}'.",
        focus_area=f"Prioritize monitoring high-risk segment {top_driver_str} and track monthly cohort dispute rates against threshold."
    )

def generate_risk_explanation(
    analytics_result: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> RiskExplanationResponse:
    """
    Generates a structured, fact-grounded explanation of deterministic analytics outputs using Gemini AI.
    
    Does NOT compute or alter metrics. Strictly explains the provided analytics_result object.
    """
    # Resolve API key & Model name from env vars if not passed explicitly
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not model_name:
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()

    # Check if API key is present
    if not api_key:
        return _build_fallback_explanation(
            analytics_result,
            reason="Gemini API key is unconfigured. Set GEMINI_API_KEY in backend/.env to enable AI narrative generation."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an expert, data-grounded chargeback risk explanation engine for DisputeGuard.
Your role is purely to EXPLAIN the already-computed deterministic analytics results provided below.

CRITICAL CONSTRAINTS:
1. You are an EXPLANATION layer, NOT a calculation or analytics layer.
2. Use ONLY the supplied structured facts in the JSON object below.
3. Do NOT calculate or recompute any metrics.
4. Do NOT invent numbers, dates, causes, probabilities, or other unprovided facts.
5. Do NOT make causal claims from observational segment data. Use terms like "strongest observed driver" or "associated segment" rather than "caused by" or "root cause".
6. If the facts do not support a conclusion, state that the information is insufficient.
7. Do NOT use external information or web searches.
8. Do NOT make unsupported financial, legal, or operational guarantees.

STRUCTURED ANALYTICS FACTS:
{json.dumps(analytics_result, indent=2)}

INSTRUCTIONS FOR YOUR RESPONSE FIELDS:
- summary: High-level factual overview of current merchant dispute rate vs configured threshold.
- trend_explanation: Factual explanation of the observed monthly dispute rate trajectory and trend direction.
- driver_explanation: Factual breakdown of the strongest observed segment driver(s), including observed lift and excess disputes.
- forecast_explanation: Factual explanation of the deterministic threshold forecast state, projected breach month (if applicable), and uncertainty state.
- focus_area: Concise merchant-facing operational focus area focused on the strongest observed driver.
"""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RiskExplanationResponse,
                temperature=0.2,
            ),
        )

        if not response or not response.text:
            return _build_fallback_explanation(
                analytics_result,
                reason="Gemini model returned empty response."
            )

        explanation = RiskExplanationResponse.model_validate_json(response.text)
        return explanation

    except Exception as e:
        # Secure error handling: do not expose API keys or sensitive error stack traces in return object
        error_msg = f"Gemini generation error: {type(e).__name__}"
        return _build_fallback_explanation(analytics_result, reason=error_msg)
