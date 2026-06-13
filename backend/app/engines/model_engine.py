"""
model_engine.py — XGBoost training with imbalance handling & threshold tuning.

Strategy (faithful to the BOI 112:1 problem):
  * scale_pos_weight = 112 to weight the rare mule class in the XGBoost objective.
  * Stratified 5-fold CV with SMOTE applied STRICTLY inside each fold's training
    portion only (never on validation rows — leakage prevention). Out-of-fold
    (OOF) probabilities drive the PRIMARY metric, PR-AUC.
  * Decision threshold tuned on the OOF Precision-Recall curve (NOT the default
    0.5) by maximising F1. The same SMOTE + scale_pos_weight recipe is used for
    the folds AND the final fit, so the tuned threshold transfers consistently.
  * Two models trained:
      - Model A: WITH F3912 (shows maximum, leakage-inflated performance).
      - Model B: WITHOUT F3912 (the generalisation / production model).

Run standalone:  python -m app.engines.model_engine     (pre-trains both models)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.model_selection import StratifiedKFold, train_test_split
from xgboost import XGBClassifier

from app.analyzers.dataset_loader import load_dataset
from app.analyzers.feature_engineer import FeatureEngineer
from app.config import (
    MODEL_A_PATH,
    MODEL_B_PATH,
    RANDOM_STATE,
    SCALE_POS_WEIGHT,
)

TEST_SIZE = 0.20
N_SPLITS = 5


def _xgb(scale_pos_weight: float = SCALE_POS_WEIGHT) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=1,
        gamma=0.0,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        tree_method="hist",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )


def _smote_resample(X: pd.DataFrame, y: pd.Series):
    """SMOTE the training rows; k_neighbors adapts to the minority count."""
    n_pos = int((y == 1).sum())
    if n_pos < 2:
        return X, y
    k = min(5, max(1, n_pos - 1))
    sm = SMOTE(random_state=RANDOM_STATE, k_neighbors=k)
    Xr, yr = sm.fit_resample(X, y)
    return Xr, yr


@dataclass
class TrainedModel:
    name: str
    include_f3912: bool
    feature_engineer: FeatureEngineer
    booster: XGBClassifier
    threshold: float = 0.5
    cv_pr_auc: float = 0.0
    selected_features: list[str] = field(default_factory=list)
    test_index: list[int] = field(default_factory=list)   # held-out test rows (positional)
    train_time_s: float = 0.0

    # ----- inference ------------------------------------------------------ #
    def _prep(self, X_raw: pd.DataFrame) -> pd.DataFrame:
        return self.feature_engineer.transform(X_raw)

    def predict_proba(self, X_raw: pd.DataFrame) -> np.ndarray:
        Xt = self._prep(X_raw)
        return self.booster.predict_proba(Xt.values)[:, 1]

    def predict_proba_single(self, features: dict) -> float:
        row = pd.DataFrame([features])
        return float(self.predict_proba(row)[0])


def _tune_threshold(y_true: np.ndarray, proba: np.ndarray) -> float:
    """Pick the threshold maximising F1 on the PR curve."""
    prec, rec, thr = precision_recall_curve(y_true, proba)
    # precision_recall_curve returns len(thr) = len(prec)-1
    f1 = np.divide(
        2 * prec[:-1] * rec[:-1],
        (prec[:-1] + rec[:-1]),
        out=np.zeros_like(prec[:-1]),
        where=(prec[:-1] + rec[:-1]) > 0,
    )
    if len(thr) == 0:
        return 0.5
    return float(thr[int(np.argmax(f1))])


def train_one(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    include_f3912: bool,
    name: str,
) -> TrainedModel:
    t0 = time.time()

    # Deterministic stratified hold-out test split (positional indices).
    pos_index = np.arange(len(X))
    tr_pos, te_pos = train_test_split(
        pos_index, test_size=TEST_SIZE, stratify=y.values, random_state=RANDOM_STATE
    )
    X_tr, y_tr = X.iloc[tr_pos], y.iloc[tr_pos]

    # Feature engineering fit on TRAIN ONLY.
    fe = FeatureEngineer(include_f3912=include_f3912).fit(X_tr, y_tr)
    X_tr_t = fe.transform(X_tr)

    # OOF cross-validation: SMOTE strictly inside each fold's training portion.
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    oof = np.zeros(len(X_tr_t))
    for fold_tr, fold_val in skf.split(X_tr_t, y_tr):
        Xf, yf = X_tr_t.iloc[fold_tr], y_tr.iloc[fold_tr]
        Xf_res, yf_res = _smote_resample(Xf, yf)
        m = _xgb()
        m.fit(Xf_res.values, yf_res.values)
        oof[fold_val] = m.predict_proba(X_tr_t.iloc[fold_val].values)[:, 1]

    cv_pr_auc = float(average_precision_score(y_tr.values, oof))
    threshold = _tune_threshold(y_tr.values, oof)

    # Final fit: same recipe (SMOTE + scale_pos_weight) on the full train split.
    X_res, y_res = _smote_resample(X_tr_t, y_tr)
    booster = _xgb()
    booster.fit(X_res.values, y_res.values)

    return TrainedModel(
        name=name,
        include_f3912=include_f3912,
        feature_engineer=fe,
        booster=booster,
        threshold=threshold,
        cv_pr_auc=cv_pr_auc,
        selected_features=fe.selected_features,
        test_index=te_pos.tolist(),
        train_time_s=round(time.time() - t0, 2),
    )


class ModelEngine:
    """Loads / trains / serves the two models. Model B is the production default."""

    def __init__(self) -> None:
        self.model_a: Optional[TrainedModel] = None
        self.model_b: Optional[TrainedModel] = None

    # ----- lifecycle ------------------------------------------------------ #
    def train(self, dataset_path=None) -> dict:
        ds = load_dataset(dataset_path) if dataset_path else load_dataset()
        if ds.y is None:
            raise ValueError("Training requires the target column F3924.")
        self.model_a = train_one(ds.X, ds.y, include_f3912=True, name="Model A")
        self.model_b = train_one(ds.X, ds.y, include_f3912=False, name="Model B")
        self.save()
        return {
            "model_a": {"cv_pr_auc": self.model_a.cv_pr_auc, "threshold": self.model_a.threshold,
                        "features": len(self.model_a.selected_features), "train_time_s": self.model_a.train_time_s},
            "model_b": {"cv_pr_auc": self.model_b.cv_pr_auc, "threshold": self.model_b.threshold,
                        "features": len(self.model_b.selected_features), "train_time_s": self.model_b.train_time_s},
        }

    def save(self) -> None:
        if self.model_a:
            joblib.dump(self.model_a, MODEL_A_PATH)
        if self.model_b:
            joblib.dump(self.model_b, MODEL_B_PATH)

    def load(self) -> bool:
        ok = False
        if MODEL_A_PATH.exists():
            self.model_a = joblib.load(MODEL_A_PATH)
            ok = True
        if MODEL_B_PATH.exists():
            self.model_b = joblib.load(MODEL_B_PATH)
            ok = True
        return ok

    @property
    def is_loaded(self) -> bool:
        return self.model_b is not None

    # ----- serving (Model B = production default) ------------------------- #
    def production_model(self) -> TrainedModel:
        if self.model_b is None:
            raise RuntimeError("Model B not loaded. Train first.")
        return self.model_b

    def get_threshold(self) -> float:
        return self.production_model().threshold

    def predict_single(self, features: dict, use_model: str = "B") -> float:
        m = self.model_a if use_model.upper() == "A" else self.model_b
        if m is None:
            raise RuntimeError(f"Model {use_model} not loaded.")
        return m.predict_proba_single(features)

    def predict_batch(self, df: pd.DataFrame, use_model: str = "B") -> np.ndarray:
        m = self.model_a if use_model.upper() == "A" else self.model_b
        if m is None:
            raise RuntimeError(f"Model {use_model} not loaded.")
        return m.predict_proba(df)


# Module-level singleton (imported by routes & engines).
ENGINE = ModelEngine()


def _selftest() -> None:
    print("== model_engine: training both models ==")
    eng = ModelEngine()
    summary = eng.train()
    for name in ("model_a", "model_b"):
        s = summary[name]
        print(f"{name}: PR-AUC(cv)={s['cv_pr_auc']:.4f}  thr={s['threshold']:.4f}  "
              f"feats={s['features']}  time={s['train_time_s']}s")
    print(f"saved -> {MODEL_A_PATH.name}, {MODEL_B_PATH.name}")
    print("OK")


if __name__ == "__main__":
    # Delegate to the imported package module so that TrainedModel (and the
    # FeatureEngineer it holds) pickle under 'app.engines.model_engine' rather
    # than '__main__' — otherwise the saved .pkl can't be loaded by the API.
    from app.engines.model_engine import _selftest as _packaged_selftest
    _packaged_selftest()
