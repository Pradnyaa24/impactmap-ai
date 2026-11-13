
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():

    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            await session.initialize()

            print("\nMCP Server Connected Successfully!")

            print("\n========== AVAILABLE MCP TOOLS ==========")

            tools = await session.list_tools()

            for tool in tools.tools:
                print("-", tool.name)

            print("\n========== CODE IMPACT ANALYSIS ==========")

            result = await session.call_tool(
                "analyze_code_impact",
                {
                    "project_path": "sample_projects/EmployeeManagementSystem",
                    "changed_function": "calculateSalary"
                }
            )

            for content in result.content:
                if hasattr(content, "text"):
                    print(content.text)


asyncio.run(main())
