
from modules.impact_analyzer import analyze_change_impact

project_path = "sample_projects/EmployeeManagementSystem"

changed_function = "calculateSalary"

result = analyze_change_impact(
    project_path,
    changed_function
)

print("\n========== IMPACT ANALYSIS REPORT ==========")

print("\nChanged Function:")
print(result["changed_function"])

print("\nDefinition Files:")
for file in result["definition_files"]:
    print("-", file)

print("\nImpacted Files:")
for file in result["impacted_files"]:
    print("-", file)

print("\nRelated Test Files:")
for file in result["test_files"]:
    print("-", file)

print("\nDependencies:")
for dependency in result["dependencies"]:
    print(
        dependency["source"],
        "->",
        dependency["target"],
        "| Function:",
        dependency["function"]
    )

print("\nRelated Code:")
for item in result["related_code"]:
    print(
        item["file"],
        "| Similarity:",
        item["score"]
    )
