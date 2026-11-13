
from modules.code_comparator import compare_code


original_code = """
double calculateSalary(double basic, double bonus) {
    return basic + bonus;
}
"""

modified_code = """
double calculateSalary(double basic, double bonus) {
    return basic + bonus + 2000;
}
"""

result = compare_code(
    original_code,
    modified_code
)

print("\n========== CODE COMPARISON ==========")

print("Change Summary:")
print(result["change_summary"])

print("\nAdded Lines:")
for line in result["added_lines"]:
    print("+", line)

print("\nRemoved Lines:")
for line in result["removed_lines"]:
    print("-", line)

print("\nFunction Signature Changed:")
print(result["signature_changed"])

print("\nReturn Statement Changed:")
print(result["return_changed"])

print("\nUnified Diff:")
for line in result["unified_diff"]:
    print(line)
