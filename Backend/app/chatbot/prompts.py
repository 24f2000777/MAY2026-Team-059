from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

CATEGORIES = [
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

SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]


class ComplaintInfo(BaseModel):
    location: Optional[str] = Field(default=None, description="the place mentioned in the message, plain text, kept short. set to null if the message does not mention any location at all")
    complaint_category: Optional[str] = Field(default=None, description="must be copied exactly from the known category list, no changes to spelling or spacing. set to null if the message is not actually a Mumbai civic/BMC infrastructure issue, or doesn't genuinely match any category")
    severity: str = Field(description="one of Low, Medium, High, Critical, default to Medium if the message gives no clue about urgency")


categories_text = "\n".join(f"- {c}" for c in CATEGORIES)

extraction_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You read a citizen's message and decide if it's a genuine Mumbai civic complaint "
     "that BMC (Brihanmumbai Municipal Corporation) would handle, and if so, pull out "
     "three things: location, complaint_category, and severity.\n\n"
     f"complaint_category must be copied exactly from this list, do not change spelling or spacing:\n{categories_text}\n\n"
     "If the message is not actually about a Mumbai civic/BMC infrastructure or public "
     "service issue (for example: personal problems, private companies, internet or "
     "phone service, requests unrelated to any of the categories above, or anything that "
     "doesn't genuinely fit even loosely), set complaint_category to null. Do not force "
     "a match into the closest sounding category just because something needs to be "
     "picked, only pick a category when it genuinely fits.\n\n"
     f"severity must be exactly one of {SEVERITY_LEVELS}. Default to Medium if the message "
     "gives no clue about urgency. Only use Critical or High when the message clearly signals "
     "danger or something urgent.\n\n"
     "If the message does not mention any location at all, set location to null, do not "
     "guess or invent one.\n\n"
     "Reply with only a JSON object in exactly this shape, nothing else, no explanation, "
     "no bullet points, no extra words before or after it:\n"
     '{{"location": "..." or null, "complaint_category": "..." or null, "severity": "..."}}'),
    ("human", "{user_query}"),
])