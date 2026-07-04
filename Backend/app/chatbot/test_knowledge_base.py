from knowledge_base import load_knowledge_base

if __name__ == "__main__":
    vector_store = load_knowledge_base()

    query = "how do I file a complaint with BMC and what is the helpline number"
    results = vector_store.similarity_search(query, k=3)

    for i, doc in enumerate(results, start=1):
        print(f"\n--- result {i} (source: {doc.metadata['source']}, page {doc.metadata['page']}) ---")
        print(doc.page_content[:500])
