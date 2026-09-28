from typing import Dict, Any
from flask import current_app
from ..utils.logger import get_logger

logger = get_logger("DataAgent.InsightGenerator")

class InsightGenerator:
    @classmethod
    def generate_insight(
        cls,
        question: str,
        intent: Dict[str, Any],
        evidence: Dict[str, Any],
        answer_text: str
    ) -> str:
        """
        Formulate clear, actionable business insight derived from the verified evidence.
        """
        api_key = None
        try:
            if current_app:
                api_key = current_app.config.get("GEMINI_API_KEY")
        except Exception:
            pass

        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)

                prompt = f"""
You are an Executive Business Intelligence Specialist.
Given:
User Question: "{question}"
Verified Findings: "{answer_text}"
Evidence Breakdown: {evidence.get('breakdown', [])[:5]}
Rows Analyzed: {evidence.get('rows_analyzed', 0)}

Write a concise, 1-2 sentence executive business insight highlighting what this means for decision makers.
Do not repeat raw numbers needlessly. Focus on business impact.
"""
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                return resp.text.strip()
            except Exception as e:
                logger.warning(f"GenAI InsightGenerator error: {e}. Falling back to deterministic insight synthesis.")

        # Deterministic business insight synthesis
        breakdown = evidence.get("breakdown", [])
        if breakdown:
            top_item = breakdown[0]
            ent = top_item.get("entity", "")
            val_str = top_item.get("formatted_value", "")
            group_by = evidence.get("group_by", "segment")
            metric = evidence.get("metric_analyzed", "metric")

            if len(breakdown) > 1:
                second_item = breakdown[1]
                diff_note = f", outpacing {second_item.get('entity', '')} ({second_item.get('formatted_value', '')})"
            else:
                diff_note = ""

            return f"{ent} represents the primary driver for {metric.lower()}{diff_note}. Strategic focus and resource allocation should prioritize this {group_by.lower()}."
        
        return "The analysis indicates significant distribution variance across key business metrics that warrants operational tracking."
