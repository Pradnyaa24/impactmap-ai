
from mcp.server.fastmcp import FastMCP

from modules.cpp_analyzer import analyze_cpp_project
from modules.dependency_analyzer import build_dependency_map
from modules.impact_analyzer import analyze_change_impact

from modules.rag_engine import (
    load_project_documents,
    chunk_documents,
    build_tfidf_index,
    search_documents
)


mcp = FastMCP("ImpactMap AI")


@mcp.tool()
def scan_cpp_project(project_path: str) -> dict:
    """Scan a C++ project and extract files, classes and functions."""

    results = analyze_cpp_project(project_path)

    return {
        "files": results["files"],
        "classes": results["classes"],
        "functions": results["functions"]
    }


@mcp.tool()
def get_project_dependencies(project_path: str) -> list:
    """Analyze dependencies between C++ source files."""

    results = analyze_cpp_project(project_path)

    return build_dependency_map(results)


@mcp.tool()
def search_project_knowledge(
    project_path: str,
    query: str,
    top_k: int = 3
) -> list:
    """Search relevant C++ source code and project documentation."""

    documents = load_project_documents(project_path)

    chunks = chunk_documents(documents)

    index = build_tfidf_index(chunks)

    return search_documents(
        query,
        index,
        top_k
    )


@mcp.tool()
def analyze_code_impact(
    project_path: str,
    changed_function: str,
    source_file: str = ""
) -> dict:
    """Analyze the impact of a changed function in a specific source file."""

    return analyze_change_impact(
        project_path,
        changed_function,
        source_file=source_file or None
    )


if __name__ == "__main__":
    mcp.run()
