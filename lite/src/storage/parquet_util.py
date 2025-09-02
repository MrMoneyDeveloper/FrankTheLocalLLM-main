import os
import errno
import pandas as pd
from .config import META_DIR


def _fsync_file(p: str) -> None:
    try:
        fd = os.open(p, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass


def _fsync_dir(p: str) -> None:
    try:
        dfd = os.open(os.path.dirname(p) or ".", os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except Exception:
        pass


def atomic_replace(path: str, df: pd.DataFrame) -> None:
    """Atomically replace a parquet file with backup rotation (.bak).

    Pattern: write .tmp -> fsync -> rotate .bak -> rename -> fsync dir.
    """
    tmp = path + ".tmp"
    bak = path + ".bak"
    # Use pyarrow engine by default
    df.to_parquet(tmp, engine="pyarrow", index=False)
    _fsync_file(tmp)
    # rotate backup
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
    _fsync_file(path)
    _fsync_dir(path)


# Backwards compat alias
_atomic_replace = atomic_replace


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


def repair_parquet_if_needed(path: str, required_columns: list[str] | None = None) -> None:
    """If main parquet is corrupt but .bak is valid (and schema matches), restore from .bak."""
    if not os.path.exists(path):
        # If only backup exists, promote it
        bak = path + ".bak"
        if os.path.exists(bak):
            try:
                os.replace(bak, path)
            except Exception:
                pass
        return
    try:
        df = pd.read_parquet(path, engine="pyarrow")
        if required_columns:
            for c in required_columns:
                if c not in df.columns:
                    raise ValueError("missing column")
    except Exception:
        bak = path + ".bak"
        if os.path.exists(bak):
            try:
                bdf = pd.read_parquet(bak, engine="pyarrow")
                if required_columns and any(c not in bdf.columns for c in required_columns):
                    return
                os.replace(bak, path)
            except Exception:
                pass
