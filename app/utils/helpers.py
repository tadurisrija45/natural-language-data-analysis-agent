import math
from datetime import datetime
from typing import Any, Union

def format_currency(value: Union[int, float], currency_symbol: str = "$") -> str:
    """
    Format numbers cleanly with standard currency symbol.
    Example: 900000 -> $900,000.00
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"

    
    try:
        num = float(value)
        is_negative = num < 0
        num = abs(num)
        
        # Round if effectively whole
        if num == int(num):
            s = str(int(num))
            decimals = ""
        else:
            parts = f"{num:.2f}".split(".")
            s = parts[0]
            decimals = "." + parts[1]

        # Indian numbering format
        if currency_symbol == "₹" and len(s) > 3:
            last3 = s[-3:]
            remaining = s[:-3]
            groups = []
            while remaining:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            formatted_num = ",".join(groups) + "," + last3 + decimals
        else:
            # Standard international format
            formatted_num = f"{num:,.2f}".rstrip("0").rstrip(".") if num != int(num) else f"{int(num):,}"
            
        sign = "-" if is_negative else ""
        return f"{currency_symbol}{sign}{formatted_num}"
    except Exception:
        return f"{currency_symbol}{value}"


def format_number(value: Any) -> str:
    """Format general numbers nicely."""
    if value is None:
        return "0"
    try:
        num = float(value)
        if math.isnan(num):
            return "N/A"
        if num == int(num):
            return f"{int(num):,}"
        return f"{num:,.2f}"
    except (ValueError, TypeError):
        return str(value)


def format_file_size(bytes_size: int) -> str:
    """Convert bytes to human readable format (KB, MB, GB)."""
    if not bytes_size or bytes_size <= 0:
        return "0 KB"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}" if unit != "B" else f"{bytes_size} B"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def format_datetime(dt: datetime, format_type: str = "full") -> str:
    """Format datetime consistently."""
    if not dt:
        return ""
    if format_type == "time_only":
        return dt.strftime("%I:%M %p").lstrip("0")
    if format_type == "date_only":
        return dt.strftime("%d %b %Y")
    # "27 Sep 2026, 4:25 PM"
    return f"{dt.strftime('%d %b %Y, %I:%M %p').replace(' 0', ' ')}"
