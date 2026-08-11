"""
Loads dataset files from shared storage (e.g., S3 or shared volume).
In production, use boto3/aiobotocore for S3; here uses local filesystem.

Tenant isolation is ENFORCED here by validating that the loaded file
resides under the requesting org's directory. This is defense-in-depth
on top of Django's proxy validation.
"""
import os
from pathlib import Path

import pandas as pd

MAX_ROWS = 500_000


def _get_media_root() -> Path:
    return Path(os.getenv("MEDIA_ROOT", "/app/media"))


def _validate_org_path(file_path: Path, org_id: str) -> None:
    base = _get_media_root().resolve()
    try:
        resolved = file_path.resolve()
        relative = resolved.relative_to(base)
        parts = relative.parts
        if len(parts) < 2 or str(parts[1]) != str(org_id):
            raise ValueError("Access denied: file does not belong to your organization.")
    except ValueError as exc:
        raise ValueError(f"Access denied: {exc}")


def load_dataset(dataset_id: str, org_id: str) -> pd.DataFrame:
    """
    Locate and load a dataset file into a DataFrame.

    Tenant ownership is verified by checking the file path matches the
    provided org_id. This is defense-in-depth on top of Django proxy validation.
    """
    base = _get_media_root() / "datasets" / str(org_id)
    if not base.exists():
        raise FileNotFoundError(f"No datasets directory for organization {org_id}")

    matches = list(base.rglob(f"*{dataset_id}*"))

    if not matches:
        raise FileNotFoundError(f"No file found for dataset {dataset_id} in organization {org_id}")

    file_path = None
    for match in matches:
        _validate_org_path(match, org_id)
        if match.is_file():
            file_path = match
            break

    if file_path is None:
        raise FileNotFoundError(f"No valid file found for dataset {dataset_id}")

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

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df
