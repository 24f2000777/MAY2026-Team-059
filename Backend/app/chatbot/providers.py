import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from langchain_core.runnables import RunnableLambda
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from app.core.config import settings
from .prompts import extraction_prompt, ComplaintInfo

GROQ_API_KEY = settings.GROQ_API_KEY
GEMINI_API_KEY = settings.GEMINI_API_KEY
HUGGINGFACE_API_KEY = settings.HUGGINGFACE_API_KEY

SAFE_FALLBACK_REPLY = "Sorry, I'm having trouble with that right now. Please try again, or call the BMC helpline at 1916."

# The three provider clients accept their own timeout kwargs (request_timeout
# for groq, timeout for gemini/huggingface), set below, but at least one of
# them (confirmed: gemini, ChatGoogleGenerativeAI) doesn't actually honor it —
# a call still hung past 45s in testing with timeout=15 set. Rather than
# trust every provider library to correctly enforce its own timeout, every
# .invoke() in this module also runs through _invoke_with_timeout, a hard
# ceiling enforced from this side regardless of what the library underneath
# actually does with its own timeout parameter. This is what makes
# safe_chat_call's fallback chain (and SAFE_FALLBACK_REPLY) actually work as
# intended — none of that matters if the first provider in the chain can
# just hang forever and never hand control back.
LLM_REQUEST_TIMEOUT_SECONDS = 15

# extraction_chain (built below with .with_fallbacks()) tries up to 3
# providers *inside a single .invoke() call* — groq, then huggingface,
# then gemini, sequentially, only moving to the next on an exception.
# Wrapping that whole call in the same 15s budget meant for one
# provider was its own bug: a legitimate case where groq is a bit slow, the
# broken huggingface config fails fast (see hf_endpoint below), and gemini
# then succeeds could easily take longer than 15s total and get cut off
# before it had a real chance to finish, correctly, via a working fallback.
# This budget instead assumes the worst case is all three providers each
# taking close to LLM_REQUEST_TIMEOUT_SECONDS.
CHAIN_WITH_FALLBACKS_TIMEOUT_SECONDS = LLM_REQUEST_TIMEOUT_SECONDS * 3

_llm_call_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="llm-call")


def _invoke_with_timeout(llm, prompt, timeout=LLM_REQUEST_TIMEOUT_SECONDS):
    future = _llm_call_executor.submit(llm.invoke, prompt)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        raise TimeoutError(f"{llm.__class__.__name__} call did not return within {timeout}s")

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
    # llama-3.3-70b-versatile is decommissioned by Groq on 2026-08-16.
    # openai/gpt-oss-120b is the production-tier (not preview) replacement:
    # bigger than the old 70B, similar speed and rate limits. Groq's own
    # decommission notice also suggested qwen/qwen3.6-27b, but that model
    # is listed as Preview on Groq's model page, "should not be used in
    # production... may be discontinued at short notice" per Groq's own
    # docs, exactly the problem this swap is meant to avoid.
    model="openai/gpt-oss-120b",
    groq_api_key=GROQ_API_KEY,
    rate_limiter=groq_rate_limiter,
    max_retries=1,
    request_timeout=LLM_REQUEST_TIMEOUT_SECONDS,
    # Fact extraction, not conversation - the prompt already says "never
    # invent a location", but at the default ~0.7 temperature the model
    # still occasionally does anyway (confirmed: fabricated "near my
    # apartment in Andheri" out of a message that named no location at
    # all, which then also skipped the location follow-up question
    # entirely since a location was already "found"). temperature=0
    # makes the model consistently pick its single most likely output
    # instead of sampling, which is what a should-be-deterministic
    # extraction task like this needs.
    temperature=0,
).with_structured_output(ComplaintInfo)

groq_chat_llm = ChatGroq(
    # See groq_llm above for why this is gpt-oss-120b, not llama-3.3-70b-versatile.
    model="openai/gpt-oss-120b",
    groq_api_key=GROQ_API_KEY,
    rate_limiter=groq_rate_limiter,
    max_retries=1,
    request_timeout=LLM_REQUEST_TIMEOUT_SECONDS,
)

# A Groq small-model client (llama-3.1-8b-instant) was tried here for the
# graph's yes/no gating checks, to cut latency on the 70B round trips. Not
# kept: it got a real Mumbai location ("Linking Road, Bandra") wrong on
# jurisdiction, and misread "somewhere near my house" as not answering the
# location question — both reliably correct on the 70B model. Latency isn't
# worth trading away correctness on checks that decide whether a citizen's
# real complaint gets filed or silently dropped.

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
    timeout=LLM_REQUEST_TIMEOUT_SECONDS,
    # Same reasoning as groq_llm above - this is the extraction fallback,
    # not a conversational reply, it should be deterministic.
    temperature=0,
    # Root cause of the hang this whole fallback chain was built to avoid:
    # this client's default transport is gRPC, which silently does not
    # honor `timeout` — confirmed directly, a call sat for 45+s with
    # timeout=15 set. REST transport does honor it (confirmed: reliably
    # ~1.2-2s per call across repeated tries, timeout actually enforced).
    transport="rest",
).with_structured_output(ComplaintInfo)

# plain gemini, no structured output binding, used for intent classification and
# generating natural replies rather than pulling out complaint fields
gemini_chat_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    rate_limiter=gemini_rate_limiter,
    max_retries=1,
    timeout=LLM_REQUEST_TIMEOUT_SECONDS,
    transport="rest",
)

hf_endpoint = HuggingFaceEndpoint(
    # meta-llama/Meta-Llama-3-8B-Instruct is no longer supported by any
    # inference provider enabled on this token — confirmed, every call
    # failed instantly with a "model_not_supported" 400. Verified this
    # replacement is currently supported and fast (0.69s for a one-word
    # reply) against the same token.
    repo_id="meta-llama/Llama-3.1-8B-Instruct",
    huggingfacehub_api_token=HUGGINGFACE_API_KEY,
    timeout=LLM_REQUEST_TIMEOUT_SECONDS,
)
huggingface_llm = ChatHuggingFace(llm=hf_endpoint)


def safe_chat_call(prompt, default_reply=SAFE_FALLBACK_REPLY):
    """
    The accurate path: every reply a citizen actually reads (question
    answers, chitchat) and intent classification go through this, on the
    70B model. Tries groq first, since its free tier is far more generous
    than gemini or huggingface, falls back to huggingface, then gemini, and
    if genuinely everything fails, returns a fixed safe reply instead of
    raising and crashing the conversation. Every call goes through
    _invoke_with_timeout rather than calling .invoke() directly, so a
    provider that's just hanging (confirmed: gemini can do this even with
    its own timeout kwarg set) still fails within LLM_REQUEST_TIMEOUT_SECONDS
    and falls through to the next provider, instead of stalling the whole
    reply indefinitely.
    """
    try:
        return _invoke_with_timeout(groq_chat_llm, prompt).content
    except Exception as e:
        print(f"groq chat call failed, falling back to huggingface: {e}")

    try:
        return _invoke_with_timeout(huggingface_llm, prompt).content
    except Exception as e:
        print(f"huggingface chat call failed, falling back to gemini: {e}")

    try:
        return _invoke_with_timeout(gemini_chat_llm, prompt).content
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