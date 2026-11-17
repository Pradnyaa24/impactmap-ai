
import re
from pathlib import Path

from modules.cpp_analyzer import analyze_cpp_project
from modules.dependency_analyzer import build_dependency_map

from modules.rag_engine import (
    load_project_documents,
    chunk_documents,
    build_tfidf_index,
    search_documents
)


def normalize_file_path(file_path):
    return str(file_path).replace("\\", "/").strip()


def discover_related_test_files(project_path, changed_function, impacted_files=None):
    """
    Discover tests that reference the selected function.

    Also preserves test files already identified through dependencies.
    Returns project-relative paths such as tests/SalaryTest.cpp.
    """

    project_root = Path(project_path).resolve()
    discovered_tests = set()

    # Keep test files already identified by dependency analysis.
    for file_path in impacted_files or []:
        normalized = normalize_file_path(file_path)

        if normalized.startswith("tests/") and normalized.endswith(".cpp"):
            candidate = project_root / normalized

            if candidate.is_file():
                discovered_tests.add(normalized)

    # Search all C++ test files for the selected function name.
    tests_directory = project_root / "tests"

    if tests_directory.is_dir():
        function_pattern = re.compile(
            rf"\b{re.escape(changed_function)}\b",
            re.IGNORECASE
        )

        for test_path in tests_directory.rglob("*.cpp"):
            try:
                content = test_path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

                if function_pattern.search(content):
                    relative_path = test_path.relative_to(
                        project_root
                    ).as_posix()

                    discovered_tests.add(relative_path)

            except OSError:
                continue

    return sorted(discovered_tests)


def analyze_change_impact(
    project_path,
    changed_function,
    top_k=5,
    source_file=None
):

    # Step 1: Scan the complete C++ project
    analysis = analyze_cpp_project(project_path)

    # Step 2: Build project dependencies
    dependencies = build_dependency_map(analysis)

    normalized_source = (
        normalize_file_path(source_file)
        if source_file
        else None
    )

    # Step 3: Find the selected function's definition files
    definition_files = sorted({
        item["file"]
        for item in analysis["functions"]
        if (
            item["name"].lower() == changed_function.lower()
            and (
                normalized_source is None
                or normalize_file_path(item["file"]).lower()
                == normalized_source.lower()
            )
        )
    })

    # Step 4: Find dependencies belonging to the selected definition
    matching_dependencies = [
        dependency
        for dependency in dependencies
        if (
            dependency["function"].lower()
            == changed_function.lower()
            and (
                normalized_source is None
                or normalize_file_path(dependency["target"]).lower()
                == normalized_source.lower()
            )
        )
    ]

    # Step 5: Identify directly impacted files
    impacted_files = sorted({
        dependency["source"]
        for dependency in matching_dependencies
    })

    # Step 6: Discover tests by function reference and dependencies
    test_files = discover_related_test_files(
        project_path,
        changed_function,
        impacted_files
    )

    # Step 7: Retrieve related project knowledge using RAG
    documents = load_project_documents(project_path)

    chunks = chunk_documents(documents)

    index = build_tfidf_index(chunks)

    search_query = changed_function

    if normalized_source:
        search_query = f"{changed_function} {normalized_source}"

    related_code = search_documents(
        search_query,
        index,
        top_k=top_k
    )

    return {
        "changed_function": changed_function,
        "selected_source_file": normalized_source,
        "definition_files": definition_files,
        "impacted_files": impacted_files,
        "test_files": test_files,
        "dependencies": matching_dependencies,
        "related_code": related_code
    }
