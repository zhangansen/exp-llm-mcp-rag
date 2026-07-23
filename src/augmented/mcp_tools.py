from __future__ import annotations

from dataclasses import dataclass
import os
import shlex

from dotenv import load_dotenv

load_dotenv()


@dataclass
class McpToolInfo:
    name:str
    shell_cmd_pattern:str
    main_cmd_options:str=""
    mcp_params:str=""

    @property
    def shell_cmd(self)->str:#一个模板多种格式
        return self.shell_cmd_pattern.format(
            main_cmd_options=self.main_cmd_options,
            mcp_params=self.mcp_params,
        )
    
    def copy(self) -> "McpToolInfo":
        """Return a shallow copy, so class-level presets are never mutated."""
        return McpToolInfo(
            name=self.name,
            shell_cmd_pattern=self.shell_cmd_pattern,
            main_cmd_options=self.main_cmd_options,
            mcp_params=self.mcp_params,
        )

    def append_mcp_params(self, params: str) -> "McpToolInfo":
        """Return a new instance with additional MCP params appended."""
        if not params:
            return self.copy()
        new = self.copy()
        new.mcp_params += params
        return new

    def append_main_cmd_options(self, options: str) -> "McpToolInfo":
        """Return a new instance with additional command options appended."""
        if not options:
            return self.copy()
        new = self.copy()
        new.main_cmd_options += options
        return new
    
    def to_common_params(self)->dict[str,str]:
        command,*args = shlex.split(self.shell_cmd, posix=False)
        return dict(
            name=self.name,
            command=command,
            args=args,
        )
    

class McpCmdOptions:
    uvx_use_cn_mirror = (
        ("--extra-index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple")
        if os.environ.get("USE_CN_MIRROR")
        else ""
    )
    npx_use_cn_mirror = (
        ("--registry https://registry.npmmirror.com")
        if os.environ.get("USE_CN_MIRROR")
        else ""
    )
    fetch_server_mcp_use_proxy = (
        f"--proxy-url {os.environ.get('PROXY_URL')}"
        if os.environ.get("PROXY_URL")
        else ""
    )


class PresetMcpTools:#使用的时候不需要每次都实例化，所以属性没有写self.,是类属性
    filesystem = McpToolInfo(
        name="filesystem",
        shell_cmd_pattern="npx {main_cmd_options} -y @modelcontextprotocol/server-filesystem {mcp_params}",
    ).append_main_cmd_options(
        McpCmdOptions.npx_use_cn_mirror,
    )
    fetch = (
        McpToolInfo(
            name="fetch",
            shell_cmd_pattern="uvx {main_cmd_options} mcp-server-fetch {mcp_params}",
        )
        .append_main_cmd_options(
            McpCmdOptions.uvx_use_cn_mirror,
        )
        .append_mcp_params(
            McpCmdOptions.fetch_server_mcp_use_proxy,
        )
    )
