from typing import Dict, Any, List

class AnalysisPlanner:
    @staticmethod
    def create_plan(intent: Dict[str, Any], question: str) -> Dict[str, Any]:
        """
        Formulate an internal multi-step execution plan from structured intent.
        Kept internal to the pipeline while providing a user-friendly high-level summary.
        """
        group_by = intent.get("group_by", "category")
        metric = intent.get("metric", "value")
        agg = intent.get("aggregation", "sum")
        analysis_type = intent.get("analysis_type", "groupby_aggregation")
        target_dataset = intent.get("target_dataset", "dataset")

        steps = [
            f"1. Access and inspect target dataset: '{target_dataset}'",
            f"2. Validate presence of metric column '{metric}' and grouping column '{group_by}'",
            f"3. Filter out null/invalid records in '{metric}'",
            f"4. Apply '{agg}' aggregation on '{metric}' grouped by '{group_by}'",
            f"5. Sort aggregated results in {intent.get('sort', 'descending')} order",
            f"6. Extract top ranking entity and rank distribution",
            f"7. Validate arithmetic integrity and reconciliation against raw dataset",
            f"8. Construct Chart.js visualization ({intent.get('chart_type', 'bar')})",
            f"9. Generate traceable evidence including row counts and sample values",
            f"10. Synthesize executive business insight with proof formula"
        ]

        # Friendly one-line label
        if group_by and metric:
            friendly_label = f"{str(group_by).replace('_', ' ').title()} {str(metric).replace('_', ' ').lower()} {analysis_type.replace('_', ' ')}"
        else:
            friendly_label = f"{analysis_type.replace('_', ' ').title()}"

        return {
            "internal_steps": steps,
            "friendly_label": friendly_label,
            "intent": intent,
        }
