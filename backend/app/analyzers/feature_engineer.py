"""
feature_engineer.py — feature selection & leakage-safe imputation.

Responsibilities:
  * Mutual-Information filter: score every feature against the target F3924,
    rank, and retain the top 200.
  * Always prioritise the 18 BOI domain-hint features (force-included if present).
  * Track the F3912 leakage flag; allow excluding it entirely (Model B).
  * Fit a median imputer on the TRAINING split ONLY (leakage prevention),
    then transform any matrix with those stored medians.

The class is sklearn-style: fit(X_train, y_train) then transform(X). This is
what makes the leakage guarantee enforceable — medians and the selected
feature set are learned from training rows alone.

Run standalone:  python -m app.analyzers.feature_engineer
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif

from app.config import (
    DOMAIN_HINT_FEATURES,
    LEAKAGE_FEATURE,
    RANDOM_STATE,
    TOP_K_FEATURES,
)


@dataclass
class FeatureEngineer:
    top_k: int = TOP_K_FEATURES
    include_f3912: bool = True
    prioritize: list[str] = field(default_factory=lambda: list(DOMAIN_HINT_FEATURES))

    # learned state
    selected_features: list[str] = field(default_factory=list)
    medians: dict[str, float] = field(default_factory=dict)
    mi_scores: dict[str, float] = field(default_factory=dict)
    f3912_present: bool = False
    fitted: bool = False

    # ------------------------------------------------------------------ #
    def fit(self, X: pd.DataFrame, y: pd.Series) -> "FeatureEngineer":
        X = X.copy()
        self.f3912_present = LEAKAGE_FEATURE in X.columns

        # Model B: drop the leakage feature entirely before anything else.
        if not self.include_f3912 and self.f3912_present:
            X = X.drop(columns=[LEAKAGE_FEATURE])

        # MI needs a dense matrix — impute with column medians for scoring only.
        med = X.median(numeric_only=True)
        X_mi = X.fillna(med).fillna(0.0)

        mi = mutual_info_classif(
            X_mi.values, y.values,
            discrete_features=False,
            random_state=RANDOM_STATE,
        )
        self.mi_scores = {c: float(s) for c, s in zip(X.columns, mi)}

        ranked = sorted(self.mi_scores, key=self.mi_scores.get, reverse=True)

        # Force-include prioritised domain-hint features that are present,
        # plus their missingness indicators if any.
        forced = [f for f in self.prioritize if f in X.columns]
        forced += [
            c for c in X.columns
            if c.endswith("_missing") and c[:-len("_missing")] in self.prioritize
        ]
        if self.include_f3912 and self.f3912_present:
            forced.append(LEAKAGE_FEATURE)

        selected: list[str] = []
        seen: set[str] = set()
        for f in forced:
            if f not in seen:
                selected.append(f)
                seen.add(f)
        for f in ranked:
            if len(selected) >= self.top_k:
                break
            if f not in seen:
                selected.append(f)
                seen.add(f)

        self.selected_features = selected
        self.medians = {c: float(med.get(c, 0.0)) for c in selected}
        self.fitted = True
        return self

    # ------------------------------------------------------------------ #
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            raise RuntimeError("FeatureEngineer.transform() called before fit().")
        # Reindex to the exact selected feature set (missing cols -> NaN).
        out = X.reindex(columns=self.selected_features)
        # Impute with TRAINING medians (never recomputed on this matrix).
        for c in self.selected_features:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(self.medians[c])
        return out

    def fit_transform(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        return self.fit(X, y).transform(X)

    # ------------------------------------------------------------------ #
    @property
    def has_leakage_feature(self) -> bool:
        return self.include_f3912 and self.f3912_present and LEAKAGE_FEATURE in self.selected_features

    def top_mi(self, n: int = 20) -> list[tuple[str, float]]:
        return sorted(self.mi_scores.items(), key=lambda kv: kv[1], reverse=True)[:n]


def _selftest() -> None:
    from sklearn.model_selection import train_test_split

    from app.analyzers.dataset_loader import load_dataset

    print("== feature_engineer self-test ==")
    ds = load_dataset()
    assert ds.y is not None, "need target for selftest"
    X_tr, X_te, y_tr, y_te = train_test_split(
        ds.X, ds.y, test_size=0.2, stratify=ds.y, random_state=RANDOM_STATE
    )

    fe = FeatureEngineer(include_f3912=True).fit(X_tr, y_tr)
    Xt = fe.transform(X_te)
    print(f"selected features    : {len(fe.selected_features)}")
    print(f"F3912 present/used   : {fe.f3912_present} / {fe.has_leakage_feature}")
    print(f"transformed test NaNs: {int(Xt.isna().sum().sum())} (must be 0)")
    print("top-8 MI features:")
    for name, score in fe.top_mi(8):
        print(f"   {name:<14} {score:.4f}")
    domain_in = [f for f in DOMAIN_HINT_FEATURES if f in fe.selected_features]
    print(f"domain hints retained: {len(domain_in)}/{len(DOMAIN_HINT_FEATURES)}")

    feb = FeatureEngineer(include_f3912=False).fit(X_tr, y_tr)
    print(f"Model B excludes F3912: {LEAKAGE_FEATURE not in feb.selected_features}")
    print("OK")


if __name__ == "__main__":
    _selftest()
