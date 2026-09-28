import pandas as pd
from typing import Dict, List, Any

class RelationshipDetector:
    @staticmethod
    def detect_relationships(dataframes: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Inspect pairs of datasets to detect possible join keys:
        - Primary key candidates (unique column in a table)
        - Matching column names or suffix matches (e.g. customer_id <-> id or customer_id <-> customer_id)
        - Value overlap percentage
        - Compatible data types
        """
        relationships = []
        df_keys = list(dataframes.keys())

        for i in range(len(df_keys)):
            for j in range(i + 1, len(df_keys)):
                name_a, df_a = df_keys[i], dataframes[df_keys[i]]
                name_b, df_b = df_keys[j], dataframes[df_keys[j]]

                if df_a is None or df_b is None or df_a.empty or df_b.empty:
                    continue

                for col_a in df_a.columns:
                    for col_b in df_b.columns:
                        clean_a = str(col_a).strip().lower()
                        clean_b = str(col_b).strip().lower()

                        # Check column name equality or suffix match
                        name_match = (
                            clean_a == clean_b or
                            (clean_a.endswith("_id") and clean_a == f"{clean_b}_id") or
                            (clean_b.endswith("_id") and clean_b == f"{clean_a}_id")
                        )

                        if not name_match:
                            continue

                        # Check uniqueness for candidate primary key
                        is_pk_a = df_a[col_a].is_unique
                        is_pk_b = df_b[col_b].is_unique

                        # Check value overlap
                        set_a = set(df_a[col_a].dropna().astype(str).unique())
                        set_b = set(df_b[col_b].dropna().astype(str).unique())

                        if not set_a or not set_b:
                            continue

                        intersection = set_a.intersection(set_b)
                        overlap_ratio = len(intersection) / max(min(len(set_a), len(set_b)), 1)

                        if overlap_ratio >= 0.2:  # at least 20% value overlap
                            confidence = "high" if overlap_ratio > 0.8 and (is_pk_a or is_pk_b) else "medium"
                            relationships.append({
                                "dataset_a": name_a,
                                "column_a": str(col_a),
                                "is_pk_a": is_pk_a,
                                "dataset_b": name_b,
                                "column_b": str(col_b),
                                "is_pk_b": is_pk_b,
                                "overlap_ratio": round(overlap_ratio, 2),
                                "confidence": confidence,
                                "common_values_sample": list(intersection)[:3],
                            })

        return relationships

    @staticmethod
    def find_join_between(
        meta_a: Dict[str, Any],
        meta_b: Dict[str, Any],
        name_a: str = "",
        name_b: str = ""
    ) -> Dict[str, str]:
        """
        Find best join columns between two datasets using their metadata schemas.
        Returns dict {"left_on": col_a, "right_on": col_b} or empty dict if none found.
        """
        cols_a = meta_a.get("columns", [])
        cols_b = meta_b.get("columns", [])

        # 1. Exact match (case-insensitive)
        for ca in cols_a:
            for cb in cols_b:
                if str(ca).strip().lower() == str(cb).strip().lower():
                    # Prioritize key-like columns (id, code, key, etc.)
                    return {"left_on": str(ca), "right_on": str(cb)}

        # 2. Suffix / ID matching
        for ca in cols_a:
            for cb in cols_b:
                cal = str(ca).strip().lower()
                cbl = str(cb).strip().lower()
                if (cal.endswith("_id") and cal == f"{cbl}_id") or (cbl.endswith("_id") and cbl == f"{cal}_id"):
                    return {"left_on": str(ca), "right_on": str(cb)}
                if (cal == "id" and f"{name_b.split('.')[0].lower()}_id" == cbl) or (cbl == "id" and f"{name_a.split('.')[0].lower()}_id" == cal):
                    return {"left_on": str(ca), "right_on": str(cb)}

        return {}

    @classmethod
    def find_join_path(
        cls,
        datasets_meta: Dict[str, Any],
        needed_datasets: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Given a list of dataset names, determine how to join them sequentially.
        """
        if len(needed_datasets) <= 1:
            return []

        join_steps = []
        base_ds = needed_datasets[0]
        remaining = list(needed_datasets[1:])

        current_meta = datasets_meta.get(base_ds, {})
        for next_ds in remaining:
            next_meta = datasets_meta.get(next_ds, {})
            join_info = cls.find_join_between(current_meta, next_meta, base_ds, next_ds)
            if join_info:
                join_steps.append({
                    "left_dataset": base_ds,
                    "right_dataset": next_ds,
                    "left_on": join_info["left_on"],
                    "right_on": join_info["right_on"],
                    "how": "inner"
                })
        return join_steps

