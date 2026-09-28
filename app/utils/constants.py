"""
Application constants and branding configuration.
"""

BRAND_NAME = "DataAgent"
BRAND_TAGLINE = "Natural Language Data Analysis"
HACKATHON_MESSAGE = "No answer without evidence."

# Professional Teal/Slate Color Palette
THEME_COLORS = {
    "primary": "#0F766E",
    "primary_dark": "#115E59",
    "accent": "#14B8A6",
    "background": "#F8FAFC",
    "cards": "#FFFFFF",
    "main_text": "#0F172A",
    "secondary_text": "#64748B",
    "borders": "#E2E8F0",
    "success": "#16A34A",
    "warning": "#D97706",
    "error": "#DC2626",
}

# Supported file extensions
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json", "parquet"}

# Category icons mapping based on domain / keywords
CATEGORY_ICONS = {
    "sales": "📊",
    "customers": "👥",
    "students": "🎓",
    "marketing": "📣",
    "time_series": "📈",
    "finance": "💰",
    "products": "📦",
    "hr": "💼",
    "operations": "⚙️",
    "general": "🔍",
}

# Standard chart types
CHART_TYPES = {
    "bar": "bar",
    "horizontal_bar": "horizontalBar",
    "line": "line",
    "pie": "pie",
    "doughnut": "doughnut",
    "scatter": "scatter",
    "box": "box",
}
