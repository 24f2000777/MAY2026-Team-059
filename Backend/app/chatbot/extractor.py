from app.utils.constants import DEPARTMENT_NAMES

from .prompts import CATEGORIES, SEVERITY_LEVELS
from .providers import (
    CHAIN_WITH_FALLBACKS_TIMEOUT_SECONDS,
    _invoke_with_timeout,
    extraction_chain,
    routing_chain,
)


def _location_is_grounded(location, user_query):
    """
    Rejects a location the model claims to have found if none of its
    words actually appear anywhere in the message it supposedly came
    from — a cheap, deterministic check that catches the exact failure
    mode temperature=0 on the extraction LLM (see providers.py) reduces
    but can't fully rule out: a plausible-sounding place name invented
    for a message that never mentioned one at all.
    """
    query_words = set(user_query.lower().split())
    location_words = [w.strip(".,!?()") for w in location.lower().split()]
    return any(len(w) >= 3 and w in query_words for w in location_words)


def extract_complaint_info(user_query):
    # extraction_chain has its own provider fallbacks built in (see
    # providers.py) — up to 3 sequential provider attempts inside this one
    # .invoke() call, only exceptions trigger the next one, a provider that
    # just hangs would never hand control to the next. _invoke_with_timeout
    # enforces a hard ceiling from this side regardless of what the chain's
    # own fallback logic does, sized for 3 provider attempts
    # (CHAIN_WITH_FALLBACKS_TIMEOUT_SECONDS), not a single one.
    result = _invoke_with_timeout(
        extraction_chain, {"user_query": user_query}, timeout=CHAIN_WITH_FALLBACKS_TIMEOUT_SECONDS
    )

    # category being None is a valid, expected result, it means the llm decided
    # this isn't actually a BMC civic complaint, not a parsing failure
    category = result.complaint_category.strip() if result.complaint_category else None
    severity = result.severity.strip()
    location = result.location.strip() if result.location else None
    if location and not _location_is_grounded(location, user_query):
        location = None

    if category is not None and category not in CATEGORIES:
        raise ValueError(f"llm returned an invalid category: {category}")
    if severity not in SEVERITY_LEVELS:
        raise ValueError(f"llm returned an invalid severity: {severity}")

    return {
        "location": location,
        "complaint_category": category,
        "severity": severity,
    }


def predict_department(category, description):
    """
    Asks the LLM to pick exactly one department (app/utils/constants.
    DEPARTMENT_NAMES) for a complaint's category and description. The
    Literal-typed DepartmentRouting schema means Groq/Gemini can only
    ever return one of those exact names, never something invented.
    """
    result = _invoke_with_timeout(
        routing_chain,
        {"category": category, "description": description},
        timeout=CHAIN_WITH_FALLBACKS_TIMEOUT_SECONDS,
    )
    department = result.department.strip()

    if department not in DEPARTMENT_NAMES:
        raise ValueError(f"llm returned an unknown department: {department}")

    return department


# every field predict_priority needs, besides complaint_category and severity which
# come straight from extract_complaint_info above
REQUIRED_FIELDS_FROM_ELSEWHERE = [
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