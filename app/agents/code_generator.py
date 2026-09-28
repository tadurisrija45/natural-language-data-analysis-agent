import re
from typing import Dict, Any, List
from flask import current_app
from ..utils.logger import get_logger
from ..analysis.relationship_detector import RelationshipDetector

logger = get_logger("DataAgent.CodeGenerator")

class CodeGenerator:
    @classmethod
    def generate_code(
        cls,
        intent: Dict[str, Any],
        plan: Dict[str, Any],
        datasets_meta: Dict[str, Any]
    ) -> str:
        """
        Generate executable Python analysis code operating on uploaded datasets.
        Attempts Gemini GenAI SDK first if configured, else generates robust deterministic code.
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

                target_ds = intent.get("target_dataset", list(datasets_meta.keys())[0] if datasets_meta else "data")
                meta = datasets_meta.get(target_ds, {})

                prompt = f"""
You are a Python Data Analysis Code Generator.
Available datasets in sandbox dictionary `datasets`:
{list(datasets_meta.keys())}

Selected datasets for this question:
{intent.get('selected_datasets', [target_ds])}

Analysis Intent:
{intent}

Write clean, efficient Python code using pandas, numpy, and scipy.
Rules:
- Access datasets via: datasets['dataset_name']
- If multiple datasets are needed, merge them using pd.merge on appropriate key columns (e.g. customer_id, product_id).
- Compute the required aggregation, ranking, or metric.
- Store the final output dictionary into `result_data`.
- `result_data` MUST contain:
  - "summary": informative sentence answering the question
  - "breakdown": list of objects [{{"entity": "South", "value": 900000}}, ...]
  - "top_entity": string name of highest/lowest (or null)
  - "top_value": float/int value of highest/lowest (or null)
  - "proof_components": list of numbers contributing to top_value
  - "rows_analyzed": int total rows considered
  - "source_records": list of up to 15 representative rows as dicts for source data view
- Do NOT import os, sys, subprocess, or make network calls.
- Return ONLY valid Python code, no explanation or markdown fences.
"""
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                code_text = resp.text.strip()
                if "```" in code_text:
                    code_text = re.sub(r"^```[a-z]*\n?", "", code_text)
                    code_text = re.sub(r"\n?```$", "", code_text)
                return code_text.strip()
            except Exception as e:
                logger.warning(f"GenAI CodeGenerator error: {e}. Falling back to deterministic code generation.")

        return cls._deterministic_code(intent, datasets_meta)

    @classmethod
    def _deterministic_code(
        cls,
        intent: Dict[str, Any],
        datasets_meta: Dict[str, Any]
    ) -> str:
        """Deterministic Python code generator supporting cross-dataset joins and distinct analysis intents."""
        analysis_type = intent.get("analysis_type", "groupby_aggregation")
        selected_datasets = intent.get("selected_datasets", [])
        if not selected_datasets:
            selected_datasets = [intent.get("target_dataset", list(datasets_meta.keys())[0])]
        
        target_ds = intent.get("target_dataset") or selected_datasets[0]

        # 0. Dataset Comparison Analysis
        if analysis_type == "dataset_comparison":
            ds_keys = list(datasets_meta.keys())
            ds_a = selected_datasets[0] if len(selected_datasets) > 0 else (ds_keys[0] if ds_keys else "data_a")
            ds_b = selected_datasets[1] if len(selected_datasets) > 1 else (ds_keys[1] if len(ds_keys) > 1 else ds_a)
            metric_hint = intent.get("metric") or ""
            return f"""
# DataAgent Comparative Dataset Analysis
df_a = datasets.get('{ds_a}')
df_b = datasets.get('{ds_b}')

if df_a is None or df_b is None:
    result_data = {{"error": "Both datasets must be loaded for comparison."}}
else:
    rows_a = int(len(df_a))
    rows_b = int(len(df_b))
    cols_a = list(df_a.columns)
    cols_b = list(df_b.columns)

    # Detect common columns / join keys
    common_cols = [c for c in cols_a if c in cols_b]

    # Look for common numeric metric or evaluate volume
    metric_candidate = '{metric_hint}' if '{metric_hint}' and '{metric_hint}' != 'rows' else None
    if not metric_candidate:
        for c in cols_a:
            if c in cols_b and pd.api.types.is_numeric_dtype(df_a[c]) and pd.api.types.is_numeric_dtype(df_b[c]):
                metric_candidate = c
                break

    if metric_candidate and metric_candidate in df_a.columns and metric_candidate in df_b.columns:
        val_a = float(pd.to_numeric(df_a[metric_candidate], errors='coerce').sum())
        val_b = float(pd.to_numeric(df_b[metric_candidate], errors='coerce').sum())
        metric_label = metric_candidate.replace('_', ' ').title()
        breakdown = [
            {{"entity": '{ds_a}', "value": round(val_a, 2)}},
            {{"entity": '{ds_b}', "value": round(val_b, 2)}}
        ]
        diff = abs(val_a - val_b)
        higher_ds = '{ds_a}' if val_a >= val_b else '{ds_b}'
        summary = f"Comparing {{metric_label}}: {{higher_ds}} has the higher total ({{max(val_a, val_b):,.2f}}) compared to {{min(val_a, val_b):,.2f}}, with a difference of {{diff:,.2f}}."
        top_ent = higher_ds
        top_v = max(val_a, val_b)
        proof_vals = [val_a, val_b]
    else:
        # Compare volume and structural synergy
        breakdown = [
            {{"entity": '{ds_a}', "value": rows_a}},
            {{"entity": '{ds_b}', "value": rows_b}}
        ]
        key_str = f" connected via '{{common_cols[0]}}'" if common_cols else ""
        summary = f"Dataset comparison: '{ds_a}' contains {{rows_a:,}} records ({{len(cols_a)}} columns) and '{ds_b}' contains {{rows_b:,}} records ({{len(cols_b)}} columns){{key_str}}."

        top_ent = '{ds_a}' if rows_a >= rows_b else '{ds_b}'
        top_v = max(rows_a, rows_b)
        proof_vals = [rows_a, rows_b]


    # Combine sample records from both for the source view modal
    sample_a = df_a.head(8).copy()
    sample_a['_dataset'] = '{ds_a}'
    sample_b = df_b.head(8).copy()
    sample_b['_dataset'] = '{ds_b}'
    source_records = pd.concat([sample_a, sample_b], ignore_index=True).fillna("").to_dict(orient="records")

    result_data = {{
        "summary": summary,
        "breakdown": breakdown,
        "top_entity": top_ent,
        "top_value": round(top_v, 2),
        "proof_components": proof_vals,
        "rows_analyzed": rows_a + rows_b,
        "group_by": "dataset",
        "metric": metric_candidate or "records",
        "source_records": source_records
    }}
""".strip()

        # 0.5 Dataset Summary Overview Analysis
        if analysis_type == "dataset_summary":
            return f"""
# DataAgent Dataset Summary Overview
df = datasets.get('{target_ds}')
if df is None or df.empty:
    result_data = {{"error": "Dataset '{target_ds}' is empty or not found."}}
else:
    rows = int(len(df))
    cols = list(df.columns)
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c])]

    breakdown = []
    for c in num_cols[:5]:
        s = pd.to_numeric(df[c], errors='coerce').dropna()
        if not s.empty:
            breakdown.append({{"entity": "Avg " + str(c).replace("_", " ").title(), "value": round(float(s.mean()), 2)}})

    if not breakdown and cat_cols:
        for c in cat_cols[:4]:
            breakdown.append({{"entity": "Unique " + str(c).replace("_", " ").title(), "value": int(df[c].nunique())}})

    summary_parts = [f"Dataset '{target_ds}' contains {{rows:,}} records across {{len(cols)}} columns."]
    if num_cols:
        summary_parts.append("Numeric fields: " + ", ".join(num_cols[:4]) + ".")
    if cat_cols:
        summary_parts.append("Categorical fields: " + ", ".join(cat_cols[:4]) + ".")
    summary = " ".join(summary_parts)

    clean_export = df.head(15).copy()
    for col in clean_export.columns:
        if pd.api.types.is_datetime64_any_dtype(clean_export[col]):
            clean_export[col] = clean_export[col].astype(str)
    source_records = clean_export.fillna("").to_dict(orient="records")

    result_data = {{
        "summary": summary,
        "breakdown": breakdown,
        "top_entity": f"{{rows:,}} Records",
        "top_value": rows,
        "proof_components": [rows, len(cols)],
        "rows_analyzed": rows,
        "group_by": "dataset",
        "metric": "summary",
        "source_records": source_records
    }}
""".strip()

        # 1. Count Analysis
        if analysis_type == "count":
            entity_label = target_ds.split(".")[0].replace("_", " ").title()

            return f"""
# DataAgent Count Analysis
df = datasets.get('{target_ds}')
if df is None or df.empty:
    result_data = {{"error": "Dataset '{target_ds}' is empty or not found."}}
else:
    count_val = int(len(df))
    entity_label = "{entity_label}"
    clean_export = df.head(15).copy()
    for col in clean_export.columns:
        if pd.api.types.is_datetime64_any_dtype(clean_export[col]):
            clean_export[col] = clean_export[col].astype(str)
    source_records = clean_export.fillna("").to_dict(orient="records")
    result_data = {{
        "summary": f"There are {{count_val:,}} {{entity_label.lower()}} in the dataset.",
        "breakdown": [{{"entity": f"Total {{entity_label}}", "value": count_val}}],
        "top_entity": f"Total {{entity_label}}",
        "top_value": count_val,
        "proof_components": [count_val],
        "rows_analyzed": count_val,
        "source_records": source_records
    }}
""".strip()

        # 2. Scalar Metric Analysis (Mean, Median, Min, Max, Total/Sum, Nunique)
        if analysis_type in ["scalar_metric", "total"]:
            metric = intent.get("metric") or "value"
            agg = intent.get("aggregation", "sum")
            return f"""
# DataAgent Scalar Metric Analysis
df = datasets.get('{target_ds}')
if df is None or df.empty:
    result_data = {{"error": "Dataset '{target_ds}' is empty or not found."}}
else:
    clean_df = df.copy()
    metric_col = '{metric}' if '{metric}' in clean_df.columns else None
    if not metric_col:
        for c in clean_df.columns:
            if pd.api.types.is_numeric_dtype(clean_df[c]):
                metric_col = c
                break
    if not metric_col:
        metric_col = clean_df.columns[0]

    s = pd.to_numeric(clean_df[metric_col], errors='coerce').dropna()
    agg_type = '{agg}'.lower()

    if agg_type in ['mean', 'average', 'avg']:
        val = float(s.mean()) if not s.empty else 0.0
        agg_label = "average"
    elif agg_type == 'median':
        val = float(s.median()) if not s.empty else 0.0
        agg_label = "median"
    elif agg_type == 'min':
        val = float(s.min()) if not s.empty else 0.0
        agg_label = "minimum"
    elif agg_type == 'max':
        val = float(s.max()) if not s.empty else 0.0
        agg_label = "maximum"
    elif agg_type == 'nunique':
        val = float(clean_df[metric_col].nunique())
        agg_label = "distinct count of"
    else:
        val = float(s.sum()) if not s.empty else 0.0
        agg_label = "total"

    rows_analyzed = len(clean_df)
    m_name = str(metric_col).replace('_', ' ')
    sample_vals = [float(v) for v in s.head(5).tolist()]

    clean_export = clean_df.head(15).copy()
    for col in clean_export.columns:
        if pd.api.types.is_datetime64_any_dtype(clean_export[col]):
            clean_export[col] = clean_export[col].astype(str)
    source_records = clean_export.fillna("").to_dict(orient="records")

    is_curr = any(k in m_name.lower() for k in ["revenue", "sales", "profit", "salary", "spend", "cost", "price", "amount"])
    fmt_val = f"${{val:,.2f}}" if is_curr else (f"{{val:,.2f}}" if (val % 1 != 0) else f"{{int(val):,}}")

    summary = f"The {{agg_label}} {{m_name}} is {{fmt_val}} across all {{rows_analyzed:,}} records."

    breakdown = [
        {{"entity": f"{{agg_label.capitalize()}} {{m_name.title()}}", "value": round(val, 2)}}
    ]
    if not s.empty and agg_type in ['mean', 'sum']:
        breakdown.append({{"entity": "Min", "value": round(float(s.min()), 2)}})
        breakdown.append({{"entity": "Max", "value": round(float(s.max()), 2)}})
        breakdown.append({{"entity": "Median", "value": round(float(s.median()), 2)}})

    result_data = {{
        "summary": summary,
        "breakdown": breakdown,
        "top_entity": f"{{agg_label.capitalize()}} {{m_name.title()}}",
        "top_value": round(val, 2),
        "proof_components": sample_vals if sample_vals else [val],
        "rows_analyzed": rows_analyzed,
        "metric": metric_col,
        "source_records": source_records
    }}
""".strip()

        # 3. Profit Margin Analysis
        if analysis_type == "profit_margin":
            group_by = intent.get("group_by") or "product_name"
            return f"""
# DataAgent Profit Margin Analysis
df = datasets.get('{target_ds}')
if df is None or df.empty:
    result_data = {{"error": "Dataset '{target_ds}' is empty or not found."}}
else:
    clean_df = df.copy()
    group_col = '{group_by}' if '{group_by}' in clean_df.columns else None
    if not group_col:
        for c in ['product_name', 'product_id', 'product', 'item', 'name']:
            if c in clean_df.columns:
                group_col = c
                break
    if not group_col:
        group_col = clean_df.columns[0]

    # Calculate profit margin if not already present
    if 'profit_margin' in clean_df.columns:
        clean_df['calc_margin'] = pd.to_numeric(clean_df['profit_margin'], errors='coerce')
    elif 'price' in clean_df.columns and 'cost' in clean_df.columns:
        p = pd.to_numeric(clean_df['price'], errors='coerce')
        c = pd.to_numeric(clean_df['cost'], errors='coerce')
        clean_df['calc_margin'] = (p - c) / p.replace(0, float('nan'))
    elif 'unit_price' in clean_df.columns and 'unit_cost' in clean_df.columns:
        p = pd.to_numeric(clean_df['unit_price'], errors='coerce')
        c = pd.to_numeric(clean_df['unit_cost'], errors='coerce')
        clean_df['calc_margin'] = (p - c) / p.replace(0, float('nan'))
    else:
        clean_df['calc_margin'] = 0.0

    clean_df['calc_margin'] = clean_df['calc_margin'].fillna(0)
    max_val = float(clean_df['calc_margin'].max())
    is_decimal = (0 < max_val <= 1.0)
    clean_df['margin_pct'] = clean_df['calc_margin'] * 100.0 if is_decimal else clean_df['calc_margin']

    sorted_df = clean_df.sort_values(by='margin_pct', ascending=False)
    top_row = sorted_df.iloc[0] if not sorted_df.empty else None
    top_entity = str(top_row[group_col]) if top_row is not None else None
    top_val = float(top_row['margin_pct']) if top_row is not None else 0.0

    breakdown_records = []
    for _, r in sorted_df.head(15).iterrows():
        breakdown_records.append({{
            "entity": str(r[group_col]),
            "value": round(float(r['margin_pct']), 2)
        }})

    source_records = clean_df.head(15).fillna("").to_dict(orient="records")
    result_data = {{
        "summary": f"{{top_entity}} has the highest profit margin with {{round(top_val, 2)}}%.",
        "breakdown": breakdown_records,
        "top_entity": top_entity,
        "top_value": round(top_val, 2),
        "proof_components": [round(top_val, 2)],
        "rows_analyzed": len(clean_df),
        "group_by": group_col,
        "metric": "profit_margin",
        "source_records": source_records
    }}
""".strip()

        # 4. Time Series Analysis
        if analysis_type == "time_series":
            metric = intent.get("metric") or "revenue"
            date_col = intent.get("group_by") or "order_date"
            return f"""
# DataAgent Time Series Analysis
df = datasets.get('{target_ds}')
if df is None or df.empty:
    result_data = {{"error": "Dataset '{target_ds}' is empty or not found."}}
else:
    clean_df = df.copy()
    date_c = '{date_col}' if '{date_col}' in clean_df.columns else None
    metric_c = '{metric}' if '{metric}' in clean_df.columns else None

    if not date_c:
        for c in clean_df.columns:
            if 'date' in c.lower() or 'time' in c.lower():
                date_c = c
                break
    if not metric_c:
        for c in clean_df.columns:
            if pd.api.types.is_numeric_dtype(clean_df[c]):
                metric_c = c
                break

    clean_df[metric_c] = pd.to_numeric(clean_df[metric_c], errors='coerce').fillna(0)
    clean_df['dt'] = pd.to_datetime(clean_df[date_c], errors='coerce')
    clean_df = clean_df.dropna(subset=['dt'])
    
    clean_df['period'] = clean_df['dt'].dt.to_period('M').astype(str)
    grouped = clean_df.groupby('period')[metric_c].sum().reset_index()
    grouped.columns = ['entity', 'value']
    grouped = grouped.sort_values(by='entity', ascending=True)

    breakdown_records = []
    for _, r in grouped.iterrows():
        breakdown_records.append({{
            "entity": str(r['entity']),
            "value": round(float(r['value']), 2)
        }})

    top_entity = breakdown_records[-1]['entity'] if breakdown_records else None
    top_val = breakdown_records[-1]['value'] if breakdown_records else 0.0
    first_val = breakdown_records[0]['value'] if breakdown_records else 0.0
    trend_str = "increased" if top_val >= first_val else "decreased"

    clean_df_export = clean_df.copy()
    if 'dt' in clean_df_export.columns:
        clean_df_export['dt'] = clean_df_export['dt'].astype(str)
    source_records = clean_df_export.head(15).fillna("").to_dict(orient="records")
    m_label = str(metric_c).replace('_', ' ').title()

    first_period = breakdown_records[0]['entity'] if breakdown_records else ''
    last_period = top_entity or ''
    result_data = {{
        "summary": f"{{m_label}} {{trend_str}} from {{first_val:,.2f}} ({{first_period}}) to {{top_val:,.2f}} ({{last_period}}).",
        "breakdown": breakdown_records,
        "top_entity": top_entity,
        "top_value": round(top_val, 2),
        "proof_components": [r['value'] for r in breakdown_records[:5]],
        "rows_analyzed": len(clean_df),
        "group_by": "period",
        "metric": metric_c,
        "source_records": source_records
    }}
""".strip()

        # 5. Ranking and Group-By Aggregations (Single or Multi-Dataset Merge)
        load_lines = []
        if len(selected_datasets) > 1:
            base_ds = selected_datasets[0]
            load_lines.append(f"clean_df = datasets.get('{base_ds}').copy()")
            for other_ds in selected_datasets[1:]:
                join_info = RelationshipDetector.find_join_between(
                    datasets_meta.get(base_ds, {}),
                    datasets_meta.get(other_ds, {}),
                    base_ds,
                    other_ds
                )
                if join_info:
                    l_on = join_info["left_on"]
                    r_on = join_info["right_on"]
                    load_lines.append(f"_df_other = datasets.get('{other_ds}')")
                    load_lines.append(f"clean_df = pd.merge(clean_df, _df_other, left_on='{l_on}', right_on='{r_on}', how='inner')")
                else:
                    load_lines.append(f"# Fallback without join for {other_ds}")
        else:
            load_lines.append(f"clean_df = datasets.get('{target_ds}').copy()")

        load_code = "\n    ".join(load_lines)
        group_by = intent.get("group_by")
        metric = intent.get("metric")
        agg = intent.get("aggregation", "sum")
        sort_order = intent.get("sort", "descending")
        ascending = (sort_order == "ascending")

        return f"""
# DataAgent Group-By & Ranking Analysis
if not datasets:
    result_data = {{"error": "No datasets available."}}
else:
    {load_code}
    if clean_df is None or clean_df.empty:
        result_data = {{"error": "Dataset is empty or datasets could not be joined."}}
    else:
        rows_analyzed = len(clean_df)
        group_col = '{group_by}' if '{group_by}' in clean_df.columns else None
        metric_col = '{metric}' if '{metric}' in clean_df.columns else None

        # Dynamic fallback column resolution
        if not group_col:
            for c in clean_df.columns:
                if '{group_by}'.lower() in c.lower() or c.lower() in '{group_by}'.lower():
                    group_col = c
                    break
        if not metric_col:
            for c in clean_df.columns:
                if '{metric}'.lower() in c.lower():
                    metric_col = c
                    break

        if not metric_col:
            for c in clean_df.columns:
                if pd.api.types.is_numeric_dtype(clean_df[c]):
                    metric_col = c
                    break

        if not group_col:
            for c in clean_df.columns:
                if c != metric_col and not str(c).endswith('_id'):
                    group_col = c
                    break

        agg_name = '{agg}'.lower()
        if agg_name == 'count':
            grouped = clean_df.groupby(group_col).size().reset_index(name='value')
            grouped.columns = ['entity', 'value']
        else:
            clean_df[metric_col] = pd.to_numeric(clean_df[metric_col], errors='coerce').fillna(0)
            grouped = clean_df.groupby(group_col)[metric_col].agg('{agg}').reset_index()
            grouped.columns = ['entity', 'value']

        grouped = grouped.sort_values(by='value', ascending={ascending})

        top_row = grouped.iloc[0] if not grouped.empty else None
        top_entity = str(top_row['entity']) if top_row is not None else None
        top_val = float(top_row['value']) if top_row is not None else 0.0

        breakdown_records = []
        for _, r in grouped.head(15).iterrows():
            breakdown_records.append({{
                "entity": str(r['entity']),
                "value": round(float(r['value']), 2)
            }})

        proof_components = []
        if top_entity is not None:
            if agg_name == 'count':
                proof_components = [int(top_val)]
            else:
                top_records = clean_df[clean_df[group_col].astype(str) == top_entity][metric_col]
                proof_components = [float(v) for v in top_records.head(5).tolist()]

        clean_export = clean_df.head(15).copy()
        for c in clean_export.columns:
            if pd.api.types.is_datetime64_any_dtype(clean_export[c]):
                clean_export[c] = clean_export[c].astype(str)
        source_records = clean_export.fillna("").to_dict(orient="records")

        superlative = "lowest" if {ascending} else "highest"
        m_label = str(metric_col).replace('_', ' ')
        is_curr = any(k in m_label.lower() for k in ["revenue", "sales", "profit", "salary", "spend", "cost", "price", "amount"])
        fmt_top = f"${{top_val:,.2f}}" if is_curr else (f"{{top_val:,.2f}}" if (top_val % 1 != 0) else f"{{int(top_val):,}}")

        if agg_name in ['mean', 'average', 'avg']:
            summary = f"{{top_entity}} had the {{superlative}} average {{m_label}} of {{fmt_top}}."
        elif agg_name == 'count':
            summary = f"{{top_entity}} had the {{superlative}} count with {{int(top_val):,}} records."
        elif agg_name == 'min':
            summary = f"{{top_entity}} had the lowest {{m_label}} of {{fmt_top}}."
        elif agg_name == 'max':
            summary = f"{{top_entity}} had the highest {{m_label}} of {{fmt_top}}."
        else:
            summary = f"{{top_entity}} generated the {{superlative}} {{m_label}} with {{fmt_top}}."

        result_data = {{
            "summary": summary,
            "breakdown": breakdown_records,
            "top_entity": top_entity,
            "top_value": round(top_val, 2),
            "proof_components": proof_components,
            "rows_analyzed": rows_analyzed,
            "group_by": group_col,
            "metric": metric_col if agg_name != 'count' else 'count',
            "source_records": source_records
        }}
""".strip()

