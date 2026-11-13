
import re
import math
from pathlib import Path
from collections import Counter


def load_project_documents(project_path):
    """Load C++ source files and project documentation."""

    project_path = Path(project_path)

    supported_extensions = {
        ".cpp", ".h", ".hpp", ".txt", ".md"
    }

    documents = []

    for file_path in project_path.rglob("*"):

        if file_path.suffix.lower() not in supported_extensions:
            continue

        try:
            content = file_path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            documents.append({
                "file": str(file_path.relative_to(project_path)),
                "content": content
            })

        except OSError:
            continue

    return documents


def chunk_documents(documents, chunk_size=40, overlap=5):
    """Split documents into overlapping line-based chunks."""

    chunks = []

    for document in documents:

        lines = document["content"].splitlines()

        for start in range(0, len(lines), chunk_size - overlap):

            chunk_lines = lines[start:start + chunk_size]

            chunk_text = "\n".join(chunk_lines).strip()

            if chunk_text:

                chunks.append({
                    "file": document["file"],
                    "text": chunk_text,
                    "start_line": start + 1
                })

    return chunks


def tokenize(text):
    """Convert text into lowercase tokens."""

    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())


def build_tfidf_index(chunks):
    """Build a TF-IDF index using Python dictionaries."""

    documents = []
    document_frequency = Counter()

    for chunk in chunks:

        tokens = tokenize(chunk["text"])
        term_counts = Counter(tokens)

        documents.append({
            **chunk,
            "term_counts": term_counts
        })

        document_frequency.update(set(tokens))

    total_documents = len(documents)

    for document in documents:

        weights = {}

        for term, count in document["term_counts"].items():

            tf = count / max(1, sum(document["term_counts"].values()))

            idf = math.log(
                (1 + total_documents) /
                (1 + document_frequency[term])
            ) + 1

            weights[term] = tf * idf

        document["vector"] = weights

    return documents


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two sparse vectors."""

    common_terms = set(vector_a) & set(vector_b)

    dot_product = sum(
        vector_a[term] * vector_b[term]
        for term in common_terms
    )

    magnitude_a = math.sqrt(
        sum(value ** 2 for value in vector_a.values())
    )

    magnitude_b = math.sqrt(
        sum(value ** 2 for value in vector_b.values())
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def search_documents(query, index, top_k=3):
    """Retrieve the most relevant document chunks."""

    query_tokens = tokenize(query)
    query_counts = Counter(query_tokens)

    if not query_counts:
        return []

    document_frequency = Counter()

    for document in index:
        document_frequency.update(set(document["term_counts"]))

    total_documents = len(index)

    query_vector = {}

    for term, count in query_counts.items():

        tf = count / len(query_tokens)

        idf = math.log(
            (1 + total_documents) /
            (1 + document_frequency.get(term, 0))
        ) + 1

        query_vector[term] = tf * idf

    results = []

    for document in index:

        score = cosine_similarity(
            query_vector,
            document["vector"]
        )

        if score > 0:

            results.append({
                "file": document["file"],
                "text": document["text"],
                "start_line": document["start_line"],
                "score": round(score, 4)
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results[:top_k]
