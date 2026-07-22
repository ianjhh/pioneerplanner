import asyncio
import sys
import json
import httpx

async def main():
    """
    Lightweight Model Context Protocol (MCP) Server for PioneerPlanner.
    This reads JSON-RPC requests from standard input and writes to standard output,
    following the MCP specification for tool exposure.
    """
    while True:
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            break
            
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
            
        # Respond to MCP initialization or tool calls
        if req.get("method") == "mcp/initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "result": {
                    "capabilities": {
                        "tools": [
                            {
                                "name": "search_courses",
                                "description": "Search university courses by keyword or concept.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"}
                                    },
                                    "required": ["query"]
                                }
                            },
                            {
                                "name": "get_prerequisite_path",
                                "description": "Get the prerequisite dependency tree for a target course.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "course_id": {"type": "string"}
                                    },
                                    "required": ["course_id"]
                                }
                            }
                        ]
                    }
                }
            }
            print(json.dumps(resp), flush=True)
            
        elif req.get("method") == "mcp/invokeTool":
            tool_name = req["params"]["name"]
            tool_args = req["params"]["arguments"]
            result_data = None
            
            async with httpx.AsyncClient() as client:
                if tool_name == "search_courses":
                    query = tool_args.get("query", "")
                    res = await client.get(f"http://localhost:8000/api/v1/search?q={query}")
                    result_data = res.text
                elif tool_name == "get_prerequisite_path":
                    course_id = tool_args.get("course_id", "")
                    res = await client.get(f"http://localhost:8000/api/v1/courses/{course_id}/prereq-path")
                    result_data = res.text
            
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "result": {
                    "data": result_data
                }
            }
            print(json.dumps(resp), flush=True)

if __name__ == "__main__":
    asyncio.run(main())
