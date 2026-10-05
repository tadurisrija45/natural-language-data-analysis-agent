"""
AI-powered next-question recommendation generator.
Produces 3-4 context-aware follow-up business questions based on
current query/code, analysis findings, dataset schemas, relationships,
and session history.
"""

import json
import re
from typing import Dict, Any, List, Optional
from flask import current_app
from ..utils.logger import get_logger

logger = get_logger("DataAgent.SuggestionGenerator")


class SuggestionGenerator:
    @classmethod
    def generate_suggestions(
        cls,
        current_input: str,
        current_result: Dict[str, Any],
        datasets_meta: Dict[str, Any],
        session_history: Optional[List[str]] = None,
        mode: str = "natural_language"
    ) -> List[str]:
        """
        Generate 3-4 relevant follow-up questions tailored to the current analysis results.
        Tries Gemini API first if configured, falling back to a deterministic schema-aware rule engine.
        """
        history_normalized = set()
        if session_history:
            for q in session_history:
                if q:
                    history_normalized.add(q.strip().lower())
        if current_input:
            history_normalized.add(current_input.strip().lower())

        # Attempt Gemini AI generation first
        api_key = None
        try:
            if current_app:
                api_key = current_app.config.get("GEMINI_API_KEY")
        except Exception:
            pass

        ai_suggestions = []
        if api_key:
            try:
                ai_suggestions = cls._generate_gemini_suggestions(
                    api_key=api_key,
                    current_input=current_input,
                    current_result=current_result,
                    datasets_meta=datasets_meta,
                    history_normalized=history_normalized,
                    mode=mode
                )
            except Exception as e:
                logger.warning(f"Gemini suggestion generation failed: {e}. Falling back to deterministic engine.")

        if ai_suggestions and len(ai_suggestions) >= 3:
            return ai_suggestions[:4]

        # Use deterministic schema-aware suggestion engine
        deterministic_suggestions = cls._generate_deterministic_suggestions(
            current_input=current_input,
            current_result=current_result,
            datasets_meta=datasets_meta,
            history_normalized=history_normalized,
            mode=mode
        )

        # Merge any Gemini suggestions with deterministic suggestions
        combined = []
        for s in ai_suggestions + deterministic_suggestions:
            s_clean = s.strip()
            if s_clean and s_clean.lower() not in history_normalized and s_clean not in combined:
                combined.append(s_clean)
            if len(combined) >= 4:
                break

        return combined[:4] if combined else [
            "What are the top 5 highest values by category?",
            "What is the overall summary and distribution of the dataset?",
            "How do key metrics compare across groups?"
        ]

    @classmethod
    def _generate_gemini_suggestions(
        cls,
        api_key: str,
        current_input: str,
        current_result: Dict[str, Any],
        datasets_meta: Dict[str, Any],
        history_normalized: set,
        mode: str
    ) -> List[str]:
        from google import genai

        client = genai.Client(api_key=api_key)

        # Build schema summary
        schema_lines = []
        for name, meta in datasets_meta.items():
            cols = meta.get("columns", [])
            num_cols = meta.get("numerical_columns", [])
            cat_cols = meta.get("categorical_columns", [])
            date_cols = meta.get("date_columns", [])
            schema_lines.append(
                f"- Dataset '{name}' ({meta.get('rows', 0)} rows): "
                f"Numeric=[{', '.join(num_cols)}], Categorical=[{', '.join(cat_cols)}], Dates=[{', '.join(date_cols)}]"
            )
        schema_summary = "\n".join(schema_lines)

        answer_summary = current_result.get("answer", "")
        metric_analyzed = current_result.get("evidence", {}).get("metric_analyzed", "")
        group_by = current_result.get("evidence", {}).get("group_by", "")

        prompt = f"""You are a Lead Business Intelligence Analyst.
The user just performed an analysis ({mode} mode):
User Input: "{current_input}"
Analysis Result: "{answer_summary}"
Metric Analyzed: {metric_analyzed}
Group By: {group_by}

Available Datasets and Schemas:
{schema_summary}

Generate exactly 3 to 4 logical, insightful follow-up business questions that:
1. Directly deepen the insight from the previous result (e.g. breakdown, root cause, time trend, segment comparison, or cross-dataset correlation).
2. ONLY reference columns and tables that actually exist in the schema above.
3. Are NOT already in this list of previously asked questions: {list(history_normalized)[:10]}
4. Are phrased as natural, clickable questions (concise, under 15 words).

Return ONLY a JSON array of 3 or 4 strings, e.g.:
["Question 1?", "Question 2?", "Question 3?", "Question 4?"]"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = response.text.strip()
        # Parse JSON array
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            questions = json.loads(match.group(0))
            valid = []
            for q in questions:
                if isinstance(q, str):
                    clean_q = q.strip().rstrip(".").strip()
                    if not clean_q.endswith("?"):
                        clean_q += "?"
                    if clean_q.lower() not in history_normalized:
                        valid.append(clean_q)
            return valid

        return []

    @classmethod
    def _generate_deterministic_suggestions(
        cls,
        current_input: str,
        current_result: Dict[str, Any],
        datasets_meta: Dict[str, Any],
        history_normalized: set,
        mode: str
    ) -> List[str]:
        suggestions = []

        # Extract current analysis context
        evidence = current_result.get("evidence", {}) or {}
        curr_metric = evidence.get("metric_analyzed", "").lower()
        curr_group = evidence.get("group_by", "").lower()
        breakdown = evidence.get("breakdown", []) or []

        # Extract top entity if present
        top_entity = None
        if breakdown and isinstance(breakdown, list) and len(breakdown) > 0:
            first_item = breakdown[0]
            if isinstance(first_item, dict) and "entity" in first_item:
                top_entity = str(first_item["entity"]).strip()

        # Gather all columns across datasets
        all_numeric = []
        all_categorical = []
        all_date = []
        dataset_names = list(datasets_meta.keys())

        for ds_name, meta in datasets_meta.items():
            for c in meta.get("numerical_columns", []):
                if c.lower() not in [x.lower() for x in all_numeric]:
                    all_numeric.append(c)
            for c in meta.get("categorical_columns", []):
                if c.lower() not in [x.lower() for x in all_categorical]:
                    all_categorical.append(c)
            for c in meta.get("date_columns", []):
                if c.lower() not in [x.lower() for x in all_date]:
                    all_date.append(c)

        # Format helper
        def pretty(col_name: str) -> str:
            return col_name.replace("_", " ").title()

        # 1. Deep dive into the leading entity
        if top_entity and top_entity.lower() not in ["none", "null", "all", "unknown"]:
            other_numeric = [n for n in all_numeric if n.lower() != curr_metric.lower()]
            if other_numeric:
                q = f"What is the total {pretty(other_numeric[0])} for {top_entity}?"
                if q.lower() not in history_normalized:
                    suggestions.append(q)
            elif all_date:
                q = f"What is the trend over time for {top_entity}?"
                if q.lower() not in history_normalized:
                    suggestions.append(q)

        # 2. Pivot to another dimension with current metric
        metric_to_use = curr_metric if curr_metric and curr_metric != "metric" else (all_numeric[0] if all_numeric else "revenue")
        other_cats = [c for c in all_categorical if c.lower() != curr_group.lower() and c.lower() not in ["id", "_id", "index"]]
        for alt_cat in other_cats[:2]:
            q = f"How does {pretty(metric_to_use)} compare across different {pretty(alt_cat)}s?"
            if q.lower() not in history_normalized and q not in suggestions:
                suggestions.append(q)

        # 3. Time series trend if date column exists
        if all_date:
            date_col = all_date[0]
            q = f"What is the monthly trend of {pretty(metric_to_use)} by {pretty(date_col)}?"
            if q.lower() not in history_normalized and q not in suggestions:
                suggestions.append(q)

        # 4. Multi-dataset cross-analysis / relationship suggestion
        if len(dataset_names) >= 2:
            ds1_stem = dataset_names[0].split(".")[0].title()
            ds2_stem = dataset_names[1].split(".")[0].title()
            q = f"How do {ds1_stem} metrics correlate with {ds2_stem} data?"
            if q.lower() not in history_normalized and q not in suggestions:
                suggestions.append(q)

        # 5. Top vs Bottom ranking / Distribution
        if other_cats and all_numeric:
            q = f"Which {pretty(other_cats[0])} has the lowest {pretty(all_numeric[0])}?"
            if q.lower() not in history_normalized and q not in suggestions:
                suggestions.append(q)

        # 6. Secondary metric ranking
        if len(all_numeric) > 1 and all_categorical:
            q = f"What are the top 5 {pretty(all_categorical[0])}s by {pretty(all_numeric[1])}?"
            if q.lower() not in history_normalized and q not in suggestions:
                suggestions.append(q)

        # Fillers if fewer than 3
        generic_fillers = [
            "What is the overall average and standard deviation of key metrics?",
            "Which categories represent the top 80% of total volume?",
            "Are there any notable outliers or anomalies in the dataset?",
            "What is the complete statistical distribution of the uploaded data?"
        ]
        for gf in generic_fillers:
            if len(suggestions) >= 4:
                break
            if gf.lower() not in history_normalized and gf not in suggestions:
                suggestions.append(gf)

        return suggestions[:4]
