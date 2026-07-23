import re


class MCPClient:

    def __init__(self, name: str):
        self.name = name
        self.tools: list[dict] = []
        self._handlers: dict[str, callable] = {}

    def register(self, tool_defs: list[dict], handlers: dict[str, callable]):

        self.tools = tool_defs
        self._handlers = handlers

    def call_tool(self, tool_name: str, args: dict) -> str:
        handler = self._handlers.get(tool_name)
        if not handler:
            return f"MCP错误：不存在名为{tool_name}的工具"

        try:
            return handler(**args)
        except Exception as e:
            return f"MCP错误：{e}"

mcp_clients: dict[str, MCPClient] = {}

_DISALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_-]")

def normalize_mcp_name(name: str) -> str:

    return _DISALLOWED_CHARS.sub("_", name)

def _mock_server_docs():
    client = MCPClient("docs")
    client.register(
        tool_defs=[
            {
                "name": "search",
                "description": "Search documentation. (readOnly)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            },
            {
                "name": "get_version",
                "description": "Get API version. (readOnly)",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ],
        handlers={
            "search": lambda query: f"[docs] 关键词{query}共匹配到 3 条结果",
            "get_version": lambda: "[docs] API v2.1.0"
        }
    )
    return client

def _mock_server_deploy():
    client = MCPClient("deploy")
    client.register(
        tool_defs=[
            {
                "name": "trigger",
                "description": "Trigger a deployment. (destructive — requires approval in real CC)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"]
                }
            },
            {
                "name": "status",
                "description": "Check deployment status. (readOnly)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"]
                }
            }
        ],
        handlers={
            "trigger": lambda service: f"[deploy] Triggered: {service}",
            "status": lambda service: f"[deploy] {service}: running (v1.4.2)"
        }
    )

    return client

MOCK_SERVICE = {
    "docs": _mock_server_docs,
    "deploy": _mock_server_deploy
}

def connect_mcp(name: str) -> str:
    if name in mcp_clients:
        return f"MCP服务端{name}已处于连接状态"

    factory = MOCK_SERVICE.get(name)
    if not factory:
        available = ", ".join(MOCK_SERVICE.keys())
        return f"未知服务端{name}，可用服务端列表：{available}"

    mcp_client = factory()
    mcp_clients[name] = mcp_client
    tool_names = [t["name"] for t in mcp_client.tools]
    print(f"\033[31m[mcp] connected: {name} → {tool_names}\033[0m")
    return f"已连接至MCP服务端{name}，共识别出{len(mcp_client.tools)}个可用工具：{', '.join(tool_names)}"

def run_connect_mcp(name: str) -> str:
    return connect_mcp(name)
