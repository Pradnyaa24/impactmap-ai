
from modules.impact_analyzer import analyze_change_impact
from modules.llm_explainer import generate_impact_explanation

PROJECT_PATH = (
    r"C:\Users\Lenovo\impactmap-ai"
    r"\sample_projects\EmployeeManagementSystem"
)

print("Running code impact analysis...")

impact_result = analyze_change_impact(
    PROJECT_PATH,
    "calculateSalary"
)

print("Generating AI explanation...")

explanation = generate_impact_explanation(impact_result)

print("\n========== AI IMPACT REPORT ==========\n")
print(explanation)
