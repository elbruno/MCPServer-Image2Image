# MCPServer-Image2Image

This repository contains a simple MCP-based Image2Image server (`mcp_server.py`) that exposes an `image2image` tool. The tool wraps a Foundry/OpenAI-style images edit endpoint. The repository also includes scripts to create and activate a virtual environment.

## Quick start (Windows PowerShell)

1. Create and activate the virtual environment (if not already created):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install the project's requirements:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

3. Ensure you have a `.env` file with the following variables set:

```
FOUNDRY_ENDPOINT=<your_foundry_endpoint>
FOUNDRY_API_KEY=<your_api_key>
FOUNDRY_API_VERSION=<api_version>
FLUX_DEPLOYMENT_NAME=<flux_deployment>
GPT_DEPLOYMENT_NAME=<gpt_deployment>
```

4. Run the MCP server (this exposes the `image2image` tool):

```powershell
.\.venv\Scripts\python.exe mcp_server.py
```

The MCP server will start and listen for MCP client connections. By default `mcp.run()` will start an interactive MCP server (see MCP docs for client steps).

## Quick test (direct call without starting server)

If you want to test the `image2image` logic without running the MCP service, you can call the `image2image` function directly from a Python REPL or small script. Example:

```python
from mcp_server import image2image

# Call using a file path already on disk
print(image2image(image_path='02-bruno.jpg'))
```

or call with a base64 payload:

```python
from pathlib import Path
import base64

data = Path('02-bruno.jpg').read_bytes()
b64 = 'data:image/jpeg;base64,' + base64.b64encode(data).decode()
from mcp_server import image2image
print(image2image(image_base64=b64))
```

Note: the `image2image` tool will call the configured Foundry endpoint and requires valid endpoint and API key values.

## Troubleshooting

- If you see ModuleNotFoundError for `mcp`, install the package and extras:

```powershell
.\.venv\Scripts\pip.exe install "mcp[cli]"
```

- If the MCP server appears to hang when started in the terminal, it is running an interactive loop; run the server in a dedicated terminal window and use an MCP client to connect.

## Files of interest

- `mcp_server.py` - MCP server and the `image2image` tool implementation
- `requirements.txt` - Python dependencies
- `scripts/` - helper venv activation scripts for different shells

If you'd like, I can add a small client script to demonstrate connecting to the MCP server and invoking the `image2image` tool.
