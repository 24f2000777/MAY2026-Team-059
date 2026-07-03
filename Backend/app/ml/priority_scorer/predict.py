from pathlib import Path
import pandas as pd
import joblib

from features import FEATURE_COLUMNS, severity_order

MODEL_PATH = Path(__file__).parent / "model.joblib"

# load the trained pipeline once when this module is imported - not per request
pipeline = joblib.load(MODEL_PATH)

valid_categories = [
    "Pothole / Road Damage",
    "Water Supply Disruption",
    "Solid Waste / Garbage",
    "Drainage Overflow / Flooding",
    "Street Light Failure",
    "Illegal Construction",
    "Encroachment",
    "Tree Fallen / Dangerous Tree",
    "Water Leakage / Pipe Burst",
    "Public Toilet Condition",
    "Noise / Air Pollution",
    "Stray Animal Menace",
    "Health / Epidemic",
]


def predict_priority(
    complaint_category,
    severity,
    ward_code,
    zone,
    ward_type,
    population_density,
    ward_slum_percentage,
    complaint_channel,
    complainant_type,
    property_type,
    is_monsoon_season,
    repeat_complainant,
    prior_complaints_count,
    has_photo_evidence=0,
    has_gps_location=0,
):
    if complaint_category not in valid_categories:
        raise ValueError(f"unknown complaint_category: {complaint_category}")
    if severity not in severity_order:
        raise ValueError(f"unknown severity: {severity}")

    row = {
        "complaint_category": complaint_category,
        "ward_code": ward_code,
        "zone": zone,
        "ward_type": ward_type,
        "population_density": population_density,
        "complaint_channel": complaint_channel,
        "complainant_type": complainant_type,
        "property_type": property_type,
        "severity": severity,
        "ward_slum_percentage": ward_slum_percentage,
        "prior_complaints_count": prior_complaints_count,
        "is_monsoon_season": is_monsoon_season,
        "repeat_complainant": repeat_complainant,
        "has_photo_evidence": has_photo_evidence,
        "has_gps_location": has_gps_location,
    }

    input_df = pd.DataFrame([row])[FEATURE_COLUMNS]
    prediction = pipeline.predict(input_df)[0]

    return max(0.0, min(100.0, float(prediction)))

if __name__ == "__main__":
    urgent = predict_priority(
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
    )

    minor = predict_priority(
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
    )

    print(f"urgent case (Health/Epidemic, Critical, high slum%, monsoon): {urgent:.1f}")
    print(f"minor case (Noise, Low, low slum%, non-monsoon): {minor:.1f}")
    assert urgent > minor, "urgent case should score higher than minor case!"
    print("sanity check passed - urgent scores higher than minor")