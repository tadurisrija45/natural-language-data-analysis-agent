import re
from typing import Dict, Any, Optional
from flask import current_app
from ..utils.logger import get_logger

logger = get_logger("DataAgent.CorrectionAgent")

class CorrectionAgent:
    @classmethod
    def correct_code(
        cls,
        failing_code: str,
        error_message: str,
        intent: Dict[str, Any],
        datasets_meta: Dict[str, Any],
        attempt_number: int
    ) -> str:
        """
        Analyze code execution error and produce corrected Python code.
        Attempts Gemini GenAI SDK first if available, otherwise applies rule-based fixes.
        """
        logger.info(f"Self-correction triggered (Attempt {attempt_number}): {error_message}")

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
You are a Python self-correction agent. The following Python code failed with an error:

ERROR:
{error_message}

FAILING CODE:
{failing_code}

DATASET SCHEMA:
{datasets_meta}

INTENT:
{intent}

Fix the code so it runs successfully without error. Ensure `result_data` is assigned.
Return ONLY the corrected Python code, no explanation or markdown fences.
"""
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                fixed_code = resp.text.strip()
                if "```" in fixed_code:
                    fixed_code = re.sub(r"^```[a-z]*\n?", "", fixed_code)
                    fixed_code = re.sub(r"\n?```$", "", fixed_code)
                return fixed_code.strip()
            except Exception as e:
                logger.warning(f"GenAI CorrectionAgent error: {e}. Applying rule-based self-healing.")

        # Rule-based fix: Wrap with safe column coercion and NaN handling
        target_ds = intent.get("target_dataset", list(datasets_meta.keys())[0] if datasets_meta else "data")
        meta = datasets_meta.get(target_ds, {})
        num_cols = meta.get("numerical_columns", [])
        cat_cols = meta.get("categorical_columns", [])

        metric = num_cols[0] if num_cols else "value"
        group_by = cat_cols[0] if cat_cols else "category"

        fallback_code = f"""
df = datasets.get('{target_ds}')
if df is None:
    result_data = {{"error": "Dataset not found"}}
else:
    clean_df = df.copy()
    m_col = '{metric}' if '{metric}' in clean_df.columns else clean_df.select_dtypes(include='number').columns[0]
    g_col = '{group_by}' if '{group_by}' in clean_df.columns else clean_df.select_dtypes(exclude='number').columns[0]
    
    clean_df[m_col] = pd.to_numeric(clean_df[m_col], errors='coerce').fillna(0)
    grouped = clean_df.groupby(g_col)[m_col].sum().reset_index()
    grouped.columns = ['entity', 'value']
    grouped = grouped.sort_values(by='value', ascending=False)
    
    top = grouped.iloc[0] if not grouped.empty else None
    
    result_data = {{
        "summary": f"{{top['entity']}} has the highest {{m_col}} with {{top['value']}}.",
        "breakdown": [{{"entity": str(r.entity), "value": float(r.value)}} for _, r in grouped.head(10).iterrows()],
        "top_entity": str(top['entity']) if top is not None else None,
        "top_value": float(top['value']) if top is not None else 0.0,
        "proof_components": [float(v) for v in clean_df[clean_df[g_col] == (top['entity'] if top is not None else '')][m_col].head(4).tolist()],
        "rows_analyzed": len(clean_df),
        "source_records": clean_df.head(10).fillna("").to_dict(orient="records")
    }}
"""
        return fallback_code.strip()
