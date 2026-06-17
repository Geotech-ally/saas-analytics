"""
Loads dataset files from shared storage (e.g., S3 or shared volume).
In production, use boto3/aiobotocore for S3; here uses local filesystem.
"""
import os
from pathlib import Path

import pandas as pd

MEDIA_ROOT = os.getenv("MEDIA_ROOT", "/app/media")
MAX_ROWS = 500_000


def load_dataset(dataset_id: str, org_id: str) -> pd.DataFrame:
    """
    Locate and load a dataset file into a DataFrame.
    Searches common paths used by Django's FileField.
    """
    # Search under media/datasets/ recursively
    base = Path(MEDIA_ROOT) / "datasets"
    matches = list(base.rglob(f"*{dataset_id}*")) if base.exists() else []

    if not matches:
        raise FileNotFoundError(f"No file found for dataset {dataset_id}")

    file_path = matches[0]
    ext = file_path.suffix.lower()

    if ext == ".csv":
        df = pd.read_csv(file_path, nrows=MAX_ROWS)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, nrows=MAX_ROWS)
    elif ext == ".json":
        df = pd.read_json(file_path)
        if len(df) > MAX_ROWS:
            df = df.head(MAX_ROWS)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # Basic cleanup
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df
