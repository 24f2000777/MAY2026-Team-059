<div align="center">

# 🏛️ NAGRIK AI

### AI-Powered Civic Complaint Management Platform

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)

**Team 059** · IIT Madras Software Engineering · 2026

---

`feature/priority-scorer-ml` — ML priority scoring module

</div>

---

## What's in this branch

This branch adds the **priority scoring ML module** — the part of NAGRIK AI that looks at a
newly filed complaint and assigns it a `priority_score` from 0 to 100, so high-risk complaints
(health hazards, flooding, dangerous trees) get surfaced to officers before cosmetic ones
(noise, litter).

It fits into the larger pipeline like this:

```
Citizen text (chatbot) → LLM extracts (location, problem_type, severity)
                        → Priority Scorer ML model (this branch) → priority_score (0-100)
                        → stored on the complaint record (Complaint.priority_score)
```

### The core problem this solves

**There is no `priority_score` column anywhere in the raw BMC dataset.** BMC never labeled
complaints with a priority — it's not in the data. That means normal supervised learning
(train a model against a real target column) isn't possible here. This branch solves that with
a two-stage approach:

1. **Invent the label ourselves** via a transparent, rule-based formula
   (`formula.py::calculate_priority`) using only fields known at the moment a complaint is
   filed — never anything that's only known after resolution.
2. **Train an ML model to reproduce that formula** (`train.py`), so scoring a new complaint at
   inference time is fast and doesn't require re-running the formula logic in production.

This is intentional, not a hack — it's documented here and in the code comments so nobody
mistakes the formula-derived label for a real ground-truth priority.

---

## Files

| File | What it does |
|------|---------------|
| `Backend/app/ml/priority_scorer/formula.py` | The priority formula (`calculate_priority`, plus a vectorized version for bulk use) and three validation checks that catch a broken/flat formula before it's used for training |
| `Backend/app/ml/priority_scorer/features.py` | Builds the `ColumnTransformer` that turns raw complaint fields into a model-ready input matrix (one-hot for categories, ordinal for severity, numeric passthrough) |
| `Backend/app/ml/priority_scorer/train.py` | Loads the dataset, applies the formula, validates it, trains the model, evaluates it, prints feature importances, and saves `model.joblib` |
| `Backend/app/ml/priority_scorer/predict.py` | `predict_priority(...)` — the function the FastAPI backend will call to score a real complaint |
| `Backend/app/ml/priority_scorer/model.joblib` | The trained model (committed to the branch, so you don't have to retrain to use it) |
| `Backend/app/ml/priority_scorer/data/` | Where `bmc_train.csv` / `bmc_test.csv` go (gitignored — not committed, too large) |

---

## How the formula works

`calculate_priority(row)` looks at six fields and produces a 0–100 score:

- **`severity`** (Low=20, Medium=45, High=70, Critical=90) — the dominant factor, since this is
  self-reported by the citizen/officer at filing time and is the single strongest urgency signal.
- **`complaint_category`** — a small bonus (+0 to +10) for categories that are inherently
  higher-risk regardless of severity (e.g. `Health / Epidemic`, `Drainage Overflow / Flooding`
  score higher than `Noise / Air Pollution`).
- **`ward_slum_percentage`** — a small equity boost (up to +8 at 100% slum), since
  under-resourced wards are more vulnerable when infrastructure fails.
- **`is_monsoon_season`** — a boost (+8), but only for weather-relevant categories (flooding,
  water supply/leakage, fallen trees) — it doesn't affect a noise complaint.
- **`repeat_complainant` / `prior_complaints_count`** — a small, capped boost, since repeated
  complaints about the same unresolved issue signal neglect.

The result is clipped to `[0, 100]`.

**Explicitly excluded from the formula and from the model** — anything that isn't known at the
moment a complaint is filed: `resolution_days`, `num_reassignments`, `complaint_status`,
`contractor_category`, `work_quality_rating`, `site_inspected`, `defect_liability_claim`,
`estimated_cost_inr`, `infrastructure_age_years`, `months_since_last_maintained` (all
post-resolution "leakage" fields), plus `media_attention` and `politically_sensitive` (not
reliably known at filing time either). These fields are used **only** in `formula.py`'s
validation checks, as a sanity check on the formula — never as a model input.

### Validation (done before trusting the formula)

`train.py` runs three checks on the formula's output before training anything:

1. **Distribution** — scores shouldn't all bunch into one narrow band.
2. **Severity consistency** — a `Critical` complaint should never score lower than a `Low` one
   in the same category, anywhere in the dataset.
3. **Proxy correlation** — checks the formula's scores correlate sensibly (not strongly, just
   directionally) with `resolution_days`, `media_attention`, and `politically_sensitive`
   *for validation only* — these three checks all passed on the full dataset.

---

## The model

- **Model:** `HistGradientBoostingRegressor` (scikit-learn) — chosen over `RandomForestRegressor`
  for training speed on the full 960,000-row training set; same `Pipeline` shape, and gradient
  boosting is listed as an acceptable alternative in the original spec for this module.
- **Data:** the dataset's own pre-split `bmc_train.csv` (960,000 rows) and `bmc_test.csv`
  (240,000 rows) — this is a real Kaggle-style train/test split, not one we manually cut
  ourselves (confirmed by `bmc_test.csv` lacking the `citizen_satisfied` column that
  `bmc_train.csv` still has).
- **Results on the test set:** MAE 0.17, RMSE 0.25, R² 1.000 — because the target label is a
  deterministic formula built from the same fields the model sees (no real-world noise), a
  near-perfect fit here means the model correctly learned the formula, not that something's
  wrong.
- **Feature importance** (permutation importance, on the held-out test set): `severity`
  dominates by roughly an order of magnitude over everything else, `complaint_category` is a
  distant second, and unrelated fields (`ward_code`, `zone`, `population_density`, etc.) have
  ~zero importance — matching the formula's design exactly.

---

## Setup & running it yourself

### Prerequisites
- Python 3.9+
- `bmc_train.csv` and `bmc_test.csv` (BMC complaint dataset) — not included in the repo, place
  them in `Backend/app/ml/priority_scorer/data/`

### Install dependencies
```bash
cd Backend
python -m venv venv
source venv/bin/activate          # Mac/Linux
pip install -r requirements.txt
```
Note: `requirements.txt` on this branch only lists what the ML module needs (`pandas`,
`numpy`, `scikit-learn`, `joblib`) — the full backend stack (FastAPI, SQLAlchemy, etc.) lives
on `feature/db-setup`, unmerged into `develop` as of this branch. Once that's resolved, this
file will need reconciling with the fuller list.

### Retrain the model (optional — `model.joblib` is already committed)
```bash
cd Backend/app/ml/priority_scorer
python3 train.py
```
Note: this trains on 960,000 rows and can take a while on CPU. Training was originally done on
Google Colab; see the code comments in `train.py` for why the model choice and data split were
made the way they are.

### Use the trained model directly
```bash
cd Backend/app/ml/priority_scorer
python3 predict.py
```
Runs the built-in sanity check (`if __name__ == "__main__":` block) — a high-risk complaint
combo should score much higher than a low-risk one.

To call it from other code:
```python
from app.ml.priority_scorer.predict import predict_priority

score = predict_priority(
    complaint_category="Drainage Overflow / Flooding",
    severity="Critical",
    ward_code="K/W",
    zone="Western",
    ward_type="Suburban",
    population_density="High",
    ward_slum_percentage=40,
    complaint_channel="WhatsApp",
    complainant_type="Resident",
    property_type="Slum/Chawl",
    is_monsoon_season=1,
    repeat_complainant=0,
    prior_complaints_count=1,
)
```
Raises `ValueError` if `complaint_category` or `severity` isn't one of the known values,
instead of silently mis-scoring.

---

## Chatbot / API interface contract

`predict_priority()` needs 13+ fields, but the citizen should never have to fill out a form —
they just describe their problem in a chat message (e.g. *"hey I live in sector 5 Dharavi and
there's a pothole in front of my house, want it fixed"*). Getting from that free-text message to
a full `predict_priority()` call is split between the LLM extraction step and the backend, so no
extra fields are ever surfaced to the citizen:

### Extracted by the LLM (from the citizen's message)
| Field | How |
|-------|-----|
| `complaint_category` | The problem type ("pothole" → `Pothole / Road Damage`) |
| location (raw text) | Used below to look up ward fields — not passed to the model directly |
| `severity` | Inferred from the urgency/language used (e.g. "massive pothole, someone got hurt" → `High`/`Critical`); defaults to `Medium` when there's no clear signal either way |

### Derived automatically by the backend — no citizen or LLM input needed
| Field | How |
|-------|-----|
| `ward_code`, `zone`, `ward_type`, `population_density`, `ward_slum_percentage` | Fuzzy-match the LLM's extracted location text against a static ward reference table (built once from this dataset's own `ward_area` → attributes mapping — no external geocoding needed for this project) |
| `is_monsoon_season` | `1` if the current month is June–September, else `0` |
| `repeat_complainant`, `prior_complaints_count` | Query this citizen's past complaints in the DB at the moment the new one is created |
| `has_photo_evidence`, `has_gps_location` | Whether the chat session actually captured a photo attachment / GPS share |
| `complaint_channel` | Hardcoded to whichever existing trained value matches this chatbot (reuse a real trained category — an unseen value gets zeroed out by `handle_unknown='ignore'`, losing signal) |
| `complainant_type`, `property_type` | Defaulted (e.g. `"Resident"`) unless there's a reason to have the LLM extract these too |

This assembly logic (ward lookup + date check + DB query, gluing the LLM's output to
`predict_priority()`'s full signature) belongs in the API layer that calls this module, not
inside `priority_scorer/` itself — this module doesn't have DB access.

---

## What's not done yet

- **Not wired into the FastAPI app.** `predict_priority` is a standalone function; it still
  needs to be called from a route (and the model should be loaded once via a FastAPI lifespan
  event, not per-request — `predict.py` already loads it once at import time, which is
  compatible with that).
- **The chatbot/API assembly layer described above isn't built yet** — the ward reference
  table, the location fuzzy-matcher, and the DB lookups for repeat-complainant history all still
  need to be written, most likely in the API/chatbot module rather than here.
- **This branch was created off `develop`, which doesn't yet have the database models**
  (`config.py`, `model.py`, etc. — those currently only exist on `feature/db-setup`, unmerged).
  Once that's resolved, this branch will need a rebase to pick up `Complaint.priority_score`
  and the rest of the schema.

---

<div align="center">

**NAGRIK AI** · Team 059 · IIT Madras SE 2026

</div>
