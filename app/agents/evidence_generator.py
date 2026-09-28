from typing import Dict, Any, List
from ..utils.helpers import format_currency, format_number

class EvidenceGenerator:
    @staticmethod
    def generate_evidence_and_proof(
        intent: Dict[str, Any],
        execution_result: Dict[str, Any],
        target_dataset_name: str,
        related_dataset_name: str = None
    ) -> Dict[str, Any]:
        """
        Synthesize rigorous traceable evidence and step-by-step mathematical proof.
        """
        analysis_type = intent.get("analysis_type", "groupby_aggregation")
        rows_analyzed = execution_result.get("rows_analyzed", 0)
        breakdown = execution_result.get("breakdown", [])
        top_entity = execution_result.get("top_entity", "N/A")
        top_value = execution_result.get("top_value", 0.0)
        proof_components = execution_result.get("proof_components", [])
        metric = intent.get("metric", "value")

        # Determine formatting function
        is_pct = (analysis_type == "profit_margin" or "margin" in str(metric).lower() or "%" in str(metric))
        is_currency = not is_pct and any(k in str(metric).lower() for k in ["sales", "revenue", "profit", "salary", "spend", "cost", "price"])
        
        def fmt_fn(v):
            if is_pct:
                return f"{float(v):.2f}%"
            elif is_currency:
                return format_currency(v)
            else:
                return format_number(v)

        # Build formatted breakdown rows
        formatted_breakdown = []
        for item in breakdown:
            ent = item.get("entity", "")
            val = item.get("value", 0)
            formatted_breakdown.append({
                "entity": ent,
                "raw_value": val,
                "formatted_value": fmt_fn(val)
            })

        # Dataset attribution
        selected_ds = intent.get("selected_datasets", [])
        if len(selected_ds) > 1:
            source_label = " + ".join(selected_ds)
        else:
            source_label = target_dataset_name


        m_analyzed = "Record Count" if analysis_type == "count" else str(metric).replace("_", " ").title()
        g_analyzed = "Overall" if analysis_type in ["count", "total"] else str(intent.get("group_by", "Category")).replace("_", " ").title()

        evidence_dict = {
            "source_dataset": source_label,
            "related_dataset": related_dataset_name,
            "rows_analyzed": rows_analyzed,
            "metric_analyzed": m_analyzed,
            "group_by": g_analyzed,
            "breakdown": formatted_breakdown,
            "sample_source_records": execution_result.get("source_records", [])
        }

        # Construct Mathematical Proof
        proof_lines = []
        if analysis_type == "dataset_summary":
            proof_lines.append(f"Comprehensive Dataset Profiling for '{target_dataset_name}'")
            proof_lines.append(f"= Total Records: {rows_analyzed:,}")
            if formatted_breakdown:
                for b in formatted_breakdown[:4]:
                    proof_lines.append(f"- {b['entity']}: {b['formatted_value']}")
        elif analysis_type == "dataset_comparison":
            proof_lines.append(f"Comparative evaluation across datasets: {source_label}")
            if formatted_breakdown and len(formatted_breakdown) >= 2:
                for b in formatted_breakdown:
                    proof_lines.append(f"- {b['entity']}: {b['formatted_value']}")
            proof_lines.append(f"= Total combined records: {rows_analyzed:,}")
        elif analysis_type == "count":
            proof_lines.append(f"Row count evaluation across dataset '{target_dataset_name}'")
            proof_lines.append(f"= Total records counted: {int(top_value):,}")
        elif analysis_type in ["total", "scalar_metric"]:
            agg_name = intent.get("aggregation", "sum").capitalize()
            m_name = str(metric).replace("_", " ")
            proof_lines.append(f"{agg_name}({m_name}) across all {rows_analyzed:,} records in '{target_dataset_name}'")
            if proof_components and len(proof_components) > 1 and agg_name == "Total":
                sample_str = " + ".join([fmt_fn(c) for c in proof_components[:4]])
                proof_lines.append(f"= {sample_str} + ...")
            proof_lines.append(f"= {fmt_fn(top_value)}")
        elif analysis_type == "profit_margin":
            proof_lines.append(f"Profit Margin for {top_entity}")
            proof_lines.append(f"= (Price - Cost) / Price")
            proof_lines.append(f"= {top_value:.2f}%")
        elif top_entity and proof_components and len(proof_components) > 1:
            comp_formatted = [fmt_fn(c) for c in proof_components]
            proof_lines.append(f"{top_entity} {str(metric).replace('_', ' ')}")
            proof_lines.append(f"= {' + '.join(comp_formatted[:4])}{' + ...' if len(proof_components) > 4 else ''}")
            proof_lines.append(f"= {fmt_fn(top_value)}")
        elif top_entity:
            proof_lines.append(f"{top_entity} aggregate {str(metric).replace('_', ' ')}")
            proof_lines.append(f"= {fmt_fn(top_value)} (calculated across {rows_analyzed} records)")
        else:
            proof_lines.append(f"Aggregation formula applied across {rows_analyzed} records.")

        proof_text = "\n".join(proof_lines)

        return {
            "evidence": evidence_dict,
            "proof": proof_text
        }

