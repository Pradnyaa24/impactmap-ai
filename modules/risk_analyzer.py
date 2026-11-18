import re


def _as_lines(value):
    """Convert supported comparison values into a list of text lines."""
    if value is None:
        return []
    if isinstance(value, str):
        return value.splitlines()
    if isinstance(value, (list, tuple)):
        lines = []
        for item in value:
            if isinstance(item, str):
                lines.extend(item.splitlines())
            elif item is not None:
                lines.append(str(item))
        return lines
    return []


def _clean_code_line(line):
    """Remove diff markers and simple comments from a changed line."""
    line = str(line).strip()

    if line.startswith(("+++", "---")):
        return ""
    if line.startswith(("+", "-")):
        line = line[1:].strip()

    # Remove ordinary single-line comments. This is intentionally a
    # lightweight heuristic, not a complete C++ lexer.
    line = re.sub(r"//.*$", "", line).strip()
    return line


def _extract_changed_lines(comparison):
    """
    Read changed lines from the comparison result.

    Prefer explicit added_lines/removed_lines fields. If those are absent,
    try to parse a unified diff supplied by the comparator.
    """
    added = _as_lines(comparison.get("added_lines"))
    removed = _as_lines(comparison.get("removed_lines"))

    if added or removed:
        return (
            [_clean_code_line(line) for line in added if _clean_code_line(line)],
            [_clean_code_line(line) for line in removed if _clean_code_line(line)],
            True,
        )

    for key in ("unified_diff", "diff", "detailed_diff"):
        diff_lines = _as_lines(comparison.get(key))
        if not diff_lines:
            continue

        parsed_added = []
        parsed_removed = []

        for line in diff_lines:
            line = str(line)
            if line.startswith(("+++", "---")):
                continue
            if line.startswith("+"):
                parsed_added.append(_clean_code_line(line))
            elif line.startswith("-"):
                parsed_removed.append(_clean_code_line(line))

        if parsed_added or parsed_removed:
            return (
                [line for line in parsed_added if line],
                [line for line in parsed_removed if line],
                True,
            )

    return [], [], False


def _normalize_expression(expression):
    """Normalize whitespace and redundant outer parentheses."""
    expression = re.sub(r"\s+", "", expression or "")
    expression = expression.rstrip(";")

    while (
        len(expression) >= 2
        and expression.startswith("(")
        and expression.endswith(")")
    ):
        expression = expression[1:-1]

    return expression


def _return_expressions(lines):
    """Extract simple C++ return expressions from changed lines."""
    expressions = []
    for line in lines:
        match = re.search(r"\breturn\s+(.+?)\s*;", line)
        if match:
            expressions.append(_normalize_expression(match.group(1)))
    return expressions


def _simple_assignment_aliases(lines):
    """
    Find simple local assignments such as:
        double total = basic + bonus;

    The type may include common C++ qualifiers and namespace/template text.
    This is used only to recognize straightforward temporary-variable
    refactoring in return statements.
    """
    aliases = {}

    assignment_pattern = re.compile(
        r"^\s*(?:(?:const|static|constexpr|volatile)\s+)*"
        r"[\w:<>,*&]+\s+(\w+)\s*=\s*(.+?)\s*;\s*$"
    )

    for line in lines:
        match = assignment_pattern.match(line)
        if not match:
            continue

        variable = match.group(1)
        expression = _normalize_expression(match.group(2))

        # Only treat uncomplicated expressions as aliases. Function calls,
        # increments and assignments can have side effects.
        if re.search(r"\+\+|--|(?<![=!<>])=(?!=)", expression):
            continue

        aliases[variable] = expression

    return aliases


def _expand_alias(expression, aliases):
    """Replace a returned temporary variable with its simple initializer."""
    expanded = expression
    for _ in range(5):
        replacement = aliases.get(expanded)
        if replacement is None or replacement == expanded:
            break
        expanded = replacement
    return _normalize_expression(expanded)


def _return_behavior_analysis(added_lines, removed_lines, lines_available,
                              return_changed):
    """
    Return (behavior_changed, equivalent_refactor).

    None means the available diff did not contain enough information.
    """
    if not return_changed:
        return False, False

    if not lines_available:
        return None, False

    old_returns = _return_expressions(removed_lines)
    new_returns = _return_expressions(added_lines)

    if not old_returns or not new_returns:
        return None, False

    aliases = _simple_assignment_aliases(added_lines)
    expanded_new_returns = [
        _expand_alias(expression, aliases)
        for expression in new_returns
    ]

    if sorted(old_returns) == sorted(expanded_new_returns):
        return False, True

    return True, False


def _has_control_flow_change(added_lines, removed_lines):
    """Detect changes to control-flow statements and conditions."""
    control_pattern = re.compile(
        r"\b(if|else|switch|case|for|while|do|break|continue|throw|catch)\b"
    )

    added_control = [
        _normalize_expression(line)
        for line in added_lines
        if control_pattern.search(line)
    ]
    removed_control = [
        _normalize_expression(line)
        for line in removed_lines
        if control_pattern.search(line)
    ]

    return sorted(added_control) != sorted(removed_control)


def _assignment_changes(added_lines, removed_lines):
    """
    Detect changed right-hand sides for the same assigned variable.

    New temporary variables alone are not treated as business-logic changes;
    return-expression and control-flow checks handle their meaningful effect.
    """
    assignment_pattern = re.compile(
        r"^\s*(?:[\w:<>,*&]+\s+)?(\w+)\s*=\s*(.+?)\s*;\s*$"
    )

    def collect(lines):
        result = {}
        for line in lines:
            if re.search(r"\b(return|if|while|for|switch)\b", line):
                continue
            match = assignment_pattern.match(line)
            if match:
                result[match.group(1)] = _normalize_expression(match.group(2))
        return result

    old_assignments = collect(removed_lines)
    new_assignments = collect(added_lines)

    for variable in old_assignments.keys() & new_assignments.keys():
        if old_assignments[variable] != new_assignments[variable]:
            return True

    return False


def calculate_change_risk(
    impact_result,
    comparison=None,
    test_status="NOT_RUN",
    generated_test_status="NOT_GENERATED",
    generated_test_count=0
):
    """
    Calculate code change risk using:
    1. Dependency impact
    2. Function definition detection
    3. Related test detection
    4. Function signature changes
    5. Return-expression behavior
    6. Control-flow and assignment changes
    7. Code change size
    8. Automated test execution status

    This is a heuristic risk estimate. It does not prove semantic
    equivalence or guarantee that code is safe.
    """

    risk_score = 0
    reasons = []

    impact_result = impact_result or {}
    comparison = comparison or {}

    # --------------------------------------------------
    # STEP 1: DEPENDENCY IMPACT
    # --------------------------------------------------

    impacted_files = impact_result.get("impacted_files") or []
    definition_files = impact_result.get("definition_files") or []
    test_files = impact_result.get("test_files") or []

    impacted_file_count = len(impacted_files)
    definition_file_count = len(definition_files)
    test_file_count = len(test_files)

    if impacted_file_count == 0:
        reasons.append("No dependent files were identified.")
    elif impacted_file_count <= 2:
        risk_score += 2
        reasons.append(f"{impacted_file_count} dependent file(s) identified.")
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
            f"Function definition found in {definition_file_count} file(s)."
        )
    else:
        risk_score += 1
        reasons.append("Function definition could not be identified.")

    # --------------------------------------------------
    # STEP 3: RELATED TEST CHECK
    # --------------------------------------------------

    if test_file_count > 0:
        reasons.append(f"{test_file_count} related test file(s) identified.")
    else:
        risk_score += 3
        reasons.append(
            "No related test files were identified. "
            "Regression risk is increased."
        )

    # --------------------------------------------------
    # STEP 4: CODE COMPARISON
    # --------------------------------------------------

    added_line_count = int(comparison.get("added_count") or 0)
    removed_line_count = int(comparison.get("removed_count") or 0)

    signature_changed = bool(comparison.get("signature_changed", False))
    return_changed = bool(comparison.get("return_changed", False))

    if signature_changed:
        risk_score += 3
        reasons.append(
            "Function signature changed. "
            "Dependent function calls may require updates."
        )
    else:
        reasons.append("No function signature changes detected.")

    added_lines, removed_lines, lines_available = _extract_changed_lines(
        comparison
    )

    return_behavior_changed, equivalent_return_refactor = (
        _return_behavior_analysis(
            added_lines,
            removed_lines,
            lines_available,
            return_changed,
        )
    )

    if not return_changed:
        reasons.append("No return statement changes detected.")
    elif equivalent_return_refactor:
        reasons.append(
            "Return statement was refactored using a temporary variable; "
            "the detected return expression remains equivalent."
        )
    elif return_behavior_changed is True:
        risk_score += 2
        reasons.append(
            "Return expression changed. The function's returned value "
            "may be different."
        )
    else:
        risk_score += 2
        reasons.append(
            "Return statement changed, but the available diff was not "
            "sufficient to verify whether the returned value is equivalent."
        )

    # --------------------------------------------------
    # STEP 5: BUSINESS LOGIC CHANGE DETECTION
    # --------------------------------------------------

    business_logic_changed = False
    business_logic_analysis_available = lines_available

    if lines_available:
        control_flow_changed = _has_control_flow_change(
            added_lines,
            removed_lines,
        )
        assignment_changed = _assignment_changes(
            added_lines,
            removed_lines,
        )

        business_logic_changed = (
            control_flow_changed
            or assignment_changed
            or return_behavior_changed is True
        )

        if business_logic_changed:
            risk_score += 2
            reasons.append(
                "Potential behavioral changes detected in return "
                "expressions, control flow, or existing assignments."
            )
        elif equivalent_return_refactor:
            reasons.append(
                "No behavioral change was detected in the return expression. "
                "The change appears to be a simple refactoring."
            )
        else:
            reasons.append(
                "No control-flow, return-expression, or existing-assignment "
                "changes were detected in the available diff."
            )
    else:
        reasons.append(
            "Behavioral analysis was limited because detailed added and "
            "removed code lines were unavailable."
        )

    # --------------------------------------------------
    # STEP 6: CODE CHANGE SIZE
    # --------------------------------------------------

    total_changed_lines = added_line_count + removed_line_count

    if total_changed_lines >= 20:
        risk_score += 2
        reasons.append(
            f"{total_changed_lines} lines changed. The change size is large."
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

    test_status = str(test_status or "NOT_RUN").strip().upper()
    test_risk_points = 0

    if test_status == "PASSED":
        reasons.append("Automated C++ tests passed successfully.")

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

    elif test_status == "NOT_AVAILABLE":
        generated_status_for_check = str(
            generated_test_status or "NOT_GENERATED"
        ).strip().upper()

        if generated_status_for_check in (
            "PASSED",
            "FAILED",
            "COMPILE_FAILED"
        ):
            reasons.append(
                "No pre-existing C++ test suite was found. "
                "Generated tests were used for validation."
            )
        else:
            test_risk_points = 2
            risk_score += test_risk_points
            reasons.append(
                "No pre-existing C++ tests or completed generated tests "
                "were available. The change remains unverified."
            )

    else:
        test_risk_points = 2
        risk_score += test_risk_points
        reasons.append(
            "Automated C++ tests were not run or their status is unknown. "
            "The change remains unverified."
        )

    # --------------------------------------------------
    # STEP 8: GENERATED TEST EXECUTION STATUS
    # --------------------------------------------------

    generated_test_status = str(
        generated_test_status or "NOT_GENERATED"
    ).strip().upper()

    generated_test_count = max(0, int(generated_test_count or 0))
    generated_test_risk_points = 0

    if generated_test_count == 0 or generated_test_status == "NOT_GENERATED":
        reasons.append("No additional generated test cases were available.")

    elif generated_test_status == "PASSED":
        reasons.append(
            f"All generated test cases passed. "
            f"Generated test count: {generated_test_count}."
        )

    elif generated_test_status == "FAILED":
        generated_test_risk_points = 4
        risk_score += generated_test_risk_points
        reasons.append(
            f"Generated test cases failed. "
            f"Generated test count: {generated_test_count}. "
            "The proposed change may violate expected business requirements."
        )

    elif generated_test_status == "COMPILE_FAILED":
        generated_test_risk_points = 4
        risk_score += generated_test_risk_points
        reasons.append(
            "Generated test compilation failed. "
            "The generated test suite could not be validated."
        )

    elif generated_test_status in (
        "EXECUTION_BLOCKED", "TIMEOUT", "ERROR", "NOT_RUN"
    ):
        generated_test_risk_points = 2
        risk_score += generated_test_risk_points
        reasons.append(
            f"Generated test execution status is {generated_test_status}. "
            "Additional validation is required."
        )

    else:
        generated_test_risk_points = 2
        risk_score += generated_test_risk_points
        reasons.append(
            "Generated test result is unknown. "
            "The proposed change remains partially unverified."
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

    if generated_test_status == "FAILED":
        recommendation = (
            "Generated test assertions failed. The proposed code may "
            "violate the specified business requirements. Correct the "
            "modified logic and rerun the generated tests before merging."
            )

    elif generated_test_status == "COMPILE_FAILED":
        recommendation = (
            "Generated tests could not compile. Review the generated "
            "test code and project dependencies before merging."
        )
    elif test_status == "FAILED":
        recommendation = (
            "Resolve the C++ compilation errors and rerun the automated "
            "tests before merging."
        )
    elif test_status == "EXECUTION_BLOCKED":
        recommendation = (
            "Test execution was blocked by a security policy. Use an approved "
            "test environment and validate the proposed changes."
        )
    elif test_status == "TIMEOUT":
        recommendation = (
            "Investigate the test timeout. Check for infinite loops or "
            "performance issues and rerun the tests."
        )
    elif test_status == "ERROR":
        recommendation = (
            "Investigate the test runner error. Verify the test environment "
            "and validate the modified code."
        )
    elif test_status == "NOT_RUN":
        recommendation = (
            "Run the related C++ tests before merging. Review the modified "
            "function and impacted files."
        )
    elif risk_level == "HIGH":
        recommendation = (
            "Perform a detailed code review. Validate business logic, "
            "dependent files, and test coverage before merging."
        )
    elif risk_level == "MEDIUM":
        recommendation = (
            "Review the modified function and dependent files. Execute "
            "additional boundary and regression tests before merging."
        )
    else:
        recommendation = (
            "The detected change has relatively low impact. Complete the "
            "normal code review before merging."
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
        "return_behavior_changed": return_behavior_changed,
        "equivalent_return_refactor": equivalent_return_refactor,
        "business_logic_changed": business_logic_changed,
        "business_logic_analysis_available": business_logic_analysis_available,
        "test_status": test_status,
        "test_risk_points": test_risk_points,
        "generated_test_status": generated_test_status,
        "generated_test_count": generated_test_count,
        "generated_test_risk_points": generated_test_risk_points,
        "reasons": reasons,
        "recommendation": recommendation,
    }
