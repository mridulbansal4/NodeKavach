"""
dataset_loader.py — BOI dataset ingestion & cleaning.

Responsibilities:
  * Load the BOI CSV (boi_dataset.csv or an uploaded CSV).
  * Drop the leading unnamed index column.
  * Drop fully-null columns automatically (the 63 dead columns).
  * Add binary missingness-indicator features for any column with >5% nulls
    (missingness is itself a fraud signal in this dataset).
  * Separate F3924 as the target if present.
  * Label-encode the two categorical features F3889 and F3891.
  * Return a cleaned numeric feature matrix plus metadata.

Run standalone:  python -m app.analyzers.dataset_loader
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.config import (
    DEFAULT_DATASET,
    F3889_ENCODING,
    F3891_ENCODING,
    INDEX_COLUMN,
    TARGET_COLUMN,
)

MISSINGNESS_THRESHOLD = 0.05  # >5% null -> add an indicator feature
MISSINGNESS_SUFFIX = "_missing"


@dataclass
class LoadedDataset:
    """The product of loading + cleaning a BOI CSV."""

    X: pd.DataFrame                       # cleaned numeric feature matrix
    y: Optional[pd.Series]                # target (None if absent)
    feature_names: list[str] = field(default_factory=list)
    dropped_null_columns: list[str] = field(default_factory=list)
    missingness_features: list[str] = field(default_factory=list)
    n_rows: int = 0
    n_features: int = 0
    sha256: Optional[str] = None
    raw: Optional[pd.DataFrame] = None    # original (post index-drop) frame


def sha256_of_file(path: str | Path) -> str:
    """SHA-256 of a file, streamed (datasets are >100MB)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _encode_categoricals(df: pd.DataFrame) -> None:
    """In-place label-encode F3889 (standing) and F3891 (occupation)."""
    if "F3889" in df.columns:
        df["F3889"] = (
            df["F3889"].astype(str).str.strip()
            .map(F3889_ENCODING)
        )
    if "F3891" in df.columns:
        df["F3891"] = (
            df["F3891"].astype(str).str.strip().str.lower()
            .map(F3891_ENCODING)
        )


def load_dataset(
    path: str | Path = DEFAULT_DATASET,
    *,
    compute_hash: bool = True,
    keep_raw: bool = False,
) -> LoadedDataset:
    """Load & clean a BOI CSV into a numeric feature matrix + target."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path, low_memory=False)

    # 1. Drop the leading unnamed index column (saved by pandas to_csv).
    for idx_col in (INDEX_COLUMN, "Unnamed: 0", df.columns[0]):
        if idx_col in df.columns and (
            idx_col == INDEX_COLUMN
            or str(idx_col).startswith("Unnamed")
        ):
            df = df.drop(columns=[idx_col])
            break

    raw = df.copy() if keep_raw else None

    # 2. Separate the target if present.
    y: Optional[pd.Series] = None
    if TARGET_COLUMN in df.columns:
        y = pd.to_numeric(df[TARGET_COLUMN], errors="coerce").fillna(0).astype(int)
        df = df.drop(columns=[TARGET_COLUMN])

    # 3. Drop fully-null columns (the 63 dead columns).
    null_fraction = df.isna().mean()
    dropped_null = null_fraction[null_fraction >= 1.0].index.tolist()
    if dropped_null:
        df = df.drop(columns=dropped_null)

    # 4. Encode the two known categoricals BEFORE numeric coercion.
    _encode_categoricals(df)

    # 5. Coerce everything to numeric (non-parseable strings -> NaN).
    #    NB: pandas 3.0 reads text columns as the dedicated `str` dtype (not
    #    `object`), so we test for *non-numeric* rather than `== object`.
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 6. Add missingness-indicator features for columns with >5% nulls.
    missingness_features: list[str] = []
    null_fraction = df.isna().mean()
    high_null_cols = null_fraction[null_fraction > MISSINGNESS_THRESHOLD].index.tolist()
    indicators = {}
    for col in high_null_cols:
        ind_name = f"{col}{MISSINGNESS_SUFFIX}"
        indicators[ind_name] = df[col].isna().astype(np.int8)
        missingness_features.append(ind_name)
    if indicators:
        df = pd.concat([df, pd.DataFrame(indicators, index=df.index)], axis=1)

    feature_names = df.columns.tolist()

    return LoadedDataset(
        X=df,
        y=y,
        feature_names=feature_names,
        dropped_null_columns=dropped_null,
        missingness_features=missingness_features,
        n_rows=len(df),
        n_features=len(feature_names),
        sha256=sha256_of_file(path) if compute_hash else None,
        raw=raw,
    )


def _selftest() -> None:
    print("== dataset_loader self-test ==")
    ds = load_dataset(keep_raw=True)
    print(f"rows                 : {ds.n_rows}")
    print(f"features (post-clean): {ds.n_features}")
    print(f"dropped null columns : {len(ds.dropped_null_columns)}")
    print(f"missingness features : {len(ds.missingness_features)}")
    if ds.y is not None:
        mules = int(ds.y.sum())
        legit = int((ds.y == 0).sum())
        ratio = legit / max(mules, 1)
        print(f"target present       : yes  (mules={mules}, legit={legit}, ratio≈{ratio:.0f}:1)")
    else:
        print("target present       : no")
    # sanity: encodings applied
    for c in ("F3889", "F3891"):
        if c in ds.X.columns:
            print(f"{c} encoded dtype     : {ds.X[c].dtype}  uniques={sorted(ds.X[c].dropna().unique())[:8]}")
    print(f"sha256               : {ds.sha256[:16]}...")
    print("OK")


if __name__ == "__main__":
    _selftest()
