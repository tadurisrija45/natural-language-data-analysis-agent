import json
import re
from typing import Dict, Any, List, Optional
from flask import current_app
from ..utils.logger import get_logger

logger = get_logger("DataAgent.QuestionAnalyzer")

class QuestionAnalyzer:
    @classmethod
    def analyze_question(
        cls,
        question: str,
        datasets_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze user natural language business question and extract structured intent.
        Attempts to use modern Google GenAI SDK if API key is configured,
        otherwise uses deterministic heuristic NLP pipeline.
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
                
                # Build context about available datasets
                schema_context = []
                for ds_name, meta in datasets_meta.items():
                    schema_context.append(
                        f"Dataset: {ds_name}, Columns: {meta.get('columns', [])}, "
                        f"Numerical: {meta.get('numerical_columns', [])}, "
                        f"Categorical: {meta.get('categorical_columns', [])}, "
                        f"Date: {meta.get('date_columns', [])}"
                    )
                schema_str = "\n".join(schema_context)

                prompt = f"""
You are a Lead Data Analyst. Given the following datasets and schemas:
{schema_str}

Analyze the user's business question:
"{question}"

Extract the structured analysis intent in strictly valid JSON format with keys:
- "analysis_type": one of ["ranking", "count", "total", "profit_margin", "time_series", "groupby_aggregation", "comparison"]
- "target_dataset": name of the primary dataset
- "selected_datasets": list of all dataset names required to answer this question (e.g. multiple if join needed)
- "group_by": name of column to group by or categorize (or null)
- "metric": name of numerical column to measure/aggregate (or null)
- "aggregation": "sum", "mean", "count", "max", "min"
- "sort": "descending" or "ascending"
- "limit": integer limit (e.g. 1 for highest/lowest, 5 for top 5, or null)
- "chart_type": "bar", "horizontalBar", "line", "doughnut", or null
- "title": human-friendly brief analysis title

Return ONLY raw JSON, with no markdown code fences or other text.
"""
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                raw_text = resp.text.strip()
                if "```" in raw_text:
                    raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
                    raw_text = re.sub(r"\n?```$", "", raw_text)
                parsed = json.loads(raw_text.strip())
                if "selected_datasets" not in parsed or not parsed["selected_datasets"]:
                    parsed["selected_datasets"] = [parsed.get("target_dataset")] if parsed.get("target_dataset") else list(datasets_meta.keys())[:1]
                return parsed
            except Exception as e:
                logger.warning(f"GenAI QuestionAnalyzer error: {e}. Falling back to deterministic NLP analyzer.")

        return cls._heuristic_analyze(question, datasets_meta)

    @classmethod
    def _heuristic_analyze(
        cls,
        question: str,
        datasets_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        High-precision deterministic NLP question analyzer.
        Dynamically adapts to ANY uploaded dataset schema without relying on hardcoded columns.
        Supports:
        - Dataset summaries / overviews
        - Dataset comparisons
        - Scalar metrics (mean, sum, median, min, max, count, nunique) without artificial grouping
        - Grouped aggregations & rankings (with correct aggregation functions)
        - Cross-dataset joins
        - Time series / trend analysis
        - Profit margin analysis
        """
        q_lower = question.lower().strip()
        if not datasets_meta:
            return {
                "analysis_type": "dataset_summary",
                "target_dataset": "dataset",
                "selected_datasets": [],
                "group_by": None,
                "metric": None,
                "aggregation": "count",
                "sort": "descending",
                "limit": None,
                "chart_type": None,
                "title": "Dataset Analysis"
            }

        ds_names = list(datasets_meta.keys())
        first_ds = ds_names[0]

        # 1. Dataset Overview / Summary Intent
        is_summary = any(w in q_lower for w in [
            "summary", "summarize", "overview", "describe", "profile", "tell me about",
            "what is this data", "explain the dataset", "explain this data", "about this data",
            "show columns", "data summary", "dataset overview"
        ]) and not any(w in q_lower for w in ["by ", "per ", "highest", "lowest", "compare", "margin", "trend", "versus"])

        if is_summary:
            target_ds = first_ds
            for d in ds_names:
                if d.split(".")[0].lower() in q_lower:
                    target_ds = d
                    break
            return {
                "analysis_type": "dataset_summary",
                "target_dataset": target_ds,
                "selected_datasets": [target_ds],
                "group_by": None,
                "metric": None,
                "aggregation": "summary",
                "sort": "descending",
                "limit": None,
                "chart_type": None,
                "title": f"Dataset Summary: {target_ds.split('.')[0].replace('_', ' ').title()}"
            }

        # 2. Dataset Comparison Intent
        is_dataset_comparison = (
            any(w in q_lower for w in [
                "compare both", "compare datasets", "compare the datasets", "compare two datasets",
                "compare data", "comparison between both", "compare the two", "difference between both",
                "compare both files"
            ]) or (
                ("compare" in q_lower or "versus" in q_lower or " vs " in q_lower or "difference" in q_lower)
                and len(datasets_meta) >= 2
                and not any(w in q_lower for w in ["by ", "per ", "across ", "highest", "lowest", "margin"])
            )
        )

        if is_dataset_comparison and len(datasets_meta) >= 2:
            matched_ds = []
            for d in ds_names:
                stem = d.split(".")[0].lower()
                if stem in q_lower:
                    matched_ds.append(d)
            if len(matched_ds) < 2:
                for d in ds_names:
                    if d not in matched_ds:
                        matched_ds.append(d)
                    if len(matched_ds) == 2:
                        break

            return {
                "analysis_type": "dataset_comparison",
                "target_dataset": matched_ds[0],
                "selected_datasets": matched_ds,
                "group_by": "dataset",
                "metric": "rows",
                "aggregation": "sum",
                "sort": "descending",
                "limit": 2,
                "chart_type": "bar",
                "title": f"Dataset Comparison: {matched_ds[0]} vs {matched_ds[1]}"
            }

        # 3. Profit Margin Intent
        is_margin = any(w in q_lower for w in ["profit margin", "margin", "profit %", "percentage profit", "markup"])
        if is_margin:
            target_ds = None
            for d, meta in datasets_meta.items():
                cols = [c.lower() for c in meta.get("columns", [])]
                if "profit_margin" in cols or ("price" in cols and "cost" in cols) or "margin" in cols:
                    target_ds = d
                    break
            if not target_ds:
                for d in ds_names:
                    if "product" in d.lower():
                        target_ds = d
                        break
            if not target_ds:
                target_ds = first_ds

            meta = datasets_meta.get(target_ds, {})
            p_col = "product_name" if "product_name" in meta.get("columns", []) else (
                "product_id" if "product_id" in meta.get("columns", []) else meta.get("categorical_columns", [None])[0]
            )
            is_ranking = any(w in q_lower for w in ["highest", "lowest", "top", "bottom", "best", "worst", "most", "least"])
            is_lowest = any(w in q_lower for w in ["lowest", "bottom", "least", "worst", "minimum", "min"])
            return {
                "analysis_type": "profit_margin",
                "target_dataset": target_ds,
                "selected_datasets": [target_ds],
                "group_by": p_col,
                "metric": "profit_margin",
                "aggregation": "max" if is_ranking else "mean",
                "sort": "ascending" if is_lowest else "descending",
                "limit": 1 if is_ranking else 10,
                "chart_type": "horizontalBar" if is_ranking else "bar",
                "title": "Product Profit Margin Analysis"
            }

        # 4. Time Series / Trend Intent
        is_trend = any(w in q_lower for w in ["over time", "trend", "monthly", "yearly", "timeline", "by date", "change over", "through time", "by month", "by year"])

        # 5. Build Dynamic Column Catalog from all uploaded datasets
        col_catalog = []
        for d, meta in datasets_meta.items():
            for c in meta.get("columns", []):
                c_str = str(c)
                is_num = c_str in meta.get("numerical_columns", [])
                is_dt = c_str in meta.get("date_columns", [])
                c_type = "numerical" if is_num else ("date" if is_dt else "categorical")
                c_clean = re.sub(r"[_\-\s]+", " ", c_str.lower()).strip()
                col_catalog.append({
                    "original": c_str,
                    "dataset": d,
                    "type": c_type,
                    "clean": c_clean,
                    "stems": [t.rstrip("s") for t in c_clean.split() if len(t) > 2]
                })

        # Known domain synonym mappings to assist fuzzy matching
        metric_synonyms = {
            "revenue": ["revenue", "sales", "turnover", "inflow", "amount", "total sales", "gross sales"],
            "profit": ["profit", "earnings", "net income", "margin"],
            "cost": ["cost", "expense", "unit_cost", "spend", "expenditure"],
            "price": ["price", "unit_price", "rate", "cost_price", "mrp"],
            "quantity": ["quantity", "volume", "units", "items", "qty", "number of items"],
            "salary": ["salary", "pay", "wage", "compensation", "income", "ctc"],
            "age": ["age", "years old"],
            "score": ["score", "marks", "grade", "points", "rating"],
            "rating": ["rating", "stars", "review"],
            "discount": ["discount", "rebate", "concession"]
        }

        group_synonyms = {
            "region": ["region", "territory", "zone", "area", "location", "geography"],
            "segment": ["segment", "customer segment", "customer_segment", "tier", "market"],
            "customer_name": ["customer", "client", "buyer", "customer name", "who"],
            "product_name": ["product", "item", "product name", "goods", "sku", "title"],
            "category": ["category", "sub_category", "type", "department", "genre"],
            "order_date": ["date", "month", "order_date", "day", "year", "time", "period"],
            "department": ["department", "dept", "division", "unit", "team"],
            "status": ["status", "state", "condition", "stage"],
            "city": ["city", "town", "metro"],
            "gender": ["gender", "sex"]
        }

        # 6. Aggregation Detection
        agg_op = "sum"
        is_mean = any(w in q_lower for w in ["average", "avg", "mean", "norm"])
        is_median = any(w in q_lower for w in ["median", "middle"])
        is_min = any(w in q_lower for w in ["minimum", "min"])
        is_max = any(w in q_lower for w in ["maximum", "max", "peak"])
        is_count = any(w in q_lower for w in ["how many", "count of", "number of", "quantity of", "frequency", "occurrences", "row count", "total records"])
        is_unique = any(w in q_lower for w in ["unique", "distinct", "different"])

        if is_mean:
            agg_op = "mean"
        elif is_median:
            agg_op = "median"
        elif is_min:
            agg_op = "min"
        elif is_max:
            agg_op = "max"
        elif is_count:
            agg_op = "count"
        elif is_unique:
            agg_op = "nunique"
        else:
            agg_op = "sum"

        by_match = re.search(r"\b(?:by|per|across|for each|in each|grouped by|split by)\s+([a-zA-Z0-9_\s]+)", q_lower)

        # 6.5 Pure Count Question (e.g. "How many customers are there?", "Count of rows", "Number of orders")
        if is_count and not by_match and not any(w in q_lower for w in ["revenue", "sales", "profit", "salary", "spend", "amount", "price"]):
            target_ds = first_ds
            for d in ds_names:
                stem = d.split(".")[0].lower().rstrip("s")
                if stem in q_lower or (stem in ["customer", "order", "product"] and stem in q_lower):
                    target_ds = d
                    break
            title = f"Total {target_ds.split('.')[0].replace('_', ' ').title()} Count"
            return {
                "analysis_type": "count",
                "target_dataset": target_ds,
                "selected_datasets": [target_ds],
                "group_by": None,
                "metric": "count",
                "aggregation": "count",
                "sort": "descending",
                "limit": None,
                "chart_type": None,
                "title": title
            }

        # 7. Check for explicit Group-By clause (e.g. "by region", "per segment", "across department", "for each customer")
        detected_group_by = None
        group_by_dataset = None

        if by_match:
            target_phrase = by_match.group(1).strip()
            # Match against column catalog
            best_score = 0
            for item in col_catalog:
                score = 0
                if item["clean"] in target_phrase or target_phrase in item["clean"]:
                    score = 10
                elif any(s in target_phrase for s in item["stems"]):
                    score = 5
                if score > best_score:
                    best_score = score
                    detected_group_by = item["original"]
                    group_by_dataset = item["dataset"]

        # If not found via 'by', match columns mentioned anywhere in question
        if not detected_group_by:
            # First check group synonyms
            for syn_key, syn_list in group_synonyms.items():
                if any(s in q_lower for s in syn_list):
                    for item in col_catalog:
                        if item["type"] in ["categorical", "date"]:
                            if item["clean"] == syn_key or any(s in item["clean"] for s in syn_list):
                                detected_group_by = item["original"]
                                group_by_dataset = item["dataset"]
                                break
                    if detected_group_by:
                        break

        # If still not found, check all categorical and date columns in catalog
        if not detected_group_by:
            for item in col_catalog:
                if item["type"] in ["categorical", "date"]:
                    if len(item["clean"]) >= 3 and (f" {item['clean']} " in f" {q_lower} " or any(f" {st} " in f" {q_lower} " for st in item["stems"])):
                        detected_group_by = item["original"]
                        group_by_dataset = item["dataset"]
                        break

        # 8. Detect Metric Column
        detected_metric = None
        metric_dataset = None

        # Check metric synonyms first
        for syn_key, syn_list in metric_synonyms.items():
            if any(s in q_lower for s in syn_list):
                for item in col_catalog:
                    if item["type"] == "numerical":
                        if item["clean"] == syn_key or any(s in item["clean"] for s in syn_list):
                            detected_metric = item["original"]
                            metric_dataset = item["dataset"]
                            break
                if detected_metric:
                    break

        # Check direct mention of any numerical column
        if not detected_metric:
            for item in col_catalog:
                if item["type"] == "numerical":
                    if len(item["clean"]) >= 3 and (f" {item['clean']} " in f" {q_lower} " or any(f" {st} " in f" {q_lower} " for st in item["stems"])):
                        detected_metric = item["original"]
                        metric_dataset = item["dataset"]
                        break

        # Fallback metric if none detected
        if not detected_metric:
            # If dataset has numerical columns, pick first one
            for d, meta in datasets_meta.items():
                nums = meta.get("numerical_columns", [])
                if nums:
                    detected_metric = nums[0]
                    metric_dataset = d
                    break

        # 9. Time Series Handler
        if is_trend:
            date_col = None
            date_ds = None
            for item in col_catalog:
                if item["type"] == "date" or "date" in item["clean"] or "time" in item["clean"] or "year" in item["clean"] or "month" in item["clean"]:
                    date_col = item["original"]
                    date_ds = item["dataset"]
                    break
            target_ds = metric_dataset or date_ds or first_ds
            selected_ds = list(dict.fromkeys([target_ds, date_ds] if date_ds else [target_ds]))
            return {
                "analysis_type": "time_series",
                "target_dataset": target_ds,
                "selected_datasets": selected_ds,
                "group_by": date_col or "order_date",
                "metric": detected_metric or "revenue",
                "aggregation": "sum",
                "sort": "ascending",
                "limit": None,
                "chart_type": "line",
                "title": f"{str(detected_metric or 'Metric').replace('_', ' ').title()} Over Time"
            }

        # 10. Pure Count Question (e.g. "How many customers are there?", "Count of rows")
        if is_count and not detected_group_by and not any(w in q_lower for w in ["revenue", "sales", "profit", "salary", "spend", "amount", "price"]):
            # Identify target dataset from entity mentioned
            target_ds = first_ds
            for d in ds_names:
                stem = d.split(".")[0].lower().rstrip("s")
                if stem in q_lower:
                    target_ds = d
                    break
            title = f"Total {target_ds.split('.')[0].replace('_', ' ').title()} Count"
            return {
                "analysis_type": "count",
                "target_dataset": target_ds,
                "selected_datasets": [target_ds],
                "group_by": None,
                "metric": "count",
                "aggregation": "count",
                "sort": "descending",
                "limit": None,
                "chart_type": None,
                "title": title
            }

        # 11. Scalar Metric Question (e.g. "What is the average revenue?", "Total revenue?", "What is the minimum age?", "Highest salary?")
        # When NO group_by column is requested, compute overall metric across the dataset!
        has_ranking_keyword = any(w in q_lower for w in ["which", "who", "highest", "lowest", "top", "bottom", "best", "worst", "most", "least"])
        is_scalar = (not detected_group_by and not has_ranking_keyword) or (
            any(w in q_lower for w in ["total", "overall", "average", "avg", "mean", "median"])
            and not any(w in q_lower for w in ["which", "who", "by ", "per ", "across ", "each"])
            and not detected_group_by
        )

        if is_scalar:
            target_ds = metric_dataset or first_ds
            m_label = str(detected_metric or 'Value').replace('_', ' ').title()
            agg_label = agg_op.capitalize() if agg_op != "sum" else "Total"
            return {
                "analysis_type": "scalar_metric",
                "target_dataset": target_ds,
                "selected_datasets": [target_ds],
                "group_by": None,
                "metric": detected_metric,
                "aggregation": agg_op,
                "sort": "descending",
                "limit": None,
                "chart_type": None,
                "title": f"{agg_label} {m_label} Analysis"
            }

        # 12. Group-By Aggregations & Rankings
        # If no group_by was detected yet but ranking is asked (e.g. "Which region generated highest sales?"):
        if not detected_group_by:
            # Check for region, segment, customer, product in question
            if "region" in q_lower:
                detected_group_by = "region"
            elif "segment" in q_lower:
                detected_group_by = "segment"
            elif "customer" in q_lower:
                detected_group_by = "customer_name"
            elif "product" in q_lower:
                detected_group_by = "product_name"
            else:
                # Pick first categorical column that is not an ID
                for item in col_catalog:
                    if item["type"] == "categorical" and not item["original"].endswith("_id"):
                        detected_group_by = item["original"]
                        group_by_dataset = item["dataset"]
                        break

        # Resolve dataset locations
        if not group_by_dataset and detected_group_by:
            for item in col_catalog:
                if item["original"] == detected_group_by:
                    group_by_dataset = item["dataset"]
                    break

        selected_datasets = []
        if metric_dataset:
            selected_datasets.append(metric_dataset)
        if group_by_dataset and group_by_dataset not in selected_datasets:
            selected_datasets.append(group_by_dataset)

        if not selected_datasets:
            selected_datasets = [first_ds]

        target_ds = selected_datasets[0]

        limit = None
        if "top 5" in q_lower:
            limit = 5
        elif "top 10" in q_lower:
            limit = 10
        elif has_ranking_keyword:
            limit = 1

        sort_order = "ascending" if is_min else "descending"
        analysis_type = "ranking" if (has_ranking_keyword or limit == 1) else "groupby_aggregation"
        chart_type = "horizontalBar" if (analysis_type == "ranking" and limit == 1) else "bar"

        g_label = str(detected_group_by or "Category").replace("_", " ").title()
        m_label = str(detected_metric or "Value").replace("_", " ").title()
        title = f"{g_label} {m_label} Analysis"

        return {
            "analysis_type": analysis_type,
            "target_dataset": target_ds,
            "selected_datasets": selected_datasets,
            "group_by": detected_group_by,
            "group_by_dataset": group_by_dataset,
            "metric": detected_metric,
            "metric_dataset": metric_dataset,
            "aggregation": agg_op,
            "sort": sort_order,
            "limit": limit,
            "chart_type": chart_type,
            "title": title
        }


