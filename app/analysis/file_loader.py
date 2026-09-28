import os
import pandas as pd
from typing import Optional, Dict

class FileLoader:
    @staticmethod
    def load_file(file_path: str) -> Optional[pd.DataFrame]:
        """
        Safely load a dataset file (CSV, Excel, JSON, Parquet) into a Pandas DataFrame.
        """
        if not os.path.exists(file_path):
            return None

        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".csv":
                try:
                    return pd.read_csv(file_path, encoding="utf-8", low_memory=False)
                except UnicodeDecodeError:
                    try:
                        return pd.read_csv(file_path, encoding="latin1", low_memory=False)
                    except Exception:
                        return pd.read_csv(file_path, encoding="cp1252", low_memory=False)
                except Exception:
                    # Try sniffing delimiter for semicolon/tab separated files
                    try:
                        return pd.read_csv(file_path, sep=None, engine="python", encoding="utf-8")
                    except Exception:
                        return pd.read_csv(file_path, encoding="latin1")
            elif ext in [".xlsx", ".xls"]:
                return pd.read_excel(file_path)
            elif ext == ".json":
                return pd.read_json(file_path)
            elif ext == ".parquet":
                return pd.read_parquet(file_path)
            else:
                return None
        except Exception:
            return None

    @classmethod
    def load_multiple(cls, file_map: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        """
        Load multiple datasets.
        file_map: { alias_or_name: file_path }
        """
        result = {}
        for alias, path in file_map.items():
            df = cls.load_file(path)
            if df is not None:
                result[alias] = df
        return result
