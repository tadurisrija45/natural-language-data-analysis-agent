import re
from typing import List, Tuple
from ..utils.constants import CATEGORY_ICONS

class TitleGenerator:
    @staticmethod
    def generate_title_and_category(
        dataset_names: List[str],
        first_question: str = None
    ) -> Tuple[str, str, str]:
        """
        Generate a professional, human-readable title, category, and icon
        based on dataset names and the initial business question.
        Returns: (title, category, icon)
        """
        combined_text = " ".join(dataset_names).lower()
        if first_question:
            combined_text += " " + first_question.lower()

        # Rule matching for domain keywords
        if any(w in combined_text for w in ["student", "marks", "grade", "department", "school", "exam", "education"]):
            return "Student Performance Analysis", "students", CATEGORY_ICONS["students"]

        if any(w in combined_text for w in ["employee", "salary", "hr", "hire", "staff", "attrition", "workforce"]):
            return "Workforce & Compensation Analysis", "hr", CATEGORY_ICONS["hr"]

        if any(w in combined_text for w in ["marketing", "campaign", "ad", "clicks", "impression", "conversion"]):
            if "impact" in combined_text or "roi" in combined_text:
                return "Marketing Impact Analysis", "marketing", CATEGORY_ICONS["marketing"]
            return "Marketing Campaign Performance", "marketing", CATEGORY_ICONS["marketing"]

        if any(w in combined_text for w in ["trend", "monthly", "yearly", "quarterly", "daily", "time", "date"]):
            return "Monthly Sales Trend Analysis", "time_series", CATEGORY_ICONS["time_series"]

        if any(w in combined_text for w in ["region", "state", "city", "country", "territory", "geography"]):
            return "Regional Sales Analysis", "sales", CATEGORY_ICONS["sales"]

        if any(w in combined_text for w in ["customer", "segment", "retention", "churn", "cohort"]):
            return "Customer Revenue Analysis", "customers", CATEGORY_ICONS["customers"]

        if any(w in combined_text for w in ["product", "inventory", "stock", "sku", "item", "category"]):
            return "Product Sales & Profitability Analysis", "products", CATEGORY_ICONS["products"]

        if any(w in combined_text for w in ["finance", "cost", "expense", "budget", "profit", "margin", "tax"]):
            return "Financial Performance Analysis", "finance", CATEGORY_ICONS["finance"]

        if any(w in combined_text for w in ["sales", "order", "revenue", "deal"]):
            return "Sales Performance & Growth Analysis", "sales", CATEGORY_ICONS["sales"]

        # Default fallback based on primary dataset name
        if dataset_names:
            base_name = dataset_names[0].split(".")[0].replace("_", " ").replace("-", " ").title()
            return f"{base_name} Analysis", "general", CATEGORY_ICONS["general"]

        return "Business Intelligence Analysis", "general", CATEGORY_ICONS["general"]
