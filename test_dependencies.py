
from modules.cpp_analyzer import analyze_cpp_project
from modules.dependency_analyzer import build_dependency_map

project_path = "sample_projects/EmployeeManagementSystem"

results = analyze_cpp_project(project_path)

dependencies = build_dependency_map(results)

print("\n========== DEPENDENCY MAP ==========")

for dependency in dependencies:
    print(
        dependency["source"],
        "->",
        dependency["target"],
        "| Function:",
        dependency["function"]
    )

print("\nTotal Dependencies:", len(dependencies))
