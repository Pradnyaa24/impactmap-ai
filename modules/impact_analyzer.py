
from modules.cpp_analyzer import analyze_cpp_project
from modules.dependency_analyzer import build_dependency_map

from modules.rag_engine import (
    load_project_documents,
    chunk_documents,
    build_tfidf_index,
    search_documents
)


def analyze_change_impact(project_path, changed_function, top_k=5):

    # Step 1: Analyze C++ project
    analysis = analyze_cpp_project(project_path)

    # Step 2: Build dependency relationships
    dependencies = build_dependency_map(analysis)

    # Step 3: Find the changed function's definition files
    definition_files = sorted({
        item["file"]
        for item in analysis["functions"]
        if item["name"].lower() == changed_function.lower()
    })

    # Step 4: Find direct dependent files
    matching_dependencies = [
        dependency
        for dependency in dependencies
        if dependency["function"].lower() == changed_function.lower()
    ]

    impacted_files = sorted({
        dependency["source"]
        for dependency in matching_dependencies
    })

    # Step 5: Identify related test files
    test_files = [
        file for file in impacted_files
        if file.replace("\\", "/").startswith("tests/")
    ]

    # Step 6: Retrieve relevant code using RAG
    documents = load_project_documents(project_path)
    chunks = chunk_documents(documents)
    index = build_tfidf_index(chunks)

    related_code = search_documents(
        changed_function,
        index,
        top_k=top_k
    )

    return {
        "changed_function": changed_function,
        "definition_files": definition_files,
        "impacted_files": impacted_files,
        "test_files": test_files,
        "dependencies": matching_dependencies,
        "related_code": related_code
    }
