
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# MCP server script
SERVER_PATH = PROJECT_ROOT / "mcp_server.py"


def extract_tool_output(tool_result):

    # Prefer structured MCP output
    structured_data = getattr(
        tool_result,
        "structuredContent",
        None
    )

    if structured_data is not None:
        return structured_data

    # Fallback: parse JSON from text content
    for item in tool_result.content:

        if hasattr(item, "text"):

            try:
                return json.loads(item.text)

            except json.JSONDecodeError:
                continue

    raise RuntimeError(
        "Unable to read structured output from MCP tool."
    )


async def _run_impact_analysis(project_path, changed_function):

    if not SERVER_PATH.exists():
        raise FileNotFoundError(
            f"MCP server not found: {SERVER_PATH}"
        )

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
        cwd=str(PROJECT_ROOT)
    )

    async with stdio_client(server_parameters) as (read_stream, write_stream):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            # Initialize MCP connection
            await session.initialize()

            # Retrieve available tools
            tools_response = await session.list_tools()

            available_tools = [
                tool.name
                for tool in tools_response.tools
            ]

            if "analyze_code_impact" not in available_tools:
                raise RuntimeError(
                    "analyze_code_impact tool is not available."
                )

            # Invoke MCP tool
            tool_result = await session.call_tool(
                "analyze_code_impact",
                arguments={
                    "project_path": str(project_path),
                    "changed_function": changed_function
                }
            )

            if tool_result.isError:
                raise RuntimeError(
                    "MCP tool execution failed: "
                    + str(tool_result.content)
                )

            analysis = extract_tool_output(tool_result)

            return {
                "analysis": analysis,
                "available_tools": available_tools
            }


def analyze_code_impact_via_mcp(project_path, changed_function):

    return asyncio.run(
        _run_impact_analysis(
            project_path,
            changed_function
        )
    )
