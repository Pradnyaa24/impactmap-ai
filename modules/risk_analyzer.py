
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
    4. Code comparison
    5. C++ test execution status
    """

    risk_score = 0
    reasons = []

    # --------------------------------------------------
    # STEP 1: DEPENDENCY IMPACT
    # --------------------------------------------------

    impacted_files = impact_result.get("impacted_files", [])
    definition_files = impact_result.get("definition_files", [])
    test_files = impact_result.get("test_files", [])

    impacted_file_count = len(impacted_files)
    test_file_count = len(test_files)

    if impacted_file_count == 0:

        reasons.append("No dependent files were identified.")

    elif impacted_file_count <= 2:

        risk_score += 2

        reasons.append(
            f"{impacted_file_count} dependent file(s) were identified."
        )

    elif impacted_file_count <= 4:

        risk_score += 3

        reasons.append(
            f"{impacted_file_count} dependent file(s) were identified."
        )

    else:

        risk_score += 4

        reasons.append(
            f"{impacted_file_count} dependent file(s) were identified. "
            "The change has a wide dependency impact."
        )

    # --------------------------------------------------
    # STEP 2: FUNCTION DEFINITION CHECK
    # --------------------------------------------------

    if definition_files:

        reasons.append(
            f"Function definition found in {len(definition_files)} file(s)."
        )

    else:

        risk_score += 1

        reasons.append(
            "Function definition could not be identified."
        )

    # --------------------------------------------------
    # STEP 3: RELATED TEST CHECK
    # --------------------------------------------------

    if test_files:

        reasons.append(
            f"{test_file_count} related test file(s) identified."
        )

    else:

        risk_score += 2

        reasons.append(
            "No related test files were identified."
        )

    # --------------------------------------------------
    # STEP 4: CODE COMPARISON
    # --------------------------------------------------

    added_line_count = 0
    removed_line_count = 0

    if comparison:

        added_line_count = comparison.get("added_count", 0)
        removed_line_count = comparison.get("removed_count", 0)

        if comparison.get("signature_changed", False):

            risk_score += 2

            reasons.append(
                "Function signature changed. "
                "Dependent function calls may require updates."
            )

        else:

            reasons.append(
                "No function signature changes detected."
            )

        if comparison.get("return_changed", False):

            risk_score += 1

            reasons.append(
                "Return statement changes detected. "
                "Business logic may be affected."
            )

        else:

            reasons.append(
                "No return statement changes detected."
            )

        total_changed_lines = (
            added_line_count + removed_line_count
        )

        if total_changed_lines >= 20:

            risk_score += 2

            reasons.append(
                f"{total_changed_lines} lines changed. "
                "The change size is relatively large."
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
                "Change size is relatively small."
            )

    # --------------------------------------------------
    # STEP 5: AUTOMATED TEST EXECUTION STATUS
    # --------------------------------------------------

    test_status = (test_status or "NOT_RUN").upper()

    test_risk_points = 0

    if test_status == "PASSED":

        reasons.append(
            "Automated C++ tests passed successfully."
        )

    elif test_status == "FAILED":

        test_risk_points = 3
        risk_score += test_risk_points

        reasons.append(
            "Automated C++ tests failed. "
            "The modified code may have introduced a regression."
        )

    elif test_status == "COMPILE_FAILED":

        test_risk_points = 3
        risk_score += test_risk_points

        reasons.append(
            "C++ test compilation failed. "
            "The change could not be validated."
        )

    elif test_status == "EXECUTION_BLOCKED":

        test_risk_points = 2
        risk_score += test_risk_points

        reasons.append(
            "Windows Application Control blocked test execution. "
            "The test result could not be verified."
        )

    elif test_status == "TIMEOUT":

        test_risk_points = 2
        risk_score += test_risk_points

        reasons.append(
            "C++ test execution timed out. "
            "The test result could not be verified."
        )

    elif test_status == "ERROR":

        test_risk_points = 2
        risk_score += test_risk_points

        reasons.append(
            "An error occurred in the C++ test runner."
        )

    else:

        reasons.append(
            "Automated C++ tests were not run or their status is unknown."
        )

    # --------------------------------------------------
    # STEP 6: DETERMINE RISK LEVEL
    # --------------------------------------------------

    if risk_score >= 4:

        risk_level = "HIGH"

    elif risk_score >= 2:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"

    # --------------------------------------------------
    # STEP 7: GENERATE RECOMMENDATION
    # --------------------------------------------------

    if test_status == "FAILED":

        recommendation = (
            "Fix the failing C++ tests before merging. "
            "Review the modified function and all impacted files."
        )

    elif test_status == "COMPILE_FAILED":

        recommendation = (
            "Resolve the C++ compilation errors and rerun the tests "
            "before merging."
        )

    elif test_status == "EXECUTION_BLOCKED":

        recommendation = (
            "C++ test execution was blocked by Windows security policy. "
            "The test result is unverified. Request an approved test "
            "execution environment and review the modified function "
            "and impacted files before merging."
        )

    elif test_status == "TIMEOUT":

        recommendation = (
            "Investigate the test timeout and rerun the tests "
            "before merging."
        )

    elif test_status == "ERROR":

        recommendation = (
            "Investigate the test runner error and validate the "
            "modified code before merging."
        )

    elif risk_level == "HIGH":

        recommendation = (
            "Perform a detailed review of the modified function, "
            "dependent files and test coverage before merging."
        )

    elif risk_level == "MEDIUM":

        recommendation = (
            "Review the modified function and dependent files. "
            "Execute related tests before merging."
        )

    else:

        recommendation = (
            "The detected change has relatively low impact. "
            "Complete the normal code review before merging."
        )

    # --------------------------------------------------
    # STEP 8: RETURN RISK ANALYSIS
    # --------------------------------------------------

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "impacted_file_count": impacted_file_count,
        "test_file_count": test_file_count,
        "added_line_count": added_line_count,
        "removed_line_count": removed_line_count,
        "test_status": test_status,
        "test_risk_points": test_risk_points,
        "reasons": reasons,
        "recommendation": recommendation
    }
