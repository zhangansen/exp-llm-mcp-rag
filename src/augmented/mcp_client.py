"""
Referring from https://modelcontextprotocol.io/quickstart/client
"""


import asyncio
from typing import Any, Optional

from rich import print as rprint

from mcp import ClientSession, StdioServerParameters, Tool
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from contextlib import AsyncExitStack

from dotenv import load_dotenv

from augmented.utils.pretty import ALogger, RICH_CONSOLE
from augmented.utils.info import PROJECT_ROOT_DIR
from augmented.mcp_tools import PresetMcpTools

load_dotenv()

_log = ALogger("[mcp_client]")


class MCPClient:
    def __init__(
        self,
        name: str,
        command: str,
        args: list[str],
        version: str = "0.0.1",
    ) -> None:
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.name = name
        self.version = version
        self.command = command
        self.args = args
        self.tools: list[Tool] = []

    async def init(self) -> None:
        await self._connect_to_server()

    async def cleanup(self) -> None:
        """Close the MCP connection, swallowing known Windows/anyio cleanup noise."""
        try:
            await self.exit_stack.aclose()
        except RuntimeError as exc:
            # anyio on Windows throws "Attempted to exit cancel scope in a
            # different task" during async-generator finalisation.  This is
            # harmless — the subprocess is already terminated.
            if "cancel scope" in str(exc):
                return
            rprint(f"[yellow]Cleanup RuntimeError (ignored):[/] {exc}")
        except McpError:
            # Server already disconnected — nothing to clean up.
            return
        except Exception:
            rprint("[yellow]Error during MCP client cleanup, traceback:[/]")
            RICH_CONSOLE.print_exception()

    def get_tools(self) -> list[Tool]:
        return self.tools

    async def call_tool(self, name: str, params: dict[str, Any]) -> Any:
        return await self.session.call_tool(name, params)

    async def _connect_to_server(self) -> None:
        """Connect to an MCP server over stdio."""
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
        )
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        try:
            await asyncio.wait_for(self.session.initialize(), timeout=120.0)
            response = await asyncio.wait_for(self.session.list_tools(), timeout=15.0)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"MCP server '{self.name}' timed out during initialization. "
                f"Command: {self.command} {' '.join(self.args)}"
            ) from None
        except McpError as exc:
            raise RuntimeError(
                f"MCP server '{self.name}' closed the connection before listing tools. "
                f"Command: {self.command} {' '.join(self.args)}"
            ) from exc

        self.tools = response.tools
        _log.title(f"Connected to '{self.name}' – {len(self.tools)} tools")
        rprint([tool.name for tool in self.tools])


async def example() -> None:
    for mcp_tool in [
        PresetMcpTools.filesystem.append_mcp_params(f" {PROJECT_ROOT_DIR.as_posix()}"),
        PresetMcpTools.fetch,
    ]:
        rprint(mcp_tool.shell_cmd)
        mcp_client = MCPClient(**mcp_tool.to_common_params())
        try:
            await mcp_client.init()
            tools = mcp_client.get_tools()
            rprint(tools)
        except RuntimeError as exc:
            rprint(f"[red]Failed to connect:[/] {exc}")
        finally:
            await mcp_client.cleanup()


if __name__ == "__main__":
    asyncio.run(example())