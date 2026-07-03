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
    location: str = Field(description="the place mentioned in the message, plain text, kept short")
    complaint_category: str = Field(description="must be copied exactly from the known category list, no changes to spelling or spacing")
    severity: str = Field(description="one of Low, Medium, High, Critical, default to Medium if the message gives no clue about urgency")


categories_text = "\n".join(f"- {c}" for c in CATEGORIES)

extraction_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You read a citizen's civic complaint message and pull out three things: location, "
     "complaint_category, and severity.\n\n"
     f"complaint_category must be copied exactly from this list, do not change spelling or spacing:\n{categories_text}\n\n"
     f"severity must be exactly one of {SEVERITY_LEVELS}. Default to Medium if the message "
     "gives no clue about urgency. Only use Critical or High when the message clearly signals "
     "danger or something urgent.\n\n"
     "Reply with only a JSON object in exactly this shape, nothing else, no explanation, "
     "no bullet points, no extra words before or after it:\n"
     '{{"location": "...", "complaint_category": "...", "severity": "..."}}'),
    ("human", "{user_query}"),
])