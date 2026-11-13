
import re
from pathlib import Path


def analyze_cpp_project(project_path):

    project_path = Path(project_path)

    results = {
        "files": [],
        "classes": [],
        "functions": [],
        "includes": [],
        "function_calls": []
    }

    cpp_files = list(project_path.rglob("*.cpp"))

    header_files = (
        list(project_path.rglob("*.h"))
        + list(project_path.rglob("*.hpp"))
    )

    all_files = cpp_files + header_files

    for file_path in all_files:

        content = file_path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        relative_path = str(file_path.relative_to(project_path))

        results["files"].append(relative_path)

        # Extract classes and structures
        class_matches = re.findall(
            r'\b(?:class|struct)\s+(\w+)',
            content
        )

        for class_name in class_matches:
            results["classes"].append({
                "name": class_name,
                "file": relative_path
            })

        # Extract function and method definitions
        function_pattern = (
            r'^[ \t]*'
            r'(?:[\w:<>~*&]+\s+)?'
            r'(?:[\w~]+\s*::\s*)?'
            r'([A-Za-z_]\w*)\s*'
            r'\([^;{}]*\)\s*'
            r'(?:const\s*)?'
            r'(?:noexcept\s*)?'
            r'\{'
        )

        function_matches = re.findall(
            function_pattern,
            content,
            re.MULTILINE
        )

        for function_name in function_matches:
            results["functions"].append({
                "name": function_name,
                "file": relative_path
            })

        # Extract header dependencies
        include_matches = re.findall(
            r'^\s*#include\s+"([^"]+)"',
            content,
            re.MULTILINE
        )

        for include_name in include_matches:
            results["includes"].append({
                "header": include_name,
                "file": relative_path
            })

        # Extract basic function calls
        call_matches = re.findall(
            r'\b(\w+)\s*\(',
            content
        )

        for function_name in call_matches:
            results["function_calls"].append({
                "name": function_name,
                "file": relative_path
            })

    return results
