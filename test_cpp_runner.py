
from modules.cpp_test_runner import run_cpp_tests

project_path = (
    r"C:\Users\Lenovo\impactmap-ai"
    r"\sample_projects\EmployeeManagementSystem"
)

result = run_cpp_tests(project_path)

print("\n========== C++ TEST RESULTS ==========")
print("Status:", result["status"])
print("Message:", result["message"])

if result.get("compile_errors"):
    print("\nCompilation Errors:")
    print(result["compile_errors"])

if result.get("test_output"):
    print("\nTest Output:")
    print(result["test_output"])

if result.get("test_errors"):
    print("\nTest Errors:")
    print(result["test_errors"])
