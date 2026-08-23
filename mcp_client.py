from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any

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

_exit_stack: AsyncExitStack | None = None
_session: ClientSession | None = None
_tools: list[Any] | None = None


async def initialize_mcp_tools() -> None:
    """
    Initialize the Gmail MCP server and load its tools.

    The entire MCP lifecycle is managed by one AsyncExitStack so that
    enter/exit happen in the same async context/task.
    """

    global _exit_stack, _session, _tools

    if _tools is not None:
        return

    stack = AsyncExitStack()

    try:
        # Enter stdio client through the same exit stack
        read, write = await stack.enter_async_context(
            stdio_client(SERVER_PARAMS)
        )

        # Create MCP session
        session = ClientSession(read, write)

        # Enter session through the same exit stack
        await stack.enter_async_context(session)

        # Initialize MCP protocol
        await session.initialize()

        # Load LangChain-compatible tools
        tools = await load_mcp_tools(session)

        # Only publish globals after successful initialization
        _exit_stack = stack
        _session = session
        _tools = tools

    except Exception:
        # If initialization fails, clean everything up
        await stack.aclose()
        raise


async def shutdown_mcp_tools() -> None:
    """
    Shutdown the MCP connection.

    IMPORTANT:
    The same AsyncExitStack that opened the MCP connection
    is responsible for closing it.
    """

    global _exit_stack, _session, _tools

    if _exit_stack is None:
        return

    stack = _exit_stack

    # Clear globals first so another call cannot reuse
    # a connection that is currently shutting down.
    _exit_stack = None
    _session = None
    _tools = None

    try:
        await stack.aclose()
    except Exception:
        # Do not allow MCP shutdown errors to crash FastAPI shutdown.
        # Log if needed instead of raising.
        import logging

        logging.getLogger(__name__).exception(
            "Failed to shutdown MCP tools cleanly"
        )


async def get_mcp_tools() -> list[Any]:
    """
    Return initialized MCP tools.
    """

    if _tools is None:
        raise RuntimeError(
            "MCP tools have not been initialized. "
            "Call initialize_mcp_tools() before using get_mcp_tools()."
        )

    return _tools