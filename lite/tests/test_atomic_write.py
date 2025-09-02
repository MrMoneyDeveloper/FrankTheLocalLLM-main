import os
import shutil
import tempfile
import importlib

import pandas as pd


def test_parquet_backup_fallback():
    tmp = tempfile.mkdtemp()
    os.environ["DATA_DIR"] = tmp
    # Reload modules to pick up new DATA_DIR
    from lite.src.storage import parquet_util as pq
    from lite.src.storage import config as cfg

    importlib.reload(cfg)
    importlib.reload(pq)

    cfg.ensure_storage_dirs()

    path = pq.table_path("notes_index")
    df1 = pd.DataFrame([{"note_id": "n1", "title": "t", "path": "p", "updated_at": 1, "size": 1, "sha256": "x"}])
    pq.atomic_replace(path, df1)
    # Simulate crash during next write: leave main corrupt but keep .bak valid
    # Move good main to .bak
    bak = path + ".bak"
    if os.path.exists(bak):
        os.remove(bak)
    os.replace(path, bak)
    with open(path, "wb") as f:
        f.write(b"not a parquet file")

    # Safe read should fall back to .bak
    df = pq.read_parquet_safe(path)
    assert not df.empty
    assert list(df.columns) == ["note_id", "title", "path", "updated_at", "size", "sha256"]


def test_settings_hot_apply():
    tmp = tempfile.mkdtemp()
    os.environ["DATA_DIR"] = tmp
    from lite.src.storage import config as cfg

    importlib.reload(cfg)
    s = cfg.load_settings()
    assert s["CHUNK_SIZE"] > 0
    new = cfg.save_settings({**s, "CHUNK_SIZE": s["CHUNK_SIZE"] + 1})
    again = cfg.load_settings()
    assert new["CHUNK_SIZE"] == again["CHUNK_SIZE"]

