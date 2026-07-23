"""
Predicts a complaint's category from free text (#66-68), using the same
LLM extraction chain built for the chatbot (extract_complaint_info),
reused here the same way priority_service.py reuses it for severity,
rather than training a separate text classification model.
"""

import logging

from fastapi.concurrency import run_in_threadpool

from app.chatbot.extractor import extract_complaint_info

logger = logging.getLogger(__name__)

# extract_complaint_info returns one of the BMC 13-category taxonomy
# values (or None, if the LLM decided the text isn't a genuine complaint
# at all). Mapped back to our own 10-value ComplaintCategory enum.
# Several BMC categories have no direct match in our smaller enum and
# fall back to "other".
BMC_TO_OUR_CATEGORY = {
    "Pothole / Road Damage": "pothole",
    "Water Supply Disruption": "water_supply",
    "Solid Waste / Garbage": "garbage",
    "Drainage Overflow / Flooding": "drainage",
    "Street Light Failure": "streetlight",
    "Water Leakage / Pipe Burst": "water_supply",
    "Illegal Construction": "other",
    "Encroachment": "other",
    "Tree Fallen / Dangerous Tree": "other",
    "Public Toilet Condition": "other",
    "Noise / Air Pollution": "other",
    "Stray Animal Menace": "other",
    "Health / Epidemic": "other",
}


async def predict_category(text: str) -> str:
    """
    Reads free text (a complaint's title + description) and returns one
    of our own ComplaintCategory values. Falls back to "other" if the
    LLM call fails entirely or decides the text isn't a genuine complaint.
    """
    try:
        # extract_complaint_info is a blocking network call (LLM API), run
        # it in a thread so it doesn't stall the event loop for other requests
        extracted = await run_in_threadpool(extract_complaint_info, text)
    except Exception:
        logger.warning("category extraction failed, defaulting to 'other'", exc_info=True)
        return "other"

    bmc_category = extracted["complaint_category"]
    if bmc_category is None:
        return "other"

    return BMC_TO_OUR_CATEGORY.get(bmc_category, "other")
