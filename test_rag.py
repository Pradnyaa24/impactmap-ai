
from modules.rag_engine import (
    load_project_documents,
    chunk_documents,
    build_tfidf_index,
    search_documents
)

project_path = "sample_projects/EmployeeManagementSystem"

documents = load_project_documents(project_path)
print("Documents Loaded:", len(documents))

chunks = chunk_documents(documents)
print("Chunks Created:", len(chunks))

index = build_tfidf_index(chunks)
print("TF-IDF Index Created Successfully!")

query = "calculateSalary"

results = search_documents(query, index, top_k=3)

print("\n========== RAG SEARCH RESULTS ==========")

for result in results:
    print("\nFile:", result["file"])
    print("Line:", result["start_line"])
    print("Similarity:", result["score"])
    print("Code:")
    print(result["text"])
