# MAY2026-Team-059

## Chatbot knowledge base: system dependencies

`Backend/app/chatbot/knowledge_base.py` rebuilds the chatbot's FAISS index from
the source PDFs (`python knowledge_base.py`, run from `Backend/app/chatbot/`).
That rebuild step OCRs each page with `pdf2image` + `pytesseract`, which need
the following installed as OS packages, not just `pip install`-able:

- `poppler-utils` (for `pdf2image`)
- `tesseract-ocr` (for `pytesseract`)

The running app itself never calls this rebuild step: the generated index
(`Backend/app/chatbot/faiss_index/`) is committed to the repo and loaded
directly via `load_knowledge_base()`, which only needs the Python packages
already in `requirements.txt`. These system packages are only needed if
you're regenerating the index from the source PDFs.