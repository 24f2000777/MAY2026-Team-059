import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.inspection import permutation_importance

from formula import calculate_priority_vectorized, check_distribution, check_severity_consistency, check_proxy_correlation
from features import build_preprocessor, FEATURE_COLUMNS

DATA_DIR = Path(__file__).parent / "data"

# --- load the dataset's own pre-split train/test files ---
# bmc_train.csv (960k rows) and bmc_test.csv (240k rows) are the original
# Kaggle-style 80/20 split - confirmed real by bmc_test.csv missing the
# citizen_satisfied column that bmc_train.csv still has. we use them as-is
# instead of doing our own train_test_split.
train_df = pd.read_csv(DATA_DIR / "bmc_train.csv")
test_df = pd.read_csv(DATA_DIR / "bmc_test.csv")

print(f"train rows: {len(train_df)}, test rows: {len(test_df)}")

# --- apply our priority formula to both, since neither has it ---
# vectorized version - the row-by-row calculate_priority in formula.py is
# too slow on 960k rows, this does the same math column-wise instead
train_df["priority_score"] = calculate_priority_vectorized(train_df)
test_df["priority_score"] = calculate_priority_vectorized(test_df)

train_df.to_csv(DATA_DIR / "bmc_train_with_priority.csv", index=False)
test_df.to_csv(DATA_DIR / "bmc_test_with_priority.csv", index=False)

# --- validate the formula on the training data ---
print("\n--- validation checks ---")
check_distribution(train_df["priority_score"])
check_severity_consistency(train_df)
check_proxy_correlation(train_df)

# --- build features + target ---
X_train, y_train = train_df[FEATURE_COLUMNS], train_df["priority_score"]
X_test, y_test = test_df[FEATURE_COLUMNS], test_df["priority_score"]

# --- train ---
# using HistGradientBoostingRegressor instead of RandomForestRegressor -
# much faster on 960k rows, same Pipeline shape, and the spec lists gradient
# boosting as an acceptable alternative model
pipeline = Pipeline([
    ("preprocess", build_preprocessor()),
    ("model", HistGradientBoostingRegressor(random_state=42)),
])

print("\ntraining model...")
pipeline.fit(X_train, y_train)

# --- evaluate ---
predictions = pipeline.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
rmse = mean_squared_error(y_test, predictions) ** 0.5
r2 = r2_score(y_test, predictions)

print(f"\nMAE: {mae:.2f}")
print(f"RMSE: {rmse:.2f}")
print(f"R2: {r2:.3f}")

# --- feature importance ---
# permutation_importance shuffles each raw input column (not the expanded
# one-hot columns) one at a time and measures how much error gets worse -
# so importances line up with FEATURE_COLUMNS, not get_feature_names_out()
print("\n--- feature importance ---")
result = permutation_importance(pipeline, X_test, y_test, n_repeats=5, random_state=42, n_jobs=-1)
importances = result.importances_mean
sorted_idx = np.argsort(importances)[::-1]
for i in sorted_idx:
    print(f"{FEATURE_COLUMNS[i]}: {importances[i]:.4f}")

# --- save model ---
joblib.dump(pipeline, Path(__file__).parent / "model.joblib")
print("\nsaved model.joblib")
