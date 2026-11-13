
import json

from modules.mcp_client import analyze_code_impact_via_mcp


PROJECT_PATH = (
    r"C:\Users\Lenovo\impactmap-ai"
    r"\sample_projects\EmployeeManagementSystem"
)

print("Connecting to MCP Server...")

response = analyze_code_impact_via_mcp(
    PROJECT_PATH,
    "calculateSalary"
)

print("\n========== AVAILABLE MCP TOOLS ==========")

for tool in response["available_tools"]:
    print("-", tool)

print("\n========== MCP IMPACT ANALYSIS ==========")

print(
    json.dumps(
        response["analysis"],
        indent=4
    )
)

print("\nMCP integration test completed successfully!")
