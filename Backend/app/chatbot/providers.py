import os
import json
import re

from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from prompts import extraction_prompt, ComplaintInfo

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

SAFE_FALLBACK_REPLY = "Sorry, I'm having trouble with that right now. Please try again, or call the BMC helpline at 1916."

# groq's free tier allows 30 requests a minute and well over a thousand a day,
# far more generous than gemini or huggingface right now, so it's the primary
# provider, still throttle a little as a courtesy and to fail fast if it ever
# does hit a limit
groq_rate_limiter = InMemoryRateLimiter(
    requests_per_second=20 / 60,  # comfortably under the 30/minute cap
    check_every_n_seconds=0.5,
    max_bucket_size=1,
)

groq_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY,
    rate_limiter=groq_rate_limiter,
    max_retries=1,
).with_structured_output(ComplaintInfo)

groq_chat_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=GROQ_API_KEY,
    rate_limiter=groq_rate_limiter,
    max_retries=1,
)

# gemini's free tier only allows 5 requests per minute, so throttle our own calls
# to stay comfortably under that instead of hitting a 429 during a demo
gemini_rate_limiter = InMemoryRateLimiter(
    requests_per_second=5 / 70,  # a little under 5 per minute, some safety margin
    check_every_n_seconds=0.5,
    max_bucket_size=1,
)

gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    rate_limiter=gemini_rate_limiter,
    max_retries=1,  # fail fast instead of retrying for over a minute
).with_structured_output(ComplaintInfo)

# plain gemini, no structured output binding, used for intent classification and
# generating natural replies rather than pulling out complaint fields
gemini_chat_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    rate_limiter=gemini_rate_limiter,
    max_retries=1,
)

hf_endpoint = HuggingFaceEndpoint(
    repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
    huggingfacehub_api_token=HUGGINGFACE_API_KEY,
)
huggingface_llm = ChatHuggingFace(llm=hf_endpoint)


def safe_chat_call(prompt, default_reply=SAFE_FALLBACK_REPLY):
    """
    One call function every part of the graph uses for plain text replies
    (classification, cleanup, question answering, chitchat). Tries groq first,
    since its free tier is far more generous than gemini or huggingface, falls
    back to huggingface, then gemini, and if genuinely everything fails,
    returns a fixed safe reply instead of raising and crashing the conversation.
    """
    try:
        return groq_chat_llm.invoke(prompt).content
    except Exception as e:
        print(f"groq chat call failed, falling back to huggingface: {e}")

    try:
        return huggingface_llm.invoke(prompt).content
    except Exception as e:
        print(f"huggingface chat call failed, falling back to gemini: {e}")

    try:
        return gemini_chat_llm.invoke(prompt).content
    except Exception as e:
        print(f"gemini chat call also failed: {e}")

    return default_reply


def parse_huggingface_output(ai_message):
    # ChatHuggingFace does not support with_structured_output, langchain never
    # implemented bind_tools for this integration, so we pull the json out of the
    # raw text ourselves instead of relying on that method
    text = ai_message.content

    def clean_field(raw_value):
        value = raw_value.split("(")[0].strip().rstrip(".,")
        if value.lower() in ("null", "none", ""):
            return None
        return value

    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(0))
        data.setdefault("location", None)
        data.setdefault("complaint_category", None)
        if isinstance(data.get("location"), str):
            data["location"] = clean_field(data["location"])
        if isinstance(data.get("complaint_category"), str):
            data["complaint_category"] = clean_field(data["complaint_category"])
        return ComplaintInfo(**data)

    # smaller models sometimes ignore the json instruction and write a plain
    # bulleted answer instead, like "* Location: Sector 5, Dharavi", so fall back
    # to pulling the fields out of labeled lines instead of giving up. location
    # and complaint_category are both allowed to be missing, severity is not
    location = re.search(r"location[:\-]\s*(.+)", text, re.IGNORECASE)
    category = re.search(r"category[:\-]\s*(.+)", text, re.IGNORECASE)
    severity = re.search(r"severity[:\-]\s*(.+)", text, re.IGNORECASE)

    if not severity:
        raise ValueError(f"could not find severity in the huggingface response: {text}")

    return ComplaintInfo(
        location=clean_field(location.group(1)) if location else None,
        complaint_category=clean_field(category.group(1)) if category else None,
        severity=clean_field(severity.group(1)),
    )


# try groq first, its free tier is far more generous than either huggingface or
# gemini, huggingface and gemini are backups for whenever groq itself has an issue
extraction_chain = (extraction_prompt | groq_llm).with_fallbacks(
    [
        extraction_prompt | huggingface_llm | RunnableLambda(parse_huggingface_output),
        extraction_prompt | gemini_llm,
    ]
)