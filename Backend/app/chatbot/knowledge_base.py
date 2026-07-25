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


def build_knowledge_base():
    all_documents = []
    for filename in PDF_FILES:
        pdf_path = DATA_DIR / filename
        print(f"running ocr on {filename}, this can take a few minutes...")
        all_documents.extend(pdf_to_documents(pdf_path))

    print(f"got {len(all_documents)} pages of text total")

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


if __name__ == "__main__":
    build_knowledge_base()
