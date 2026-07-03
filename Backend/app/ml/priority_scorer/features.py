from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

# columns we one-hot encode - just categories, no natural order between them
categorical_cols = [
    "complaint_category",
    "ward_code",
    "zone",
    "ward_type",
    "population_density",
    "complaint_channel",
    "complainant_type",
    "property_type",
]

# severity has a real order (Low < Medium < High < Critical) so we encode it
# as 0,1,2,3 instead of one-hot - keeps that ordering info for the model
severity_col = ["severity"]
severity_order = ["Low", "Medium", "High", "Critical"]

# numeric columns, already usable as-is
numeric_cols = [
    "ward_slum_percentage",
    "prior_complaints_count",
    "is_monsoon_season",
    "repeat_complainant",
    "has_photo_evidence",
    "has_gps_location",
]

# full list of what the model actually sees - train.py and predict.py both use this
FEATURE_COLUMNS = categorical_cols + severity_col + numeric_cols


def build_preprocessor():
    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_cols),
            ("severity", OrdinalEncoder(categories=[severity_order]), severity_col),
        ],
        remainder="passthrough",  # numeric_cols just pass through unchanged
    )