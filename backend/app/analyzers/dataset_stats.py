"""
dataset_stats.py — compute the descriptive statistics shown on the Dataset page.

Produces a DatasetStats object: row/feature counts, mule/legit counts, imbalance
ratio, sparsity, the feature-type breakdown (binary / low-card / continuous /
categorical) and the 18 domain-hint features table with per-feature mule vs
legit means and a KS statistic. Cached to JSON so the page is instant.

Run standalone:  python -m app.analyzers.dataset_stats
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from app.analyzers.dataset_loader import load_dataset
from app.config import (
    DATASET_STATS_PATH,
    DOMAIN_HINT_FEATURES,
    DOMAIN_HINT_MEANINGS,
    TARGET_COLUMN,
)
from app.models.schemas import (
    DatasetStats,
    DomainHintFeature,
    FeatureTypeBreakdown,
)


def _power(ks: float) -> str:
    if ks >= 0.5:
        return "High"
    if ks >= 0.25:
        return "Medium"
    return "Low"


def _feature_types(X: pd.DataFrame) -> FeatureTypeBreakdown:
    b = lc = cont = cat = 0
    for col in X.columns:
        if col in ("F3889", "F3891"):
            cat += 1
            continue
        nun = X[col].nunique(dropna=True)
        if nun <= 2:
            b += 1
        elif nun <= 10:
            lc += 1
        else:
            cont += 1
    return FeatureTypeBreakdown(binary=b, low_cardinality=lc, continuous=cont, categorical=cat)


def compute_dataset_stats(dataset_path=None, save: bool = True) -> DatasetStats:
    ds = load_dataset(dataset_path) if dataset_path else load_dataset()
    X, y = ds.X, ds.y

    mule_count = int(y.sum()) if y is not None else 0
    legit_count = int((y == 0).sum()) if y is not None else 0
    ratio = legit_count / mule_count if mule_count else 0
    sparsity = float(X.isna().mean().mean() * 100)

    # Domain-hint table (on raw, pre-impute values so means are meaningful).
    hints: list[DomainHintFeature] = []
    for f in DOMAIN_HINT_FEATURES:
        meaning = DOMAIN_HINT_MEANINGS.get(f, f"Feature {f}")
        if f not in X.columns or y is None:
            hints.append(DomainHintFeature(feature=f, decoded_meaning=meaning))
            continue
        col = X[f]
        mule_vals = col[y == 1].dropna()
        legit_vals = col[y == 0].dropna()
        mm = float(mule_vals.mean()) if len(mule_vals) else None
        lm = float(legit_vals.mean()) if len(legit_vals) else None
        ks = None
        if len(mule_vals) > 1 and len(legit_vals) > 1:
            ks = float(ks_2samp(mule_vals, legit_vals).statistic)
        hints.append(DomainHintFeature(
            feature=f, decoded_meaning=meaning,
            mule_mean=round(mm, 4) if mm is not None else None,
            legit_mean=round(lm, 4) if lm is not None else None,
            ks_stat=round(ks, 4) if ks is not None else None,
            discriminative_power=_power(ks) if ks is not None else "—",
        ))

    stats = DatasetStats(
        rows=ds.n_rows,
        features=ds.n_features,
        mule_count=mule_count,
        legit_count=legit_count,
        imbalance_ratio=f"{round(ratio)}:1" if ratio else "n/a",
        sparsity_pct=round(sparsity, 2),
        fully_null_columns=len(ds.dropped_null_columns),
        feature_type_breakdown=_feature_types(X),
        domain_hint_features=hints,
        sha256=ds.sha256,
    )
    if save:
        DATASET_STATS_PATH.write_text(stats.model_dump_json(indent=2), encoding="utf-8")
    return stats


def load_cached_stats() -> DatasetStats | None:
    if DATASET_STATS_PATH.exists():
        return DatasetStats.model_validate_json(DATASET_STATS_PATH.read_text(encoding="utf-8"))
    return None


def _selftest() -> None:
    print("== dataset_stats self-test ==")
    s = compute_dataset_stats()
    print(f"rows={s.rows} feats={s.features} mules={s.mule_count} legit={s.legit_count} "
          f"ratio={s.imbalance_ratio} sparsity={s.sparsity_pct}%")
    print(f"types: {s.feature_type_breakdown.model_dump()}")
    print("domain hints (top discriminative):")
    ranked = sorted(s.domain_hint_features, key=lambda h: h.ks_stat or 0, reverse=True)
    for h in ranked[:8]:
        print(f"   {h.feature:<7} {h.decoded_meaning:<28} mule={h.mule_mean} legit={h.legit_mean} "
              f"KS={h.ks_stat} ({h.discriminative_power})")
    print("OK")


if __name__ == "__main__":
    _selftest()
