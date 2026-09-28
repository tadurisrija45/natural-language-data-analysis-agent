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

    # Prepare execution environment with preloaded DataFrames
    datasets = {}
    for alias, fpath in data_files.items():
        if os.path.exists(fpath):
            ext = os.path.splitext(fpath)[1].lower()
            try:
                if ext == ".csv":
                    try:
                        datasets[alias] = pd.read_csv(fpath, encoding="utf-8", low_memory=False)
                    except UnicodeDecodeError:
                        datasets[alias] = pd.read_csv(fpath, encoding="latin1", low_memory=False)
                    except Exception:
                        datasets[alias] = pd.read_csv(fpath, sep=None, engine="python", encoding="latin1")
                elif ext in [".xlsx", ".xls"]:
                    datasets[alias] = pd.read_excel(fpath)
                elif ext == ".json":
                    datasets[alias] = pd.read_json(fpath)
                elif ext == ".parquet":
                    datasets[alias] = pd.read_parquet(fpath)
            except Exception as e:
                datasets[alias] = None

    # Restricted globals
    safe_globals = {
        "__builtins__": {
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
        },
        "pd": pd,
        "np": np,
        "datasets": datasets,
        "result_data": None,
    }

    # Inject dataframes as direct variables if aliases are valid identifiers
    for alias, df in datasets.items():
        clean_alias = alias.replace("-", "_").replace(".", "_")
        safe_globals[clean_alias] = df

    start_time = time.time()
    try:
        # Execute the code in restricted environment
        exec(code, safe_globals)
        elapsed = time.time() - start_time

        result_raw = safe_globals.get("result_data", None)
        
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
            "error": None
        }
        print(json.dumps(output))

    except Exception as e:
        elapsed = time.time() - start_time
        err_msg = traceback.format_exc()
        output = {
            "success": False,
            "execution_time": round(elapsed, 4),
            "result_data": None,
            "error": str(e),
            "traceback": err_msg
        }
        print(json.dumps(output))


if __name__ == "__main__":
    main()
