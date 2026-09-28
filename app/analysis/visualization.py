import os
import uuid
from typing import Dict, Any, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flask import current_app

from ..utils.constants import THEME_COLORS

class VisualizationEngine:
    @staticmethod
    def build_chart_config(
        chart_type: str,
        labels: List[str],
        data: List[float],
        title: str = "",
        dataset_label: str = "Value"
    ) -> Dict[str, Any]:
        """
        Build a Chart.js compliant JSON configuration using the DataAgent teal palette.
        Supported types: 'bar', 'horizontalBar', 'line', 'pie', 'doughnut', 'scatter'
        """
        teal_primary = THEME_COLORS["primary"]      # #0F766E
        teal_accent = THEME_COLORS["accent"]        # #14B8A6
        teal_dark = THEME_COLORS["primary_dark"]    # #115E59

        # Palette for multiple slices/bars
        palette = [
            "#0F766E", "#14B8A6", "#0D9488", "#2DD4BF", "#042F2E",
            "#115E59", "#5EEAD4", "#134E4A", "#99F6E4", "#0F172A"
        ]

        if chart_type in ["pie", "doughnut"]:
            bg_colors = palette[:len(labels)]
            border_colors = ["#FFFFFF"] * len(labels)
        else:
            bg_colors = [teal_primary] * len(labels)
            border_colors = [teal_dark] * len(labels)

        # Standardize horizontal bar type for Chart.js v3+ (type='bar', indexAxis='y')
        actual_type = "bar" if chart_type in ["bar", "horizontalBar"] else chart_type
        index_axis = "y" if chart_type == "horizontalBar" else "x"

        return {
            "type": actual_type,
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": dataset_label,
                    "data": data,
                    "backgroundColor": bg_colors,
                    "borderColor": border_colors,
                    "borderWidth": 1.5,
                    "borderRadius": 6 if actual_type == "bar" else 0,
                    "fill": False if chart_type == "line" else True,
                    "tension": 0.3 if actual_type == "line" else 0
                }]
            },
            "options": {
                "indexAxis": index_axis,
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {"display": chart_type in ["pie", "doughnut"]},
                    "title": {"display": bool(title), "text": title}
                }
            }
        }

    @staticmethod
    def render_static_chart_image(
        chart_type: str,
        labels: List[str],
        data: List[float],
        title: str = "",
        dataset_label: str = "Value"
    ) -> str:
        """
        Render a static chart image to disk for inclusion in PDF reports.
        Returns the absolute filepath of the generated image.
        """
        plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
        fig, ax = plt.subplots(figsize=(7, 3.5), dpi=150)

        teal = "#0F766E"
        accent = "#14B8A6"

        try:
            if chart_type == "horizontalBar":
                y_pos = range(len(labels))
                ax.barh(y_pos, data, color=teal, edgecolor="#115E59", height=0.6)
                ax.set_yticks(y_pos)
                ax.set_yticklabels(labels, fontsize=9)
                ax.invert_yaxis()
            elif chart_type == "line":
                ax.plot(labels, data, marker="o", color=teal, linewidth=2.5, markersize=6)
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
            elif chart_type in ["pie", "doughnut"]:
                palette = ["#0F766E", "#14B8A6", "#0D9488", "#2DD4BF", "#042F2E", "#115E59"]
                ax.pie(data, labels=labels, autopct="%1.1f%%", colors=palette[:len(labels)], startangle=140)
            else:  # Default vertical bar
                x_pos = range(len(labels))
                ax.bar(x_pos, data, color=teal, edgecolor="#115E59", width=0.55)
                ax.set_xticks(x_pos)
                ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)

            if title:
                ax.set_title(title, fontsize=11, fontweight="bold", pad=12, color="#0F172A")

            fig.tight_layout()

            charts_dir = current_app.config["CHARTS_DIR"]
            os.makedirs(charts_dir, exist_ok=True)
            filename = f"chart_{uuid.uuid4().hex[:10]}.png"
            filepath = os.path.join(charts_dir, filename)
            plt.savefig(filepath, format="png", bbox_inches="tight")
            return filepath
        finally:
            plt.close(fig)
