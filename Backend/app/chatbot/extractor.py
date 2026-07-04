from prompts import CATEGORIES, SEVERITY_LEVELS
from providers import extraction_chain


def extract_complaint_info(user_query):
    result = extraction_chain.invoke({"user_query": user_query})

    # category being None is a valid, expected result, it means the llm decided
    # this isn't actually a BMC civic complaint, not a parsing failure
    category = result.complaint_category.strip() if result.complaint_category else None
    severity = result.severity.strip()
    location = result.location.strip() if result.location else None

    if category is not None and category not in CATEGORIES:
        raise ValueError(f"llm returned an invalid category: {category}")
    if severity not in SEVERITY_LEVELS:
        raise ValueError(f"llm returned an invalid severity: {severity}")

    return {
        "location": location,
        "complaint_category": category,
        "severity": severity,
    }


# every field predict_priority needs, besides complaint_category and severity which
# come straight from extract_complaint_info above
REQUIRED_FIELDS_FROM_ELSEWHERE = [
    "ward_code",
    "zone",
    "ward_type",
    "population_density",
    "ward_slum_percentage",
    "complaint_channel",
    "complainant_type",
    "property_type",
    "is_monsoon_season",
    "repeat_complainant",
    "prior_complaints_count",
]

OPTIONAL_FIELDS_FROM_ELSEWHERE = [
    "has_photo_evidence",
    "has_gps_location",
]


def build_priority_scorer_input(extracted, **derived_fields):
    """
    Takes the dict from extract_complaint_info and the fields that get looked up
    elsewhere (ward lookup from location, monsoon check from today's date, complaint
    history from the database), and returns a dict shaped exactly like the keyword
    arguments predict_priority expects. Can be called directly as
    predict_priority(**build_priority_scorer_input(extracted, **derived_fields)).

    Raises a clear error instead of silently passing incomplete data to the model if
    something required is still missing.
    """

    missing = [field for field in REQUIRED_FIELDS_FROM_ELSEWHERE if field not in derived_fields]
    if missing:
        raise ValueError(f"missing fields needed for the priority scorer: {missing}")

    result = {
        "complaint_category": extracted["complaint_category"],
        "severity": extracted["severity"],
    }

    for field in REQUIRED_FIELDS_FROM_ELSEWHERE:
        result[field] = derived_fields[field]

    for field in OPTIONAL_FIELDS_FROM_ELSEWHERE:
        result[field] = derived_fields.get(field, 0)

    return result