
from pathlib import Path
import hashlib
import json
from collections import OrderedDict

import chromadb


SUPPORTED_EXTENSIONS = {
    ".cpp", ".h", ".hpp", ".txt", ".md"
}

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "venv312",
    "__pycache__",
    "node_modules",
    "build",
    "dist"
}

# Reuse one ChromaDB client throughout the running process.
_chroma_client = None

# Keep a maximum of 8 recently used project indexes in memory.
_collection_cache = OrderedDict()
MAX_CACHED_COLLECTIONS = 8


def get_chroma_client():
    """Return the shared in-memory ChromaDB client."""

    global _chroma_client

    if _chroma_client is None:
        _chroma_client = chromadb.Client()

    return _chroma_client


def load_project_documents(project_path):
    """Load supported source-code and documentation files."""

    project_path = Path(project_path)

    documents = []

    if not project_path.exists() or not project_path.is_dir():
        return documents

    for file_path in project_path.rglob("*"):

        if any(part in IGNORED_DIRECTORIES for part in file_path.parts):
            continue

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            content = file_path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            if content.strip():
                documents.append({
                    "file": str(file_path.relative_to(project_path)),
                    "content": content
                })

        except OSError:
            continue

    return documents


def chunk_documents(documents, chunk_size=40, overlap=5):
    """Split documents into overlapping line-based chunks."""

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "chunk_size must be positive and overlap must be "
            "smaller than chunk_size."
        )

    chunks = []

    step = chunk_size - overlap

    for document in documents:

        lines = document["content"].splitlines()

        for start in range(0, len(lines), step):

            chunk_lines = lines[start:start + chunk_size]

            chunk_text = "\n".join(chunk_lines).strip()

            if chunk_text:

                chunks.append({
                    "file": document["file"],
                    "text": chunk_text,
                    "start_line": start + 1
                })

    return chunks


def get_chunks_fingerprint(chunks):
    """Generate a stable fingerprint for the supplied code chunks."""

    serialized_chunks = json.dumps(
        chunks,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        serialized_chunks.encode("utf-8")
    ).hexdigest()


def build_chroma_index(chunks):
    """
    Build or reuse a ChromaDB vector index.

    Unchanged project content reuses its existing collection.
    Changed project content automatically gets a new index.
    """

    client = get_chroma_client()

    fingerprint = get_chunks_fingerprint(chunks)

    # Return the existing index if this exact content was indexed before.
    if fingerprint in _collection_cache:

        _collection_cache.move_to_end(fingerprint)

        return _collection_cache[fingerprint]

    collection_name = "impactmap_" + fingerprint[:32]

    # Check whether this collection already exists in the shared client.
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "description": "ImpactMap AI source-code embeddings",
            "hnsw:space": "cosine"
        }
    )

    # If the collection is incomplete, rebuild it.
    if collection.count() != len(chunks):

        client.delete_collection(name=collection_name)

        collection = client.create_collection(
            name=collection_name,
            metadata={
                "description": "ImpactMap AI source-code embeddings",
                "hnsw:space": "cosine"
            }
        )

        batch_size = 500

        for start in range(0, len(chunks), batch_size):

            batch = chunks[start:start + batch_size]

            ids = [
                f"chunk_{start + i}"
                for i in range(len(batch))
            ]

            documents = [
                item["text"] for item in batch
            ]

            metadatas = [
                {
                    "file": item["file"],
                    "start_line": int(item["start_line"])
                }
                for item in batch
            ]

            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

    # Remember this collection for subsequent analysis requests.
    _collection_cache[fingerprint] = collection

    _collection_cache.move_to_end(fingerprint)

    # Remove the oldest cached collection when the limit is exceeded.
    while len(_collection_cache) > MAX_CACHED_COLLECTIONS:

        old_fingerprint, old_collection = (
            _collection_cache.popitem(last=False)
        )

        client.delete_collection(
            name=old_collection.name
        )

    return collection


def build_tfidf_index(chunks):
    """
    Backward-compatible function name.

    ChromaDB is used internally instead of TF-IDF.
    Existing MCP and impact-analysis modules remain compatible.
    """

    return build_chroma_index(chunks)


def search_documents(query, index, top_k=3):
    """Retrieve semantically relevant code chunks from ChromaDB."""

    if not query or not query.strip():
        return []

    if top_k <= 0:
        return []

    total_chunks = index.count()

    if total_chunks == 0:
        return []

    results = index.query(
        query_texts=[query],
        n_results=min(top_k, total_chunks),
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    retrieved_documents = results.get("documents", [[]])[0]
    retrieved_metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []

    for document, metadata, distance in zip(
        retrieved_documents,
        retrieved_metadatas,
        distances
    ):

        if not document or not metadata:
            continue

        # ChromaDB cosine distance = 1 - cosine similarity.
        similarity_score = max(
            0.0,
            min(1.0, 1.0 - float(distance))
        )

        output.append({
            "file": metadata.get("file", "Unknown"),
            "text": document,
            "start_line": metadata.get("start_line", 1),
            "score": round(similarity_score, 4)
        })

    return output
