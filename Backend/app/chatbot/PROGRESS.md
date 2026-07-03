# feature/rag-chatbot progress notes

Tracking what has been done on this branch, separate from the main README.

## Goal

Take a citizen's free text complaint and pull out location, complaint_category, and severity,
so the priority scorer (built on feature/priority-scorer-ml) can run without the citizen
filling out a form.

## Status

- prompts.py done. Builds the extraction prompt, lists the exact 13 category strings and 4
  severity levels, asks for a strict JSON reply.
- providers.py done. Tries Gemini first (gemini-2.5-flash, uses with_structured_output since
  Gemini supports real function calling), falls back to Hugging Face
  (meta-llama/Meta-Llama-3-8B-Instruct) if Gemini fails. Hugging Face does not support
  with_structured_output at all (known unfixed gap in langchain_huggingface, see
  https://github.com/langchain-ai/langchain/issues/21352), so its output gets parsed manually,
  first trying to find a json object in the text, falling back to reading labeled lines like
  "Location: ..." if the model ignored the json instruction and wrote a plain answer instead.
- extractor.py done. extract_complaint_info(user_query) returns location, complaint_category,
  severity. build_priority_scorer_input(extracted, **derived_fields) takes that plus every
  other field predict_priority needs (ward info, monsoon flag, complaint history, etc) and
  returns a dict shaped exactly like predict_priority's keyword arguments, so it can be called
  as predict_priority(**build_priority_scorer_input(...)). Raises a clear error if a required
  field is missing instead of silently passing incomplete data through.
- Tested end to end with a real message ("huge pothole ... scooter fell in it"), both the
  Gemini path and the Hugging Face fallback path confirmed working.

## Decisions made so far

- Use both Gemini and Hugging Face as LLM providers, with fallback from one to the other,
  since Hugging Face's free tier credit is very small on its own.
- This branch was created off develop, which still does not have config.py or the database
  models (Amit's PRs have not merged in yet). API keys are read with os.getenv for now, move
  into the real Settings class once db-setup work merges in.
- CATEGORIES and SEVERITY_LEVELS in prompts.py are currently a separate copy of the same
  values used in the priority scorer module (feature/priority-scorer-ml), since that branch's
  files are not part of this branch's git history yet. Once both branches merge into develop,
  this should import from one shared source instead of keeping two copies that could drift
  out of sync.

## Next steps

- Build the actual assembly layer that fills in ward_code, zone, ward_type,
  population_density, ward_slum_percentage (lookup from location), is_monsoon_season (from
  today's date), repeat_complainant and prior_complaints_count (from the database)
- Wire this into an API route once the database models exist on this branch
- Eventually the retrieval/Q&A half of the RAG chatbot (answering questions using retrieved
  documents), which is a LangGraph shaped problem rather than a single chain, since it needs
  branching and multi turn memory
