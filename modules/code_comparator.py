
import difflib
import re


def compare_code(original_code, modified_code):
    """
    Compare original and modified source code.

    Returns added lines, removed lines, unified diff,
    function signature changes and return statement changes.
    """

    original_lines = original_code.splitlines()
    modified_lines = modified_code.splitlines()

    # --------------------------------------------------
    # LINE-BY-LINE COMPARISON
    # --------------------------------------------------

    differ = difflib.SequenceMatcher(
        None,
        original_lines,
        modified_lines
    )

    added_lines = []
    removed_lines = []
    modified_blocks = []

    for tag, i1, i2, j1, j2 in differ.get_opcodes():

        if tag == "insert":

            added_lines.extend(modified_lines[j1:j2])

        elif tag == "delete":

            removed_lines.extend(original_lines[i1:i2])

        elif tag == "replace":

            removed_lines.extend(original_lines[i1:i2])
            added_lines.extend(modified_lines[j1:j2])

            modified_blocks.append({
                "original": original_lines[i1:i2],
                "modified": modified_lines[j1:j2]
            })

    # --------------------------------------------------
    # UNIFIED DIFF
    # --------------------------------------------------

    unified_diff = list(
        difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="Original Code",
            tofile="Modified Code",
            lineterm=""
        )
    )

    # --------------------------------------------------
    # FUNCTION SIGNATURE DETECTION
    # Basic C++ function signature pattern
    # --------------------------------------------------

    signature_pattern = re.compile(
        r"^[ \t]*(?:[\w:*&<>,~]+\s+)+"
        r"[\w:~]+\s*\([^;{}]*\)\s*(?:const\s*)?(?:\{|;)?",
        re.MULTILINE
    )

    original_signatures = signature_pattern.findall(original_code)
    modified_signatures = signature_pattern.findall(modified_code)

    signature_changed = (
        set(original_signatures) != set(modified_signatures)
    )

    # --------------------------------------------------
    # RETURN STATEMENT DETECTION
    # --------------------------------------------------

    return_pattern = re.compile(
        r"\breturn\b[^;]*;",
        re.MULTILINE
    )

    original_returns = return_pattern.findall(original_code)
    modified_returns = return_pattern.findall(modified_code)

    return_changed = original_returns != modified_returns

    # --------------------------------------------------
    # CHANGE SUMMARY
    # --------------------------------------------------

    if not added_lines and not removed_lines:

        change_summary = "No code changes detected."

    else:

        change_summary = (
            f"{len(added_lines)} added line(s) and "
            f"{len(removed_lines)} removed line(s) detected."
        )

    return {
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "modified_blocks": modified_blocks,
        "added_count": len(added_lines),
        "removed_count": len(removed_lines),
        "unified_diff": unified_diff,
        "signature_changed": signature_changed,
        "original_signatures": original_signatures,
        "modified_signatures": modified_signatures,
        "return_changed": return_changed,
        "original_returns": original_returns,
        "modified_returns": modified_returns,
        "change_summary": change_summary
    }
