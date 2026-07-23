from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
import joblib

from features import FEATURE_COLUMNS, severity_order
from formula import VALID_CATEGORIES

MODEL_PATH = Path(__file__).parent / "model.joblib"

# lazy-loaded on first prediction rather than at import time, so importing
# this module (e.g. from a test, or a script that just wants FEATURE_COLUMNS)
# never does blocking disk I/O as a side effect
_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline


@dataclass
class ComplaintFeatures:
    complaint_category: str
    severity: str
    ward_code: str
    zone: str
    ward_type: str
    population_density: str
    ward_slum_percentage: float
    complaint_channel: str
    complainant_type: str
    property_type: str
    is_monsoon_season: int
    repeat_complainant: int
    prior_complaints_count: int
    has_photo_evidence: int = 0
    has_gps_location: int = 0


def predict_priority(features: ComplaintFeatures) -> float:
    if features.complaint_category not in VALID_CATEGORIES:
        raise ValueError(f"unknown complaint_category: {features.complaint_category}")
    if features.severity not in severity_order:
        raise ValueError(f"unknown severity: {features.severity}")

    input_df = pd.DataFrame([asdict(features)])[FEATURE_COLUMNS]
    prediction = _get_pipeline().predict(input_df)[0]

    return max(0.0, min(100.0, float(prediction)))

if __name__ == "__main__":
    urgent = predict_priority(ComplaintFeatures(
        complaint_category="Health / Epidemic",
        severity="Critical",
        ward_code="A",
        zone="City",
        ward_type="South",
        population_density="Very High",
        ward_slum_percentage=80,
        complaint_channel="1916 Helpline",
        complainant_type="Resident",
        property_type="Slum/Chawl",
        is_monsoon_season=1,
        repeat_complainant=1,
        prior_complaints_count=4,
    ))

    minor = predict_priority(ComplaintFeatures(
        complaint_category="Noise / Air Pollution",
        severity="Low",
        ward_code="A",
        zone="City",
        ward_type="South",
        population_density="Low",
        ward_slum_percentage=5,
        complaint_channel="MyBMC App",
        complainant_type="Resident",
        property_type="Bungalow/Villa",
        is_monsoon_season=0,
        repeat_complainant=0,
        prior_complaints_count=0,
    ))

    print(f"urgent case (Health/Epidemic, Critical, high slum%, monsoon): {urgent:.1f}")
    print(f"minor case (Noise, Low, low slum%, non-monsoon): {minor:.1f}")
    assert urgent > minor, "urgent case should score higher than minor case!"
    print("sanity check passed - urgent scores higher than minor")