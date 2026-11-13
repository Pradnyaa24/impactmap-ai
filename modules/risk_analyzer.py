
import re


def calculate_change_risk(
    impact_result,
    comparison=None,
    test_status="NOT_RUN"
):
    """
    Calculate code change risk using:
    1. Dependency impact
    2. Function definition detection
    3. Related test detection
    4. Function signature and return changes
    5. Business logic change detection
    6. Code change size
    7. Automated test execution status
    """

    risk_score = 0
    reasons = []

    impact_result = impact_result or {}
    comparison = comparison or {}

    # --------------------------------------------------
    # STEP 1: DEPENDENCY IMPACT
    # --------------------------------------------------

    impacted_files = impact_result.get("impacted_files", [])
    definition_files = impact_result.get("definition_files", [])
    test_files = impact_result.get("test_files", [])

    impacted_file_count = len(impacted_files)
    definition_file_count = len(definition_files)
    test_file_count = len(test_files)

    if impacted_file_count == 0:

        reasons.append(
            "No dependent files were identified."
        )

    elif impacted_file_count <= 2:

        risk_score += 2

        reasons.append(
            f"{impacted_file_count} dependent file(s) identified."
        )

    elif impacted_file_count <= 4:

        risk_score += 3

        reasons.append(
            f"{impacted_file_count} dependent file(s) identified. "
            "The change has a moderate dependency impact."
        )

    else:

        risk_score += 4

        reasons.append(
            f"{impacted_file_count} dependent file(s) identified. "
            "The change has a wide dependency impact."
        )

    # --------------------------------------------------
    # STEP 2: FUNCTION DEFINITION CHECK
    # --------------------------------------------------

    if definition_file_count > 0:

        reasons.append(
            f"Function definition found in "
            f"{definition_file_count} file(s)."
        )

    else:

        risk_score += 1

        reasons.append(
            "Function definition could not be identified."
        )

    # --------------------------------------------------
    # STEP 3: RELATED TEST CHECK
    # --------------------------------------------------

    if test_file_count > 0:

        reasons.append(
            f"{test_file_count} related test file(s) identified."
        )

    else:

        risk_score += 3

        reasons.append(
            "No related test files were identified. "
            "Regression risk is increased."
        )

    # --------------------------------------------------
    # STEP 4: CODE COMPARISON
    # --------------------------------------------------

    added_line_count = comparison.get("added_count", 0)
    removed_line_count = comparison.get("removed_count", 0)

    signature_changed = comparison.get(
        "signature_changed", False
    )

    return_changed = comparison.get(
        "return_changed", False
    )

    if signature_changed:

        risk_score += 3

        reasons.append(
            "Function signature changed. "
            "Dependent function calls may require updates."
        )

    else:

        reasons.append(
            "No function signature changes detected."
        )

    if return_changed:

        risk_score += 2

        reasons.append(
            "Return statement changes detected. "
            "Function behavior or returned values may be affected."
        )

    else:

        reasons.append(
            "No return statement changes detected."
        )

    # --------------------------------------------------
    # STEP 5: BUSINESS LOGIC CHANGE DETECTION
    # --------------------------------------------------

    # Look for changed code lines if the comparator provides them.
    # Supported optional keys: added_lines, removed_lines, diff,
    # unified_diff, and detailed_diff.

    changed_code = []

    for key in (
        "added_lines",
        "removed_lines",
        "diff",
        "unified_diff",
        "detailed_diff"
    ):

        value = comparison.get(key)

        if isinstance(value, str):
            changed_code.append(value)

        elif isinstance(value, (list, tuple)):
            changed_code.extend(
                str(line) for line in value
            )

    changed_code_text = "\n".join(changed_code)

    business_logic_changed = False

    if changed_code_text.strip():

        logic_patterns = [
            r"\bif\s*\(",
            r"\belse\b",
            r"\bswitch\s*\(",
            r"\bcase\b",
            r"\bfor\s*\(",
            r"\bwhile\s*\(",
            r"\breturn\b",
            r"==|!=|<=|>=",
            r"&&|\|\|",
            r"\+\+|--",
            r"\+=|-=|\*=|/=",
            r"[+\-*/%]",
            r"(?<![=!<>])=(?!=)"
        ]

        business_logic_changed = any(
            re.search(pattern, changed_code_text)
            for pattern in logic_patterns
        )

        if business_logic_changed:

            risk_score += 2

            reasons.append(
                "Potential business logic changes detected "
                "in the modified code."
            )

        else:

            reasons.append(
                "No major business logic patterns detected "
                "in the available changed lines."
            )

    else:

        reasons.append(
            "Business logic analysis skipped because "
            "detailed changed code lines are unavailable."
        )

    # --------------------------------------------------
    # STEP 6: CODE CHANGE SIZE
    # --------------------------------------------------

    total_changed_lines = (
        added_line_count + removed_line_count
    )

    if total_changed_lines >= 20:

        risk_score += 2

        reasons.append(
            f"{total_changed_lines} lines changed. "
            "The change size is large."
        )

    elif total_changed_lines >= 10:

        risk_score += 1

        reasons.append(
            f"{total_changed_lines} lines changed. "
            "The change size is moderate."
        )

    else:

        reasons.append(
            f"{total_changed_lines} lines changed. "
            "The change size is relatively small."
        )

    # --------------------------------------------------
    # STEP 7: AUTOMATED TEST EXECUTION STATUS
    # --------------------------------------------------

    test_status = (
        str(test_status or "NOT_RUN").strip().upper()
    )

    test_risk_points = 0

    if test_status == "PASSED":

        reasons.append(
            "Automated C++ tests passed successfully."
        )

    elif test_status == "FAILED":

        test_risk_points = 4
        risk_score += test_risk_points

        reasons.append(
            "Automated C++ tests failed. "
            "The modified code may have introduced a regression."
        )

    elif test_status == "COMPILE_FAILED":

        test_risk_points = 4
        risk_score += test_risk_points

        reasons.append(
            "C++ compilation failed. "
            "The proposed code could not be validated."
        )

    elif test_status == "EXECUTION_BLOCKED":

        test_risk_points = 3
        risk_score += test_risk_points

        reasons.append(
            "Test execution was blocked by a security policy. "
            "The test result could not be verified."
        )

    elif test_status == "TIMEOUT":

        test_risk_points = 3
        risk_score += test_risk_points

        reasons.append(
            "C++ test execution timed out. "
            "The test result could not be verified."
        )

    elif test_status == "ERROR":

        test_risk_points = 3
        risk_score += test_risk_points

        reasons.append(
            "An error occurred in the C++ test runner. "
            "The test result could not be verified."
        )

    else:

        test_risk_points = 2
        risk_score += test_risk_points

        reasons.append(
            "Automated C++ tests were not run or their status "
            "is unknown. The change remains unverified."
        )

    # --------------------------------------------------
    # STEP 8: DETERMINE RISK LEVEL
    # --------------------------------------------------

    if risk_score >= 8:

        risk_level = "HIGH"

    elif risk_score >= 4:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"

    # --------------------------------------------------
    # STEP 9: GENERATE RECOMMENDATION
    # --------------------------------------------------

    if test_status == "FAILED":

        recommendation = (
            "Fix the failing C++ tests before merging. "
            "Review the modified business logic and all impacted files."
        )

    elif test_status == "COMPILE_FAILED":

        recommendation = (
            "Resolve the C++ compilation errors and rerun "
            "the automated tests before merging."
        )

    elif test_status == "EXECUTION_BLOCKED":

        recommendation = (
            "Test execution was blocked by a security policy. "
            "Use an approved test environment and validate "
            "the proposed changes before merging."
        )

    elif test_status == "TIMEOUT":

        recommendation = (
            "Investigate the test timeout. Check for infinite loops "
            "or performance issues and rerun the tests."
        )

    elif test_status == "ERROR":

        recommendation = (
            "Investigate the test runner error. Verify the test "
            "environment and validate the modified code."
        )

    elif test_status == "NOT_RUN":

        recommendation = (
            "Run the related C++ tests before merging. "
            "Review the modified function and impacted files."
        )

    elif risk_level == "HIGH":

        recommendation = (
            "Perform a detailed code review. Validate business logic, "
            "dependent files and test coverage before merging."
        )

    elif risk_level == "MEDIUM":

        recommendation = (
            "Review the modified function and dependent files. "
            "Execute additional boundary and regression tests "
            "before merging."
        )

    else:

        recommendation = (
            "The detected change has relatively low impact. "
            "Complete the normal code review before merging."
        )

    # --------------------------------------------------
    # STEP 10: RETURN RISK ANALYSIS
    # --------------------------------------------------

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "impacted_file_count": impacted_file_count,
        "definition_file_count": definition_file_count,
        "test_file_count": test_file_count,
        "added_line_count": added_line_count,
        "removed_line_count": removed_line_count,
        "total_changed_lines": total_changed_lines,
        "signature_changed": signature_changed,
        "return_changed": return_changed,
        "business_logic_changed": business_logic_changed,
        "test_status": test_status,
        "test_risk_points": test_risk_points,
        "reasons": reasons,
        "recommendation": recommendation
    }
