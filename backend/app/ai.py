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
        description="Factual breakdown of strongest observed segment driver(s), including observed lift, excess disputes, and dispute reason breakdown"
    )
    forecast_explanation: str = Field(
        description="Factual explanation of deterministic threshold forecast status, estimated crossing month, and uncertainty state"
    )
    focus_area: str = Field(
        description="Concise merchant-facing operational focus area directing the merchant to review the observed high-risk segment without inferring ungrounded operational causes like product quality or fulfillment failure"
    )
    recommended_action: str = Field(
        description="Concise merchant-facing action recommendation strictly grounded in analytics facts, directing review/investigation of the observed high-risk segment and dominant dispute reason pattern without unsupported causal claims or operational assumptions."
    )

class RiskQAResponse(BaseModel):
    answer: str = Field(
        description="Concise, merchant-facing answer strictly grounded in the supplied analytics facts, or an explanation that the requested information is not available in the supplied analytics."
    )
    grounded: bool = Field(
        description="True if the question can be answered using ONLY the supplied analytics facts. False if the question requires external knowledge, unsupplied data, Razorpay policies, individual customer/transaction details, or unsupported causal speculation."
    )

class InterventionExplanationResponse(BaseModel):
    summary: str = Field(
        description="High-level factual summary of the intervention target segment, evaluation window, and deterministic outcome classification."
    )
    pre_vs_post_explanation: str = Field(
        description="Factual explanation of target-segment dispute rates observed before vs after the intervention start date."
    )
    change_explanation: str = Field(
        description="Factual explanation of absolute and relative rate changes and how they correspond to the deterministic outcome classification (improved, worsened, no_material_change, or insufficient_data)."
    )
    data_sufficiency_note: str = Field(
        description="Factual statement regarding whether data sufficiency requirements (timestamp window coverage and sample size thresholds) were satisfied."
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
    dom_reason_str = ""
    if drivers:
        d0 = drivers[0]
        dims = " + ".join([f"{k}={v}" for k, v in d0.get("values", {}).items()])
        lift = d0.get("lift", 1.0)
        top_driver_str = f"{dims} (Observed Lift: {lift:.2f}x)"
        if d0.get("dominant_dispute_reason"):
            dom_reason_str = f", particularly the observed {d0.get('dominant_dispute_reason')} dispute pattern"
        
    crossing_str = forecast.get("estimated_crossing_month") or "N/A"
    status_str = forecast.get("status", "N/A")
    trend_dir = trend.get("trend_direction", "neutral")

    return RiskExplanationResponse(
        summary=f"DisputeGuard analytics summary for {m_name}: Current monthly dispute rate is {curr_rate:.3f}% against configured threshold of {thresh:.3f}%. ({reason})",
        trend_explanation=f"Observed trend direction is classified as '{trend_dir}' across {trend.get('recent_month_count', 0)} cohort months based on linear regression fit.",
        driver_explanation=f"Strongest observed driver is {top_driver_str}.",
        forecast_explanation=f"Deterministic threshold forecast status is '{status_str}' with estimated crossing month '{crossing_str}'.",
        focus_area=f"Review transactions involving observed high-risk segment {top_driver_str}.",
        recommended_action=f"Prioritize review of transactions in observed high-risk segment {top_driver_str}{dom_reason_str}."
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
6. FOCUS_AREA & RECOMMENDED_ACTION STRICT RULES:
   - Identify the observed high-risk segment driver(s) (e.g. product category, delivery partner, subscription type, transaction type) and direct the merchant toward reviewing/investigating/monitoring transactions in that segment.
   - May reference the observed dominant dispute reason and its percentage share if explicitly present in the facts (e.g., product_not_received, refund_not_processed).
   - Direct the merchant on what area to REVIEW, INVESTIGATE, MONITOR, or PRIORITIZE.
   - Must NOT claim that the segment or dispute reason is proven to cause the risk. Avoid unsupported causal phrases such as "caused by", "causing disputes", "root cause", or "because of".
   - Must NOT infer or invent an operational cause/failure not explicitly represented in the analytics facts (such as "product quality is poor", "fulfillment process is failing", "customer dissatisfaction", "fraud intent", or "payment failure").
   - Must NOT invent specific ungrounded solutions (such as changing vendors, disabling payment methods, changing prices, refunding customers).
   - Prefer language such as "Review...", "Investigate...", "Prioritize review of...", "Monitor...", "Examine the observed dispute pattern in...".
7. If the facts do not support a conclusion, state that the information is insufficient.
8. Do NOT use external information or web searches.
9. Do NOT make unsupported financial, legal, or operational guarantees.

STRUCTURED ANALYTICS FACTS:
{json.dumps(analytics_result, indent=2)}

INSTRUCTIONS FOR YOUR RESPONSE FIELDS:
- summary: High-level factual overview of current merchant dispute rate vs configured threshold.
- trend_explanation: Factual explanation of the observed monthly dispute rate trajectory and trend direction.
- driver_explanation: Factual breakdown of the strongest observed segment driver(s), including observed lift, excess disputes, and dispute reason breakdown.
- forecast_explanation: Factual explanation of the deterministic threshold forecast state, projected breach month (if applicable), and uncertainty state.
- focus_area: Concise merchant-facing operational focus area directing the merchant to review the observed high-risk segment without making ungrounded causal or operational assumptions.
- recommended_action: Concise merchant-facing action recommendation directing the merchant to review, investigate, or prioritize the observed high-risk segment and observed dominant dispute reason pattern without making unsupported causal claims or ungrounded operational assumptions.
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


def answer_risk_question(
    analytics_result: Dict[str, Any],
    question: str,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> RiskQAResponse:
    """
    Answers a merchant Q&A question based strictly on deterministic analytics facts using Gemini AI.

    Does NOT recompute metrics, invent data, make causal claims, or consult external information.
    Sets grounded=False if the question cannot be answered strictly from analytics_result.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not model_name:
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()

    if not api_key:
        return RiskQAResponse(
            answer="Gemini API key is unconfigured. Available DisputeGuard analytics cannot answer questions without AI configuration.",
            grounded=False,
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an expert data-grounded AI assistant for DisputeGuard, answering merchant questions about their chargeback risk analytics.

Your task is to answer the merchant's question strictly using ONLY the provided structured analytics facts.

CRITICAL INSTRUCTIONS & STRICT RULES:
1. Answer ONLY using the supplied analytics facts in the JSON object below.
2. Do NOT calculate or recompute metrics. Use exact numbers, dates, and names provided in the facts.
3. Do NOT invent numbers, dates, causes, probabilities, or unprovided facts.
4. Do NOT make causal claims from observational segment data. Use phrases like "strongest observed driver" or "associated segment" rather than "caused by" or "root cause".
5. Do NOT use external knowledge, Razorpay company policies, external web searches, or real-world facts outside the analytics (e.g., weather, sports, general economics, chargeback regulations).
6. IF THE QUESTION CANNOT BE ANSWERED strictly from the supplied analytics facts (e.g. weather queries, Razorpay external policy questions, individual customer/transaction records, or ungrounded operational causes):
   - Set `grounded` to FALSE (boolean `false`).
   - In `answer`, clearly state that the requested information is not available in the supplied DisputeGuard analytics facts.
7. IF THE QUESTION CAN BE ANSWERED strictly from the supplied analytics facts (e.g. current dispute rate, risk threshold, trend direction, historical vs recent change, persistence, strongest segment drivers, lift, excess disputes, risk score components, threshold forecast, forecast uncertainty):
   - Set `grounded` to TRUE (boolean `true`).
   - Provide a concise, factual, merchant-facing answer strictly grounded in the facts.
8. Do NOT provide unsupported operational, financial, legal, or policy advice.
9. Do NOT expose raw internal code implementation details or database schemas.
10. Keep answers concise and merchant-facing.

MERCHANT QUESTION:
"{question}"

STRUCTURED ANALYTICS FACTS:
{json.dumps(analytics_result, indent=2)}
"""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RiskQAResponse,
                temperature=0.1,
            ),
        )

        if not response or not response.text:
            return RiskQAResponse(
                answer="The analytics AI model returned an empty response.",
                grounded=False,
            )

        qa_response = RiskQAResponse.model_validate_json(response.text)
        return qa_response

    except Exception as e:
        error_msg = f"Unable to answer question due to error: {type(e).__name__}"
        return RiskQAResponse(
            answer=error_msg,
            grounded=False,
        )


def _build_fallback_intervention_explanation(
    evaluation_result: Dict[str, Any], reason: str
) -> InterventionExplanationResponse:
    """Provides a deterministic, fact-grounded fallback explanation for intervention evaluation when Gemini API is unavailable or unconfigured."""
    target_seg = evaluation_result.get("target_segment", "Target Segment")
    window_days = evaluation_result.get("window_days", 14)
    pre = evaluation_result.get("pre_period", {})
    post = evaluation_result.get("post_period", {})
    comp = evaluation_result.get("comparison", {})

    status = comp.get("evaluation_status", "insufficient_data")
    is_sufficient = comp.get("is_sufficient_data", False)
    abs_chg = comp.get("absolute_change")
    rel_chg = comp.get("relative_change")

    pre_rate_pct = pre.get("segment_dispute_rate", 0) * 100
    post_rate_pct = post.get("segment_dispute_rate", 0) * 100

    if not is_sufficient:
        return InterventionExplanationResponse(
            summary=f"Intervention evaluation for segment '{target_seg}' over a {window_days}-day window is classified as '{status}'. ({reason})",
            pre_vs_post_explanation=f"Pre-intervention segment dispute rate was {pre_rate_pct:.2f}% ({pre.get('segment_disputes', 0)} disputes / {pre.get('segment_transactions', 0)} tx); post-intervention segment dispute rate was {post_rate_pct:.2f}% ({post.get('segment_disputes', 0)} disputes / {post.get('segment_transactions', 0)} tx).",
            change_explanation="Data requirements were not met, so comparison values cannot be reliably evaluated.",
            data_sufficiency_note=f"Data sufficiency check failed. Full {window_days}-day timestamp window or minimum sample size requirement (30 tx per period) was not satisfied.",
        )

    abs_str = f"{abs_chg * 100:.2f} percentage points" if abs_chg is not None else "N/A"
    rel_str = f"{rel_chg * 100:.2f}%" if rel_chg is not None else "N/A"

    return InterventionExplanationResponse(
        summary=f"Intervention evaluation for target segment '{target_seg}' over a {window_days}-day window is classified as '{status}'. ({reason})",
        pre_vs_post_explanation=f"In the pre-intervention period, the target-segment dispute rate was {pre_rate_pct:.2f}%. In the post-intervention period following the intervention start date, the target-segment dispute rate was {post_rate_pct:.2f}%.",
        change_explanation=f"Following the intervention, the target-segment dispute rate changed by {abs_str} ({rel_str} relative change), resulting in an evaluation status of '{status}'.",
        data_sufficiency_note=f"Data sufficiency verified: both pre and post periods satisfied the {window_days}-day timestamp coverage and minimum sample size thresholds.",
    )


def generate_intervention_explanation(
    evaluation_result: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> InterventionExplanationResponse:
    """
    Generates a structured, fact-grounded explanation of deterministic intervention evaluation results using Gemini AI.

    Does NOT compute metrics, alter data, invent operational causes, or claim causality.
    Strictly explains the provided evaluation_result object.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not model_name:
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()

    if not api_key:
        return _build_fallback_intervention_explanation(
            evaluation_result,
            reason="Gemini API key is unconfigured. Set GEMINI_API_KEY in backend/.env to enable AI narrative generation.",
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an expert, data-grounded intervention explanation engine for DisputeGuard.
Your role is purely to EXPLAIN the deterministic intervention evaluation facts provided below.

CRITICAL CONSTRAINTS & STRICT RULES:
1. EXPLANATION LAYER ONLY: You are an explanation layer, NOT a calculation engine. Do NOT calculate or recompute any metrics.
2. STRICT GROUNDING: Use ONLY the supplied facts in the JSON object below. Use exact numbers, dates, rates, and target segments provided.
3. NO INVENTIONS: Do NOT invent numbers, dates, causes, probabilities, or unprovided facts.
4. NO CAUSAL CLAIMS: Do NOT claim that the intervention "caused", "produced", "led to", or "resulted in" the observed change.
5. OBSERVATIONAL LANGUAGE: Use observational phrasing such as "after the intervention", "following the intervention start date", or "in the post-intervention period".
6. NO UNGROUNDED OPERATIONAL INFERENCES: Do NOT infer why the intervention worked or failed (e.g. do NOT claim "partner delivery quality improved", "fulfillment process was fixed", or "customer support resolved issues").
7. CLASSIFICATION ALIGNMENT: Conform strictly to the deterministic evaluation_status (improved, worsened, no_material_change, or insufficient_data).
8. INSUFFICIENT DATA: If evaluation_status is "insufficient_data" or is_sufficient_data is false, state clearly that impact cannot be reliably evaluated due to missing data window or sample size constraints.
9. NO EXTERNAL INFORMATION: Do NOT use external knowledge, policy assumptions, or web searches.
10. NO UNSUPPORTED ADVICE: Do NOT provide operational or financial guarantees or advice.

STRUCTURED INTERVENTION EVALUATION FACTS:
{json.dumps(evaluation_result, indent=2)}

INSTRUCTIONS FOR YOUR RESPONSE FIELDS:
- summary: High-level factual summary of the intervention target segment, evaluation window, and deterministic classification status.
- pre_vs_post_explanation: Factual explanation comparing the observed target-segment dispute rates before vs after the intervention start date using observational language.
- change_explanation: Factual explanation of absolute rate change and relative rate change, matching the evaluation_status classification without claiming causality.
- data_sufficiency_note: Factual statement confirming whether data sufficiency criteria (14-day window coverage and sample size thresholds) were met.
"""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=InterventionExplanationResponse,
                temperature=0.2,
            ),
        )

        if not response or not response.text:
            return _build_fallback_intervention_explanation(
                evaluation_result,
                reason="Gemini model returned empty response.",
            )

        explanation = InterventionExplanationResponse.model_validate_json(response.text)
        return explanation

    except Exception as e:
        error_msg = f"Gemini generation error: {type(e).__name__}"
        return _build_fallback_intervention_explanation(evaluation_result, reason=error_msg)


