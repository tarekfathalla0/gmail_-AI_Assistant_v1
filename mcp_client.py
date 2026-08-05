from __future__ import annotations

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools


SERVER_PARAMS = StdioServerParameters(
    command="uv",
    args=[
        "run",
        "python",
        "-m",
        "gmail_mcp.gmail_server",
    ],
)


_stdio_cm = None
_session = None
_tools = None


async def initialize_mcp_tools() -> None:
    global _stdio_cm, _session, _tools

    if _tools is not None:
        return

    _stdio_cm = stdio_client(SERVER_PARAMS)
    read, write = await _stdio_cm.__aenter__()

    _session = ClientSession(read, write)
    await _session.__aenter__()
    await _session.initialize()

    _tools = await load_mcp_tools(_session)


async def shutdown_mcp_tools() -> None:
    global _stdio_cm, _session, _tools

    if _session is not None:
        await _session.__aexit__(None, None, None)
        _session = None

    if _stdio_cm is not None:
        await _stdio_cm.__aexit__(None, None, None)
        _stdio_cm = None

    _tools = None


async def get_mcp_tools():
    if _tools is None:
        raise RuntimeError(
            "MCP tools have not been initialized. "
            "Call initialize_mcp_tools() before using get_mcp_tools()."
        )

    return _tools