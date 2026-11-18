
import os
import json
import difflib
import requests

from dotenv import load_dotenv

load_dotenv()


def _get_setting(name, default=None):
    """Read configuration from environment variables or Streamlit secrets."""
    value = os.getenv(name)

    if value:
        return value

    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default


def _no_change_explanation(impact_result):
    """Return immediately when original and proposed code are identical."""

    function = impact_result.get(
        "changed_function", "Selected function"
    )

    impacted_files = impact_result.get("impacted_files", [])

    report = [
        "## Code Change Overview",
        f"No code changes were detected in `{function}`.",
        "",
        "## Impact Analysis",
        "The original and proposed code are identical. "
        "Therefore, no new code-change impact is introduced.",
        ""
    ]

    if impacted_files:
        report.append("### Existing Dependent Files")
        for file in impacted_files[:10]:
            report.append(f"- `{file}`")

    report.extend([
        "",
        "## Validation",
        "- No modified implementation requires validation.",
        "- Existing dependency information is retained.",
        "- Generated tests can still be executed independently.",
        "",
        "---",
        "*Analysis completed without invoking the Llama model.*"
    ])

    return "\n".join(report)


def _generate_rule_based_explanation(impact_result):
    """Fallback explanation if Llama is unavailable."""

    function = impact_result.get(
        "changed_function", "Unknown function"
    )

    definition_files = impact_result.get("definition_files") or []
    impacted_files = impact_result.get("impacted_files") or []
    test_files = impact_result.get("test_files") or []
    dependencies = impact_result.get("dependencies") or []

    report = [
        "## 1. Change Overview",
        f"The function `{function}` has a proposed code modification.",
        "",
        "## 2. Impact Explanation"
    ]

    if definition_files:
        report.append(
            "Definition files: " + ", ".join(definition_files[:10])
        )

    if impacted_files:
        report.append("### Identified Impacted Files")
        report.extend(
            f"- `{file}`" for file in impacted_files[:10]
        )
    else:
        report.append("No impacted files were identified.")

    report.append("")
    report.append("## 3. Potential Risks")

    if dependencies:
        for dependency in dependencies[:10]:
            if isinstance(dependency, dict):
                report.append(
                    f"- `{dependency.get('target', 'Unknown')}` "
                    f"may be affected by `{function}`."
                )
    else:
        report.append("- No direct dependencies were identified.")

    report.append("")
    report.append("## 4. Recommended Tests")

    if test_files:
        report.extend(
            f"- Execute tests in `{file}`."
            for file in test_files[:10]
        )
    else:
        report.append("- Create or identify unit tests for the function.")

    report.extend([
        "- Verify normal and boundary inputs.",
        "- Execute regression tests.",
        "",
        "## 5. Developer Review",
        "- Review the modified function.",
        "- Review identified dependent files.",
        "- Verify compilation and test results.",
        "",
        "---",
        "*Generated using ImpactMap AI rule-based fallback.*"
    ])

    return "\n".join(report)


def generate_impact_explanation(
    impact_result,
    original_code=None,
    modified_code=None
):
    """
    Generate a focused impact explanation.

    Skip Ollama if the original and modified code are identical.
    """

    # --------------------------------------------------
    # STEP 1: CHECK WHETHER CODE ACTUALLY CHANGED
    # --------------------------------------------------

    if original_code is not None and modified_code is not None:

        original_normalized = str(original_code).replace(
            "\r\n", "\n"
        ).strip()

        modified_normalized = str(modified_code).replace(
            "\r\n", "\n"
        ).strip()

        if original_normalized == modified_normalized:
            return _no_change_explanation(impact_result)

    # --------------------------------------------------
    # STEP 2: READ AI CONFIGURATION
    # --------------------------------------------------

    provider = _get_setting(
        "LLM_PROVIDER", "ollama"
    ).lower()

    if provider != "ollama":
        return _generate_rule_based_explanation(impact_result)

    base_url = _get_setting(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    ).rstrip("/")

    model = _get_setting(
        "OLLAMA_MODEL",
        "llama3.2:latest"
    )

    # --------------------------------------------------
    # STEP 3: PREPARE COMPACT IMPACT CONTEXT
    # --------------------------------------------------

    context = {
        "changed_function": impact_result.get("changed_function"),
        "definition_files": (
            impact_result.get("definition_files") or []
        )[:10],
        "impacted_files": (
            impact_result.get("impacted_files") or []
        )[:10],
        "test_files": (
            impact_result.get("test_files") or []
        )[:10],
        "dependencies": (
            impact_result.get("dependencies") or []
        )[:10]
    }

    # Include the actual code difference in the AI prompt.
    code_diff = ""

    if original_code is not None and modified_code is not None:

        diff_lines = difflib.unified_diff(
            str(original_code).splitlines(),
            str(modified_code).splitlines(),
            fromfile="Original Code",
            tofile="Modified Code",
            lineterm=""
        )

        code_diff = "\n".join(diff_lines)[:5000]

    prompt = f"""
You are ImpactMap AI, a precise C++ code impact analyst.

Analyze only the supplied evidence.

IMPACT FINDINGS:
{json.dumps(context, default=str)}

ACTUAL CODE DIFFERENCE:
{code_diff if code_diff else "Code difference not supplied."}

Rules:
1. Never invent dependencies or file relationships.
2. Explain only changes supported by the supplied code and findings.
3. Distinguish confirmed impacts from possible risks.
4. Do not claim tests passed or failed.
5. Do not say the function is changing if no difference is supplied.
6. Keep the report short and technically accurate.

Use these sections:

## Change Overview
## Impacted Components
## Potential Risks
## Recommended Tests
## Developer Review

Keep the complete report concise and developer-focused.
"""

    # --------------------------------------------------
    # STEP 4: GENERATE FOCUSED AI EXPLANATION
    # --------------------------------------------------

    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "keep_alive": "5m",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 350,
                    "num_ctx": 2048
                }
            },
            timeout=(5, 60)
        )

        response.raise_for_status()

        result = response.json()

        explanation = (
            result.get("message", {}).get("content", "")
        )

        if not explanation.strip():
            raise ValueError("Llama returned an empty response.")

        return (
            explanation.strip()
            + "\n\n---\n"
            + "*Generated using Meta Llama 3.2 3B via Ollama.*"
        )

    except Exception as error:

        print(
            "ImpactMap AI: Llama unavailable. "
            f"Using rule-based fallback. Error: {error}"
        )

        return _generate_rule_based_explanation(impact_result)
