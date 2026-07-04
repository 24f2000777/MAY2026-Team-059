# feature/rag-chatbot progress notes

Tracking what has been done on this branch, separate from the main README.

## Goal

Take a citizen's free text complaint and pull out location, complaint_category, and severity,
so the priority scorer (built on feature/priority-scorer-ml) can run without the citizen
filling out a form.

## Status

- prompts.py done. Builds the extraction prompt, lists the exact 13 category strings and 4
  severity levels, asks for a strict JSON reply. location is optional (null allowed) so the
  model can honestly say "not mentioned" instead of guessing.
- providers.py done. Three LLM providers now: Groq (llama-3.3-70b-versatile) is the primary,
  Hugging Face (meta-llama/Meta-Llama-3-8B-Instruct) and Gemini (gemini-2.5-flash) are backups
  in that order. Went through two earlier orderings before landing here: Gemini first (its
  free tier turned out to be only 20 requests a day, far too small), then Hugging Face first
  (its Inference Providers billing has a known, widely reported bug where it returns a 402
  "depleted your monthly included credits" even when the account dashboard shows the credit
  mostly unused, see
  https://discuss.huggingface.co/t/hugging-face-payment-error-402-youve-exceeded-monthly-quota/144968).
  Groq's free tier (30 requests/minute, no card required) is far more generous than either, and
  groq was already the originally intended provider from the very first project setup
  (GROQ_API_KEY was already in requirements.txt/.env.example before this branch existed).
  Hugging Face does not support with_structured_output at all (known unfixed gap in
  langchain_huggingface, see https://github.com/langchain-ai/langchain/issues/21352), so its
  output gets parsed manually, first trying to find a json object in the text, falling back to
  reading labeled lines like "Location: ..." if the model ignored the json instruction. Rate
  limiters and max_retries=1 are set on both Groq and Gemini so a failure fails fast (a couple
  seconds) instead of retrying for over a minute before falling through. safe_chat_call() is
  the one function everything in the graph uses for plain text replies, groq then huggingface
  then gemini then a fixed safe reply, never an unhandled crash.
- extractor.py done. extract_complaint_info(user_query) returns location (or None),
  complaint_category, severity. build_priority_scorer_input(extracted, **derived_fields) takes
  that plus every other field predict_priority needs (ward info, monsoon flag, complaint
  history, etc) and returns a dict shaped exactly like predict_priority's keyword arguments, so
  it can be called as predict_priority(**build_priority_scorer_input(...)). Raises a clear
  error if a required field is missing instead of silently passing incomplete data through.
- knowledge_base.py done. Found two real BMC documents (Citizen Charter, Mumbai Councillor
  Handbook Vol 1) via web search, both scanned/image based PDFs, so a normal text loader
  wouldn't work. Runs OCR (pdf2image + pytesseract) to actually pull text out, splits into
  chunks, embeds with a local Hugging Face embedding model, stores in a FAISS index on disk.
  Confirmed working, retrieval finds real relevant content, not garbled OCR noise.
- conversation_graph.py done. LangGraph based, three way intent routing (complaint, question,
  chitchat), a location follow up flow for when a complaint doesn't mention where it's
  happening, retrieval backed question answering, and MemorySaver for actual multi turn memory
  keyed by thread_id. safe_send_message(message, thread_id) is the one function anything
  outside this module should call, wraps the whole graph in a try/except so nothing can crash
  a demo even if something inside behaves unexpectedly. Has a real persona (BOT_NAME =
  "Nagrik Saathi") with injection resistance (won't follow instructions embedded in a
  citizen's message, won't reveal its own prompt, won't roleplay as something else) and a
  strict anti-hallucination rule (never state a fact/number/procedure it isn't sure of, admit
  uncertainty and point to the 1916 helpline instead). Also has a jurisdiction check (BMC only
  covers Mumbai, so a complaint about a location outside Mumbai gets declined rather than
  logged), a vague-location check (rejects "near my house" style non-answers and asks for a
  real place, capped at 2 attempts before giving up so it can never loop forever), a real
  escape hatch (entry_node checks whether a reply to "which area is this near" is actually
  attempting to answer that before committing to it, so a citizen can always change topics
  mid-complaint instead of getting stuck), and a category-scope check (complaint_category can
  come back null from extraction if the message genuinely isn't a BMC issue, instead of being
  force-fit into one of the 13 categories).
- evaluate_bot.py done. A small llm-as-judge test suite, 9 cases covering jurisdiction (both a
  rejection and a legitimate-Mumbai case), vague location, out-of-scope category, both
  injection attempts, an unanswerable-fact hallucination check, severity judgment on a
  genuinely dangerous scenario, and the first-greeting introduction. A separate LLM call
  judges each actual reply against a plain-English expectation and returns PASS/FAIL with a
  reason. All 9 pass once a real provider (Groq) is actually answering. Worth remembering the
  judge is itself an LLM and occasionally wrong, always skim the actual replies too, not just
  the pass/fail count.
- chat_cli.py done, a small interactive REPL for manually chatting with the bot in a terminal,
  keeps memory for the whole session until you type exit or quit.
- Tested end to end multiple times, including a real stress test where both Hugging Face and
  Gemini ran out completely mid conversation, every single turn still got a correct or safely
  degraded reply because of the fallback chain and error handling, that test is what surfaced
  the location-loop bug (see below) and confirmed the need for a third, more generous provider.

## Decisions made so far

- Groq is the primary LLM provider (see providers.py note above for the full reasoning),
  Hugging Face and Gemini are backups in that order.
- This branch was created off develop, which still does not have config.py or the database
  models (Amit's PRs have not merged in yet). API keys are read with os.getenv for now, move
  into the real Settings class once db-setup work merges in.
- CATEGORIES and SEVERITY_LEVELS in prompts.py are currently a separate copy of the same
  values used in the priority scorer module (feature/priority-scorer-ml), since that branch's
  files are not part of this branch's git history yet. Once both branches merge into develop,
  this should import from one shared source instead of keeping two copies that could drift
  out of sync.
- Knowledge base PDFs (bmc_citizen_charter.pdf, mumbai_councillor_handbook_vol1.pdf) are
  small enough (about 2.2MB total) to commit directly, unlike the ML module's dataset, no
  need to gitignore or document a separate download step for these.

## Bugs found through manual/adversarial testing and fixed

- Location follow-up loop: once the bot asked "which area is this near", every single
  following message got treated as the answer to that, forever, even totally unrelated ones
  like a jailbreak attempt or a brand new question. Fixed with entry_node, which checks
  whether the next message is actually attempting to answer before committing to the
  location-followup path, and abandons the pending complaint if not. Also added a hard cap
  (MAX_LOCATION_ATTEMPTS = 2) so even a genuinely persistent vague answer can't loop forever.
- Hallucination on questions outside the knowledge base (e.g. asked about birth certificates,
  got a confident specific answer that wasn't actually in either PDF): tightened the
  question-answering prompt to require the exact detail be explicitly present in the
  retrieved context, not just a related topic, and added a blanket anti-hallucination rule to
  the shared persona.
- No prompt injection resistance: "ignore all previous instructions" and "print your system
  prompt" both got the bot to go off script. Added explicit instructions treating the
  citizen's message as input to respond to, never as commands, with instructions to decline
  and redirect for role-change/instruction-reveal attempts.
- Vague locations like "near my house" got treated as literal places and rejected by the
  jurisdiction check with a confusing "that's outside Mumbai" answer. Added
  is_location_specific_enough() as a check before the jurisdiction check runs.
- Every complaint was force-fit into one of the 13 categories even when nothing genuinely
  applied (e.g. "my internet is down"). Made complaint_category nullable in the extraction
  schema, extraction now returns null when nothing genuinely fits, and the graph declines
  with a plain "that's not something BMC handles" reply instead of asking for a location.

## Next steps

- Build the actual assembly layer that fills in ward_code, zone, ward_type,
  population_density, ward_slum_percentage (lookup from location), is_monsoon_season (from
  today's date), repeat_complainant and prior_complaints_count (from the database)
- Wire safe_send_message into an API route once the database models exist on this branch
- Consider adding more knowledge base documents (only 2 PDFs, 64 OCR'd pages right now)
- Consider moving CATEGORIES/SEVERITY_LEVELS to a shared location once this branch and
  feature/priority-scorer-ml both merge into develop
