# ADK — MCP Integration Guide

> Highest priority for hackathon: partner MCP servers (Elastic, MongoDB, Arize, etc.)

## How It Works

`McpToolset` connects an ADK agent to any MCP server, exposing its tools to the agent. The agent can then call those tools like any other function tool.

```python
from google.adk.tools.mcp_tool import McpToolset
```

---

## Two Connection Types

### StdioConnectionParams — Local (dev / subprocess)

Use for MCP servers that run as a local process (npx, Python, etc.):

```python
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem",
                  "/absolute/path/to/folder"],  # MUST be absolute path
        )
    ),
    tool_filter=["list_directory", "read_file"],  # restrict exposed tools
)
```

### StreamableHTTPConnectionParams — Remote (production / hosted)

Use for remote MCP servers (partner servers, hosted APIs):

```python
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://mapstools.googleapis.com/mcp",
        headers={
            "X-Goog-Api-Key": os.getenv("GOOGLE_MAPS_API_KEY"),
            # or: "Authorization": "Bearer token"
        }
    )
)
```

---

## Full Working Example (local filesystem MCP)

```python
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

root_agent = LlmAgent(
    model="gemini-flash-latest",
    name="filesystem_agent",
    instruction="Help manage and search files in the project directory.",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-filesystem",
                          os.path.abspath("/your/folder")],
                )
            ),
            tool_filter=["list_directory", "read_file", "search_files"],
        )
    ],
)
```

## Full Working Example (remote MCP — partner server pattern)

```python
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

root_agent = LlmAgent(
    model="gemini-flash-latest",
    name="data_agent",
    instruction="Search and analyze data using the available tools.",
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=os.getenv("MCP_SERVER_URL"),
                headers={"Authorization": f"Bearer {os.getenv('MCP_API_KEY')}"}
            ),
            tool_filter=["search", "query", "list_indexes"],  # restrict for security
        )
    ],
)
```

---

## tool_filter

Restrict which tools the MCP server exposes to the agent. Always use this:
- Security: prevent agent from calling destructive operations
- Performance: smaller tool list = faster LLM routing
- Clarity: agent focuses on relevant tools

```python
tool_filter=["read_only_tool", "search_tool"]  # list of tool names
```

---

## Gotchas

| Issue | Fix |
|-------|-----|
| Relative paths fail | Always use `os.path.abspath()` for filesystem paths |
| Async agent.py breaks deployment | `agent.py` definition must be synchronous (no `async` at module level) |
| Connection leaks in tests | Call `await toolset.close()` after use |
| Stdio needs Node.js | `npx`-based servers require Node.js installed; add to Dockerfile if containerizing |
| SseConnectionParams deprecated | Use `StreamableHTTPConnectionParams` (newer) |

---

## Partner MCP Servers (hackathon)

Partners provide hosted MCP servers. Pattern is the same — use `StreamableHTTPConnectionParams` with their URL + API key:

| Partner | Notes |
|---------|-------|
| Elastic | Elasticsearch search/query tools |
| MongoDB | Atlas database query tools |
| Arize | LLM observability + eval tools |
| Dynatrace | Observability metrics/traces |
| GitLab | Code repository tools |
| Fivetran | Data pipeline tools |

Check partner docs for their MCP server URL and auth method. See [[partners/elastic]], [[partners/mongodb]], [[partners/arize]] for details.

---

## Building Your Own MCP Server

Expose ADK tools via MCP (for A2A-style interop):

```python
from mcp.server.fastmcp import FastMCP
import mcp.types

app = FastMCP("my-server")

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    adk_response = await your_adk_tool.run_async(arguments, tool_context=None)
    return [mcp.types.TextContent(type="text", text=json.dumps(adk_response))]
```

---

## Related

- [[concepts/adk]] — core ADK concepts
- [[concepts/mcp]] — MCP protocol overview
- [[concepts/adk-multi-agent]] — multi-agent patterns
- [[partners/elastic]], [[partners/mongodb]], [[partners/arize]] — partner MCP servers
