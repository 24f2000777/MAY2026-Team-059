"""
Bridges a real Complaint row to the priority_scorer ML model.

predict_priority() (app/ml/priority_scorer/predict.py) expects fields that
don't exist anywhere on the Complaint model yet: severity, ward-level
demographics, complaint channel, complainant/property type. This module
fills in what it genuinely can from the database and today's date, asks
an LLM for severity (the model's dominant feature, so it can't be
defaulted to a constant), and falls back to safe placeholders for the
rest until a real wards table and those extra fields exist.
"""

import logging
from datetime import date

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select

from app.chatbot.extractor import extract_complaint_info
from app.ml.priority_scorer.predict import ComplaintFeatures, predict_priority
from app.model import Complaint, ComplaintImage

logger = logging.getLogger(__name__)

# Our ComplaintCategory enum (schemas/complaint.py) uses a different, smaller
# taxonomy than the 13 categories the model was trained on
# (formula.py's VALID_CATEGORIES). Mapped to the closest match; category is
# only a "distant second" factor behind severity per the model's feature
# importance, so an imperfect mapping here doesn't skew scores much.
CATEGORY_MAP = {
    "road": "Pothole / Road Damage",
    "pothole": "Pothole / Road Damage",
    "streetlight": "Street Light Failure",
    "drainage": "Drainage Overflow / Flooding",
    "garbage": "Solid Waste / Garbage",
    "water_supply": "Water Supply Disruption",
    "sewage": "Drainage Overflow / Flooding",
    "traffic": "Pothole / Road Damage",  # closest roads-related bucket, no direct match
    "electricity": "Street Light Failure",  # closest infra-electrical bucket, no direct match
    "other": "Noise / Air Pollution",  # lowest-impact bucket, used as a neutral catch-all
}

# Mumbai's monsoon months, per IMD/BMC convention.
MONSOON_MONTHS = (6, 7, 8, 9)

# Placeholders for fields that need a real wards reference table (ward_code,
# zone, ward_type, population_density, ward_slum_percentage) or additional
# complaint-submission fields (complaint_channel, complainant_type,
# property_type) that don't exist yet. The model was trained with
# handle_unknown="ignore" on these, so an unrecognized value just contributes
# nothing rather than erroring, and per the training README these fields have
# near-zero feature importance compared to severity and category.
UNKNOWN_WARD_FIELDS = {
    "ward_code": "Unknown",
    "zone": "Unknown",
    "ward_type": "Unknown",
    "population_density": "Unknown",
    "ward_slum_percentage": 0,
    "complaint_channel": "MyBMC App",
    "complainant_type": "Resident",
    "property_type": "Unknown",
}


async def _get_severity(complaint: Complaint) -> str:
    """
    Asks the LLM extraction chain (built for the chatbot, reused here) to
    read the complaint's own description and judge severity. Falls back to
    Medium, the same default the extraction prompt itself uses when a
    message gives no clue about urgency, if every provider fails.
    """
    try:
        # extract_complaint_info is a blocking network call (LLM API), run it
        # in a thread so it doesn't stall the event loop for other requests
        extracted = await run_in_threadpool(extract_complaint_info, complaint.description)
        return extracted["severity"]
    except Exception:
        logger.warning(
            "severity extraction failed for complaint %s, defaulting to Medium",
            complaint.id,
            exc_info=True,
        )
        return "Medium"


async def score_complaint(complaint: Complaint, db) -> float:
    """
    Computes a priority_score for the given complaint. Does not save it,
    callers are responsible for persisting the result.
    """
    severity = await _get_severity(complaint)

    prior_count_result = await db.execute(
        select(func.count(Complaint.id)).where(
            Complaint.citizen_id == complaint.citizen_id,
            Complaint.id != complaint.id,
        )
    )
    prior_complaints_count = prior_count_result.scalar_one()

    photo_count_result = await db.execute(
        select(func.count(ComplaintImage.id)).where(
            ComplaintImage.complaint_id == complaint.id
        )
    )
    has_photo_evidence = 1 if photo_count_result.scalar_one() > 0 else 0

    return predict_priority(ComplaintFeatures(
        complaint_category=CATEGORY_MAP.get(complaint.category, "Noise / Air Pollution"),
        severity=severity,
        is_monsoon_season=1 if date.today().month in MONSOON_MONTHS else 0,
        repeat_complainant=1 if prior_complaints_count > 0 else 0,
        prior_complaints_count=prior_complaints_count,
        has_photo_evidence=has_photo_evidence,
        has_gps_location=0,  # no latitude/longitude column on Complaint yet
        **UNKNOWN_WARD_FIELDS,
    ))


async def rescore_all_complaints(db) -> int:
    """
    Recomputes and saves priority_score for every complaint. Shared by the
    POST /ml/rescore-all endpoint and the nightly Celery Beat job, so both
    call one place instead of keeping the same loop in two files.
    """
    result = await db.execute(select(Complaint))
    complaints = result.scalars().all()

    for complaint in complaints:
        complaint.priority_score = round(await score_complaint(complaint, db))

    await db.commit()
    return len(complaints)
