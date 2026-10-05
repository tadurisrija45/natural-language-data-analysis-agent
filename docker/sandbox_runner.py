"""
Sandbox runner script for secure execution of generated data analysis code.
Executed inside Docker container or isolated subprocess.
"""

import sys
import os
import json
import time
import traceback
import pandas as pd
import numpy as np


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No payload file provided."}))
        sys.exit(1)

    payload_path = sys.argv[1]
    if not os.path.exists(payload_path):
        print(json.dumps({"success": False, "error": f"Payload not found: {payload_path}"}))
        sys.exit(1)

    with open(payload_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    code = payload.get("code", "")
    data_files = payload.get("data_files", {})  # alias -> file_path

    import shutil
    import math
    import datetime
    import re

    # Copy data files into the working directory so relative filepaths like
    # pandas.read_csv("filename.csv") work seamlessly
    for alias, fpath in data_files.items():
        if os.path.exists(fpath):
            try:
                base_alias = os.path.basename(alias)
                dest = os.path.join(os.getcwd(), base_alias)
                if not os.path.exists(dest) and os.path.abspath(dest) != os.path.abspath(fpath):
                    shutil.copy2(fpath, dest)
            except Exception:
                pass

    # Prepare execution environment with preloaded DataFrames
    datasets = {}
    for alias, fpath in data_files.items():
        if os.path.exists(fpath):
            ext = os.path.splitext(fpath)[1].lower()
            df = None
            try:
                if ext == ".csv":
                    try:
                        df = pd.read_csv(fpath, encoding="utf-8", low_memory=False)
                    except UnicodeDecodeError:
                        df = pd.read_csv(fpath, encoding="latin1", low_memory=False)
                    except Exception:
                        df = pd.read_csv(fpath, sep=None, engine="python", encoding="latin1")
                elif ext in [".xlsx", ".xls"]:
                    df = pd.read_excel(fpath)
                elif ext == ".json":
                    df = pd.read_json(fpath)
                elif ext == ".parquet":
                    df = pd.read_parquet(fpath)
            except Exception as e:
                df = None
            datasets[alias] = df
            stem = os.path.splitext(alias)[0].replace("-", "_").replace(" ", "_")
            datasets[stem] = df

    # Smart CSV / Excel reader that intercepts aliases or filenames
    orig_read_csv = pd.read_csv
    def smart_read_csv(filepath_or_buffer, *args, **kwargs):
        if isinstance(filepath_or_buffer, str):
            if not os.path.exists(filepath_or_buffer):
                for alias, fpath in data_files.items():
                    if filepath_or_buffer in [alias, os.path.basename(alias), alias.split(".")[0]]:
                        return orig_read_csv(fpath, *args, **kwargs)
        return orig_read_csv(filepath_or_buffer, *args, **kwargs)

    pd.read_csv = smart_read_csv

    # Safe dynamic import function for whitelisted analytical modules
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".")[0]
        allowed_modules = {
            "pandas", "pd", "numpy", "np", "scipy", "math", "datetime",
            "json", "re", "collections", "itertools", "statistics"
        }
        if root not in allowed_modules:
            raise ImportError(f"Importing module '{name}' is restricted for security.")
        return __import__(name, globals, locals, fromlist, level)

    safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "range": range,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
        "print": print,
        "isinstance": isinstance,
        "type": type,
        "filter": filter,
        "map": map,
        "reversed": reversed,
        "repr": repr,
        "hasattr": hasattr,
        "getattr": getattr,
        "__import__": safe_import,
    }

    # Restricted globals
    safe_globals = {
        "__builtins__": safe_builtins,
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
        "math": math,
        "datetime": datetime,
        "re": re,
        "json": json,
        "datasets": datasets,
        "result_data": None,
    }

    # Inject dataframes as direct variables if aliases are valid identifiers
    for alias, df in datasets.items():
        clean_alias = alias.replace("-", "_").replace(".", "_")
        safe_globals[clean_alias] = df
        stem = os.path.splitext(alias)[0].replace("-", "_").replace(" ", "_")
        safe_globals[stem] = df

    import io
    initial_keys = set(safe_globals.keys())

    # Redirect stdout during exec to capture print statements cleanly
    stdout_capture = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    start_time = time.time()
    captured_logs = ""
    try:
        # Execute the code in restricted environment
        exec(code, safe_globals)
        elapsed = time.time() - start_time
        captured_logs = stdout_capture.getvalue()
    except Exception as e:
        elapsed = time.time() - start_time
        captured_logs = stdout_capture.getvalue()
        sys.stdout = old_stdout
        err_msg = traceback.format_exc()
        output = {
            "success": False,
            "execution_time": round(elapsed, 4),
            "result_data": None,
            "stdout": captured_logs.strip(),
            "error": str(e),
            "traceback": err_msg
        }
        print("__SANDBOX_RESULT_START__")
        print(json.dumps(output))
        print("__SANDBOX_RESULT_END__")
        return
    finally:
        sys.stdout = old_stdout

    result_raw = safe_globals.get("result_data", None)
    if result_raw is None:
        for candidate in ["result", "res", "df_result", "output", "summary", "ans", "out"]:
            if candidate in safe_globals and safe_globals[candidate] is not None:
                result_raw = safe_globals[candidate]
                break
    if result_raw is None:
        new_keys = [k for k in safe_globals.keys() if k not in initial_keys and not k.startswith("_")]
        for k in reversed(new_keys):
            v = safe_globals[k]
            if isinstance(v, (pd.DataFrame, pd.Series, dict, list, int, float, str)):
                result_raw = v
                break
    if result_raw is None and captured_logs.strip():
        result_raw = captured_logs.strip()
        
    # Serialize result_data
    def serialize_item(item):
        if item is None:
            return None
        if isinstance(item, (pd.DataFrame,)):
            return json.loads(item.head(200).to_json(orient="records", date_format="iso"))
        if isinstance(item, (pd.Series,)):
            return json.loads(item.head(200).to_json(orient="index", date_format="iso"))
        if isinstance(item, (np.integer,)):
            return int(item)
        if isinstance(item, (np.floating,)):
            return float(item)
        if isinstance(item, (np.ndarray,)):
            return item.tolist()
        if isinstance(item, dict):
            return {str(k): serialize_item(v) for k, v in item.items()}
        if isinstance(item, (list, tuple)):
            return [serialize_item(v) for v in item]
        return item

    serialized_result = serialize_item(result_raw)

    output = {
        "success": True,
        "execution_time": round(elapsed, 4),
        "result_data": serialized_result,
        "stdout": captured_logs.strip(),
        "error": None
    }
    print("__SANDBOX_RESULT_START__")
    print(json.dumps(output))
    print("__SANDBOX_RESULT_END__")


if __name__ == "__main__":
    main()
