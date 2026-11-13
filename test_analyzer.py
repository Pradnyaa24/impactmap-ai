
from modules.cpp_analyzer import analyze_cpp_project

project_path = (
    "sample_projects/EmployeeManagementSystem"
)

results = analyze_cpp_project(project_path)

print("\n========== IMPACTMAP AI ANALYSIS ==========")

print("\n1. FILES FOUND:")
for file in results["files"]:
    print("-", file)

print("\n2. CLASSES FOUND:")
for item in results["classes"]:
    print("-", item["name"], "| File:", item["file"])

print("\n3. FUNCTIONS FOUND:")
for item in results["functions"]:
    print("-", item["name"], "| File:", item["file"])

print("\n4. HEADER DEPENDENCIES:")
for item in results["includes"]:
    print("-", item["file"], "->", item["header"])

print("\n5. FUNCTION CALLS:")
for item in results["function_calls"]:
    print("-", item["name"], "| File:", item["file"])

print("\n========== ANALYSIS COMPLETED ==========")
