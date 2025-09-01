import os
import pandas as pd
from .config import META_DIR


def _atomic_replace(path: str, df: pd.DataFrame) -> None:
    tmp = path + ".tmp"
    bak = path + ".bak"
    # Use pyarrow engine by default
    df.to_parquet(tmp, engine="pyarrow", index=False)
    if os.path.exists(path):
        try:
            if os.path.exists(bak):
                os.remove(bak)
        except Exception:
            pass
        try:
            os.replace(path, bak)
        except Exception:
            pass
    os.replace(tmp, path)


def read_parquet_safe(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_parquet(path, engine="pyarrow")
    except Exception:
        # try backup
        bak = path + ".bak"
        if os.path.exists(bak):
            return pd.read_parquet(bak, engine="pyarrow")
        raise


def table_path(name: str) -> str:
    return os.path.join(META_DIR, f"{name}.parquet")

