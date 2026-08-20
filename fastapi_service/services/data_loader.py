"""
Loads dataset files from shared storage (e.g., S3 or shared volume).
In production, use boto3/aiobotocore for S3; here uses local filesystem.
"""
import os
from pathlib import Path

import pandas as pd

MAX_ROWS = 500_000
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_JSON_FILE_SIZE = 5 * 1024 * 1024  # 5 MB — JSON loads entire file into memory


def _get_media_root() -> Path:
    return Path(os.getenv("MEDIA_ROOT", "/app/media"))


def _validate_path_canonical(file_path: Path, media_root: Path) -> None:
    try:
        resolved = file_path.resolve()
        resolved.relative_to(media_root.resolve())
    except ValueError:
        raise ValueError("Dataset file path is outside the allowed storage directory.")


def load_dataset(dataset_id: str, org_id: str) -> pd.DataFrame:
    """
    Locate and load a dataset file into a DataFrame.

    SECURITY: uses the canonical file path from the Dataset database record
    to prevent wildcard-based ambiguity. Only loads files belonging to the
    caller's own organization.
    """
    if not org_id:
        raise FileNotFoundError("No organization associated with this request.")

    media_root = _get_media_root()

    try:
        from apps.datasets.models import Dataset
        dataset = Dataset.objects.select_related("organization").get(id=dataset_id)
        if str(dataset.organization_id) != str(org_id):
            raise ValueError("Dataset does not belong to the caller's organization.")
        file_path = Path(dataset.file.path)
    except ImportError:
        raise RuntimeError("Dataset authorization service unavailable.")
    except Dataset.DoesNotExist:
        raise FileNotFoundError(f"Dataset {dataset_id} not found.")

    _validate_path_canonical(file_path, media_root)

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    if file_path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("Dataset file exceeds maximum allowed size.")

    ext = file_path.suffix.lower()

    try:
        if ext == ".csv":
            df = pd.read_csv(file_path, nrows=MAX_ROWS)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, nrows=MAX_ROWS)
        elif ext == ".json":
            if file_path.stat().st_size > MAX_JSON_FILE_SIZE:
                raise ValueError("JSON file exceeds maximum allowed size for memory-safe processing.")
            df = pd.read_json(file_path)
            if len(df) > MAX_ROWS:
                df = df.head(MAX_ROWS)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    except pd.errors.ParserError as exc:
        raise ValueError(f"Malformed file: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError("File encoding is not valid. Use UTF-8.") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to read dataset file: {exc}") from exc

    if len(df) > MAX_ROWS:
        df = df.head(MAX_ROWS)

    if len(df) == 0:
        raise ValueError("Dataset is empty.")

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df
