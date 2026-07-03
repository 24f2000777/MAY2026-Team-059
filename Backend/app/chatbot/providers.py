import os
import json
import re

from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from prompts import extraction_prompt, ComplaintInfo

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
).with_structured_output(ComplaintInfo)

hf_endpoint = HuggingFaceEndpoint(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
    huggingfacehub_api_token=HUGGINGFACE_API_KEY,
)
huggingface_llm = ChatHuggingFace(llm=hf_endpoint)


def parse_huggingface_output(ai_message):
    # ChatHuggingFace does not support with_structured_output, langchain never
    # implemented bind_tools for this integration, so we pull the json out of the
    # raw text ourselves instead of relying on that method
    text = ai_message.content

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(0))
        return ComplaintInfo(**data)

    # smaller models sometimes ignore the json instruction and write a plain
    # bulleted answer instead, like "* Location: Sector 5, Dharavi", so fall back
    # to pulling the three fields out of labeled lines instead of giving up
    location = re.search(r"location[:\-]\s*(.+)", text, re.IGNORECASE)
    category = re.search(r"category[:\-]\s*(.+)", text, re.IGNORECASE)
    severity = re.search(r"severity[:\-]\s*(.+)", text, re.IGNORECASE)

    if not (location and category and severity):
        raise ValueError(f"could not find location, category, and severity in the huggingface response: {text}")

    return ComplaintInfo(
        location=location.group(1).split("(")[0].strip().rstrip(".,"),
        complaint_category=category.group(1).split("(")[0].strip().rstrip(".,"),
        severity=severity.group(1).split("(")[0].strip().rstrip(".,"),
    )


# try gemini first since its free tier is more generous, huggingface is the backup
extraction_chain = (extraction_prompt | gemini_llm).with_fallbacks(
    [extraction_prompt | huggingface_llm | RunnableLambda(parse_huggingface_output)]
)