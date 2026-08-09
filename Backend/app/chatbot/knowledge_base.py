import threading
from pathlib import Path

from pdf2image import convert_from_path
import pytesseract

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DATA_DIR = Path(__file__).parent / "data"
INDEX_DIR = Path(__file__).parent / "faiss_index"

PDF_FILES = [
    "bmc_citizen_charter.pdf",
    "mumbai_councillor_handbook_vol1.pdf",
]


def pdf_to_documents(pdf_path):
    # these two pdfs are scanned images, not real text, so a normal pdf text
    # loader would come back empty. convert each page to an image first, then
    # run ocr on it to actually pull text out
    pages = convert_from_path(pdf_path)

    documents = []
    for page_number, page_image in enumerate(pages, start=1):
        text = pytesseract.image_to_string(page_image)
        if text.strip():
            documents.append(
                Document(
                    page_content=text,
                    metadata={"source": pdf_path.name, "page": page_number},
                )
            )
    return documents


# OCR-ing the static PDFs takes a few minutes, so it only happens once
# per process, not on every rebuild. Admin-added KB documents are cheap
# text and don't need caching, they're re-read from the DB each rebuild.
_static_documents_cache: list[Document] | None = None
_static_documents_lock = threading.Lock()


def _get_static_documents() -> list[Document]:
    global _static_documents_cache
    if _static_documents_cache is None:
        with _static_documents_lock:
            if _static_documents_cache is None:
                all_documents = []
                for filename in PDF_FILES:
                    pdf_path = DATA_DIR / filename
                    print(f"running ocr on {filename}, this can take a few minutes...")
                    all_documents.extend(pdf_to_documents(pdf_path))
                print(f"got {len(all_documents)} pages of text total")
                _static_documents_cache = all_documents
    return _static_documents_cache


def admin_document_to_langchain_document(kb_document) -> Document:
    """
    Converts a KnowledgeBaseDocument row into the same Document shape
    the PDF pipeline produces, so it can be chunked and embedded
    alongside the static pages. kb_document_id in metadata is what
    lets a search hit be traced back to the admin-added row it came
    from, if that's ever needed.
    """
    return Document(
        page_content=f"{kb_document.title}\n\n{kb_document.content}",
        metadata={"source": f"admin:{kb_document.title}", "kb_document_id": str(kb_document.id)},
    )


def build_knowledge_base(extra_documents: list[Document] | None = None):
    """
    Builds and persists the FAISS index from the static PDFs plus
    whatever extra_documents are passed in (admin-added KB rows).
    Static PDFs are OCR'd at most once per process (see
    _get_static_documents), so calling this repeatedly to pick up new
    admin documents is cheap after the first call.
    """
    all_documents = list(_get_static_documents()) + list(extra_documents or [])

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(all_documents)
    print(f"split into {len(chunks)} chunks")

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(str(INDEX_DIR))
    print(f"saved faiss index to {INDEX_DIR}")

    return vector_store


def load_knowledge_base():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return FAISS.load_local(str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True)


class KnowledgeBaseIndex:
    """
    Holds the live FAISS store as a swappable attribute, so
    POST /chat/rebuild-index can update it in place, and every caller
    that reads .store afterward (handle_question in
    conversation_graph.py) sees the new one without a server restart.
    """

    def __init__(self):
        self.store = load_knowledge_base()

    def rebuild(self, extra_documents: list[Document] | None = None) -> None:
        self.store = build_knowledge_base(extra_documents)


knowledge_base_index = KnowledgeBaseIndex()


if __name__ == "__main__":
    build_knowledge_base()
