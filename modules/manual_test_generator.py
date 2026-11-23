"""Build C++ test programs from user-entered assertion conditions."""

import os
import re
from pathlib import Path


INCLUDE_PATTERN = re.compile(r"^\s*#\s*include\s*[<\"][^>\"]+[>\"]\s*$", re.M)


def _failure(reason):
    return {
        "supported": False,
        "reason": reason,
        "code": "",
        "test_cases": [],
        "baseline_comparisons": [],
        "source": "manual",
    }


def build_manual_test_suite(project_path, source_file, setup_code, cases):
    """Wrap explicit C++ boolean conditions in a standalone assert program."""
    if not project_path or not source_file:
        return _failure("Select a project source file before preparing manual tests.")

    root = Path(project_path).expanduser().resolve()
    selected = Path(str(source_file))
    if not selected.is_absolute():
        selected = root / selected
    try:
        selected = selected.resolve()
        selected.relative_to(root)
    except (OSError, ValueError):
        return _failure("The selected source file is outside the project folder.")
    if not selected.is_file():
        return _failure("The selected C++ source file could not be read.")

    valid_cases = []
    for index, item in enumerate(cases or [], start=1):
        if not isinstance(item, dict):
            continue
        condition = str(item.get("condition", "")).strip()
        if not condition:
            continue
        if "\n" in condition or "\r" in condition or ";" in condition:
            return _failure(f"Test case {index}: enter one boolean expression without a semicolon or line break.")
        valid_cases.append({
            "name": str(item.get("name") or f"Test case {len(valid_cases) + 1}")[:120],
            "input": condition,
            "expected": condition,
            "description": "User-entered assertion condition.",
            "category": "manual",
        })

    if not valid_cases:
        return _failure("Enter at least one test condition. Example: salary.calculateSalary(30000, 5000) == 45500")

    try:
        source = selected.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return _failure(f"Could not read the selected C++ source: {error}")

    includes = list(dict.fromkeys(INCLUDE_PATTERN.findall(source)))
    preamble = ["#include <cassert>", "#include <iostream>"]
    for include in includes:
        if include.strip() not in preamble:
            preamble.append(include.strip())

    lines = preamble + ["", "int main() {"]
    setup = str(setup_code or "").strip()
    if setup:
        lines.extend(f"    {line}" for line in setup.splitlines())
        lines.append("")
    for case in valid_cases:
        lines.append(f"    // {case['name']}")
        lines.append(f"    assert(({case['input']}));")
    lines.extend([
        '    std::cout << "All manual test cases passed.\\n";',
        "    return 0;",
        "}",
    ])
    code = "\n".join(lines) + "\n"
    return {
        "supported": True,
        "reason": "Prepared C++ assertions from your manually entered test conditions.",
        "code": code,
        "test_cases": valid_cases,
        "baseline_comparisons": [],
        "source": "manual",
    }
