
def generate_impact_explanation(impact_result):

    changed_function = impact_result["changed_function"]
    definition_files = impact_result["definition_files"]
    impacted_files = impact_result["impacted_files"]
    test_files = impact_result["test_files"]
    dependencies = impact_result["dependencies"]

    report = []

    # 1. Change Overview
    report.append("## 1. Change Overview\n")
    report.append(
        f"The function `{changed_function}` is being modified."
    )

    if definition_files:
        report.append(
            "Its definition is located in: "
            + ", ".join(definition_files)
        )

    # 2. Impact Explanation
    report.append("\n## 2. Impact Explanation\n")

    if dependencies:
        for dependency in dependencies:
            report.append(
                f"- `{dependency['source']}` may be affected "
                f"because it references `{dependency['function']}` "
                f"in `{dependency['target']}`."
            )
    else:
        report.append(
            "No direct dependencies were identified by the analyzer."
        )

    # 3. Potential Risks
    report.append("\n## 3. Potential Risks\n")
    report.append(
        f"- Changes to `{changed_function}` may affect its callers."
    )
    report.append(
        "- Changes to function parameters or return values "
        "may require updates in dependent files."
    )
    report.append(
        "- Existing business logic may behave differently "
        "after the modification."
    )

    # 4. Recommended Test Cases
    report.append("\n## 4. Recommended Test Cases\n")

    if test_files:
        for test_file in test_files:
            report.append(
                f"- Execute the tests in `{test_file}`."
            )
    else:
        report.append(
            "- Identify or create unit tests for the modified function."
        )

    report.append(
        f"- Test normal, boundary, and invalid input scenarios "
        f"for `{changed_function}`."
    )

    # 5. Developer Review Checklist
    report.append("\n## 5. Developer Review Checklist\n")
    report.append("- [ ] Review the modified function.")
    report.append("- [ ] Review all identified impacted files.")
    report.append("- [ ] Execute the related unit tests.")
    report.append("- [ ] Check for compilation errors.")
    report.append("- [ ] Verify that existing functionality is preserved.")

    report.append(
        "\n---\n"
        "*Generated using ImpactMap AI Mock Explanation Engine. "
        "This is a rule-based report, not an actual LLM-generated response.*"
    )

    return "\n".join(report)
