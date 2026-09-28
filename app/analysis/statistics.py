import numpy as np
import pandas as pd
from typing import Dict, Any, List

class StatisticalEngine:
    @staticmethod
    def calculate_percentage_change(previous: float, current: float) -> Dict[str, Any]:
        """Calculate percentage difference and change proof."""
        if previous == 0:
            pct_change = 0.0
        else:
            pct_change = ((current - previous) / abs(previous)) * 100.0

        direction = "increase" if pct_change > 0 else ("decrease" if pct_change < 0 else "no change")
        return {
            "previous": previous,
            "current": current,
            "absolute_change": current - previous,
            "percentage_change": round(pct_change, 2),
            "direction": direction,
            "proof": f"Change = {current} - {previous} = {current - previous}\n"
                     f"Percentage change = (({current} - {previous}) / |{previous}|) × 100 = {round(pct_change, 2)}%"
        }

    @staticmethod
    def calculate_correlation(df: pd.DataFrame, col_x: str, col_y: str) -> Dict[str, Any]:
        """Compute Pearson correlation and causation disclaimer."""
        clean = df[[col_x, col_y]].dropna()
        if len(clean) < 2:
            return {"coefficient": 0.0, "observations": len(clean), "interpretation": "Insufficient data"}

        corr = clean[col_x].corr(clean[col_y])
        corr_val = round(float(corr), 4)

        if abs(corr_val) > 0.7:
            strength = "Strong"
        elif abs(corr_val) > 0.4:
            strength = "Moderate"
        else:
            strength = "Weak"

        direction = "Positive" if corr_val > 0 else "Negative"

        return {
            "coefficient": corr_val,
            "observations": len(clean),
            "strength": strength,
            "direction": direction,
            "disclaimer": "Note: Correlation measures statistical association and does NOT imply causation."
        }

    @staticmethod
    def detect_outliers(series: pd.Series) -> List[float]:
        """Detect outliers using IQR method."""
        clean = series.dropna()
        if len(clean) < 4:
            return []
        q25, q75 = np.percentile(clean, [25, 75])
        iqr = q75 - q25
        lower = q25 - (1.5 * iqr)
        upper = q75 + (1.5 * iqr)
        outliers = clean[(clean < lower) | (clean > upper)].tolist()
        return [float(x) for x in outliers]
