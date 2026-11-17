
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = PROJECT_ROOT / "mcp_server.py"


def extract_tool_output(tool_result):

    structured_data = getattr(
        tool_result,
        "structuredContent",
        None
    )

    if structured_data is not None:
        return structured_data

    for item in tool_result.content:

        if hasattr(item, "text"):

            try:
                return json.loads(item.text)

            except json.JSONDecodeError:
                continue

    raise RuntimeError(
        "Unable to read structured output from MCP tool."
    )


async def _call_mcp_tool(tool_name, arguments):

    if not SERVER_PATH.exists():
        raise FileNotFoundError(
            f"MCP server not found: {SERVER_PATH}"
        )

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
        cwd=str(PROJECT_ROOT)
    )

    async with stdio_client(server_parameters) as (
        read_stream,
        write_stream
    ):

        async with ClientSession(
            read_stream,
            write_stream
        ) as session:

            await session.initialize()

            tools_response = await session.list_tools()

            available_tools = [
                tool.name
                for tool in tools_response.tools
            ]

            if tool_name not in available_tools:
                raise RuntimeError(
                    f"MCP tool '{tool_name}' is not available."
                )

            tool_result = await session.call_tool(
                tool_name,
                arguments=arguments
            )

            if tool_result.isError:
                raise RuntimeError(
                    f"MCP tool '{tool_name}' failed: "
                    + str(tool_result.content)
                )

            output = extract_tool_output(tool_result)

            return output, available_tools


async def _run_project_scan(project_path):

    output, available_tools = await _call_mcp_tool(
        "scan_cpp_project",
        {
            "project_path": str(project_path)
        }
    )

    return {
        "scan": output,
        "available_tools": available_tools
    }


async def _run_impact_analysis(
    project_path,
    changed_function,
    source_file=None
):

    arguments = {
        "project_path": str(project_path),
        "changed_function": changed_function,
        "source_file": source_file or ""
    }

    output, available_tools = await _call_mcp_tool(
        "analyze_code_impact",
        arguments
    )

    return {
        "analysis": output,
        "available_tools": available_tools
    }


def scan_cpp_project_via_mcp(project_path):

    return asyncio.run(
        _run_project_scan(project_path)
    )


def analyze_code_impact_via_mcp(
    project_path,
    changed_function,
    source_file=None
):

    return asyncio.run(
        _run_impact_analysis(
            project_path,
            changed_function,
            source_file
        )
    )
