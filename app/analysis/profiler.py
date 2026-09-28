import pandas as pd
import numpy as np
from typing import Dict, Any

class DatasetProfiler:
    @staticmethod
    def profile_dataframe(df: pd.DataFrame, filename: str = "") -> Dict[str, Any]:
        """
        Generate comprehensive internal profile of a dataset.
        Detects rows, columns, data types, missing values, duplicates,
        numerical/categorical/date columns, and summary statistics.
        """
        if df is None or df.empty:
            return {
                "filename": filename,
                "row_count": 0,
                "column_count": 0,
                "columns": [],
                "numerical_columns": [],
                "categorical_columns": [],
                "date_columns": [],
                "missing_values": 0,
                "duplicate_rows": 0,
                "statistics": {},
                "head": []
            }

        row_count = int(len(df))
        column_count = int(len(df.columns))
        missing_count = int(df.isnull().sum().sum())
        if row_count > 50000:
            sample_df = df.sample(50000, random_state=42)
            duplicate_count = int(round(sample_df.duplicated().sum() * (row_count / 50000.0)))
        else:
            duplicate_count = int(df.duplicated().sum())

        numerical_cols = []
        categorical_cols = []
        date_cols = []
        col_details = {}

        for col in df.columns:
            col_str = str(col)
            s = df[col]
            dtype_str = str(s.dtype)
            unique_count = int(s.nunique(dropna=True))
            null_count = int(s.isnull().sum())

            # Detect datetime
            is_date = False
            if pd.api.types.is_datetime64_any_dtype(s):
                is_date = True
            elif s.dtype == object and unique_count > 0:
                # Test sample for datetime format
                sample_non_null = s.dropna().head(10).astype(str)
                date_keywords = ["date", "time", "day", "month", "year", "created", "timestamp"]
                if any(k in col_str.lower() for k in date_keywords):
                    try:
                        pd.to_datetime(sample_non_null, errors="raise")
                        is_date = True
                    except Exception:
                        pass

            if is_date:
                date_cols.append(col_str)
                col_type = "date"
            elif pd.api.types.is_numeric_dtype(s):
                numerical_cols.append(col_str)
                col_type = "numerical"
            else:
                categorical_cols.append(col_str)
                col_type = "categorical"

            # Column stats
            col_stat = {
                "name": col_str,
                "type": col_type,
                "dtype": dtype_str,
                "unique_count": unique_count,
                "null_count": null_count,
                "sample_values": [str(v) for v in s.dropna().head(4).tolist()]
            }

            if col_type == "numerical" and not s.dropna().empty:
                col_stat.update({
                    "min": float(s.min()) if not np.isnan(s.min()) else None,
                    "max": float(s.max()) if not np.isnan(s.max()) else None,
                    "mean": float(s.mean()) if not np.isnan(s.mean()) else None,
                    "median": float(s.median()) if not np.isnan(s.median()) else None,
                    "sum": float(s.sum()) if not np.isnan(s.sum()) else None,
                })

            col_details[col_str] = col_stat

        # Preview head records with safe string conversion for dates/objects
        preview_df = df.head(5).copy()
        for c in preview_df.columns:
            if pd.api.types.is_datetime64_any_dtype(preview_df[c]):
                preview_df[c] = preview_df[c].astype(str)
        head_records = preview_df.fillna("").to_dict(orient="records")

        return {
            "filename": filename,
            "row_count": row_count,
            "column_count": column_count,
            "columns": [str(c) for c in df.columns],
            "numerical_columns": numerical_cols,
            "categorical_columns": categorical_cols,
            "date_columns": date_cols,
            "missing_values": missing_count,
            "duplicate_rows": duplicate_count,
            "column_details": col_details,
            "head": head_records
        }
