# NodeKavach — Technical Design

## 1. The 112:1 imbalance strategy — why PR-AUC, never accuracy

The BOI dataset has 81 mules among 9,082 accounts (~112:1). A model that predicts
"legitimate" for everyone scores **99.1% accuracy** while catching **zero mules**.
Accuracy is therefore actively misleading and we never report it as a primary
metric (it is shown only with an explicit warning).

We optimise and report on:

- **PR-AUC (Average Precision)** — the headline metric. Precision-recall area is
  the standard for extreme imbalance because it ignores the vast true-negative
  mass and focuses on the rare positive class.
- **Precision@K** (K = 50, 100) — operationally honest: "of the K riskiest
  accounts an analyst reviews, how many are real mules?"
- **ROC-AUC, KS statistic** — ranking quality.
- **Recall / F1 at the tuned threshold** — caught-mule rate at the operating point.

Imbalance is handled three ways, layered:

1. `scale_pos_weight = 112` in the XGBoost objective.
2. **SMOTE applied strictly inside each CV fold's training portion only** — never
   on validation rows, never on the held-out test split (leakage prevention).
3. **Threshold tuning on the PR curve** (maximising F1) instead of the default
   0.5. Model B's tuned threshold is ≈ 0.983.

## 2. Risk engine — probability → 0-100 score

Imbalance-tuned models produce sharply peaked probabilities, so a naive
`score = prob × 100` would push everything to the extremes. Instead the score is
**anchored on the tuned threshold** so it reads as distance from the decision
boundary:

```
threshold = tuned operating point (e.g. 0.983)
if prob >= threshold:  score = 60 + 40 · (prob − threshold) / (1 − threshold)
else:                  score = 60 · (prob / threshold)
```

This maps `prob = threshold → 60` (the HIGH/MEDIUM boundary), `prob = 1 → 100`,
`prob = 0 → 0`, giving a meaningful spread across the four severity bands:

| Band | Score | Action |
|------|-------|--------|
| CRITICAL | 80–100 | Immediate block recommended |
| HIGH | 60–79 | Step-up authentication required |
| MEDIUM | 40–59 | Enhanced monitoring |
| LOW | 0–39 | Allow, log only |

### 8 behavioural risk indicators

Each is a domain-informed proxy mapped from the closest available BOI feature and
normalised 0–1 for the progress-bar display:

| Indicator | Feature | Signal |
|-----------|---------|--------|
| Dormancy Signal | F2956 | Low tenure (mule median 41 vs legit 64) |
| Activity Flag | F115 | Mules ~22% higher (0.72 vs 0.59) |
| Legitimacy Gap | F2082 | Every confirmed mule has F2082 = 0 |
| Missingness Pattern | F3043 null | 82.7% of mules missing vs 64% legit |
| High-Risk Flag | F670 | F670=1 → 2.29% mule rate (2.6× avg) |
| Risk Score | F115 | Normalised transaction risk |
| Occupation Risk | F3891 | student 1.94%, agriculture 1.26%, housewife 0.45% |
| Account Standing | F3889 | L7D/L14D = 0% mule, L365D = 1.26% mule |

## 3. The 5 mule typology classification rules

A flagged account (score ≥ 40) is matched against weighted predicate sets; the
highest-scoring typology wins, with confidence blended from rule coverage and the
model risk score.

| Typology | Signature |
|----------|-----------|
| **LAYER_1_MULE** | High velocity + new account + transfers out — direct recipient of stolen funds |
| **PASS_THROUGH** | Near-zero F2082 + high cash-flow ratio (F1692) — receive & forward |
| **DORMANT_ACTIVATED** | Very low / reactivated tenure (F2956) — long-lapsed account suddenly active |
| **SYNTHETIC_IDENTITY** | F670=1 + student/agriculture + very new + (F3912 registry) |
| **NETWORK_HUB** | High F115 + wide counterparty spread (F527/F531) — layering hub |

Accounts scoring below 40 receive no typology (legitimate).

## 4. SHAP integration

- `shap.TreeExplainer` over the XGBoost booster (one explainer cached per model).
- Per prediction: top-10 features by `|SHAP|`, each mapped to a human-readable
  name and a direction (`+` increases risk → red, `−` reduces risk → green).
- Global importance (mean `|SHAP|` over a 400-row test sample) drives the Metrics
  feature-importance chart.
- The waterfall is rendered as pure CSS/SVG — no chart library.

Feature dictionary (the rest fall back to `Feature F{n}`):

```
F115  Transaction Risk Score      F2082 Legitimacy Indicator
F2956 Account Tenure              F3043 Activity Count
F670  High-Risk Flag              F3889 Account Standing Period
F3891 Account Holder Occupation   F3894 Account Holder Age
F3912 Fraud Registry Flag (Leakage Warning)
```

## 5. F3912 leakage handling — Model A vs Model B

F3912 has ~96.3% precision for mules and is the **#1 mutual-information feature** in
the dataset — a textbook post-labelling leakage signature (a feature that is only
populated *after* an account is confirmed fraudulent).

- **Model A** includes F3912. Result: PR-AUC = 1.000 on the held-out split. This is
  presented honestly as the leakage ceiling, with a UI warning banner.
- **Model B** excludes F3912 entirely (dropped before feature selection). Result:
  PR-AUC = 0.919. This is the production model and the default everywhere.

Training both and showing the gap is the project's core intellectual-honesty
statement: we demonstrate that we *understand* the data, rather than reporting an
inflated number.

## 6. Leakage-safe feature engineering

- Mutual-information ranking (`mutual_info_classif`) → retain top 200.
- The 18 BOI domain-hint features are force-included if present, plus the
  missingness indicators of any domain-hint feature.
- **The median imputer is fit on the training split only** and the same medians are
  applied at transform time. The held-out test split never influences imputation,
  feature selection, or threshold tuning.
- Missingness is treated as signal: a binary `_missing` indicator is added for any
  column with > 5% nulls. These indicators routinely surface in the top SHAP
  importances, confirming the thesis that *what is absent* discriminates mules.
