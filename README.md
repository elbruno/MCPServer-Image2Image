# MCPServer-Image2Image

This repository contains a simple MCP-based Image2Image server (`mcp_server.py`) that exposes an `image2image` tool. The tool wraps a Foundry/OpenAI-style images edit endpoint. The repository also includes scripts to create and activate a virtual environment.

## Quick Start

1. Create and activate the virtual environment (if not already created):

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

    ***Note:** there are scripts in the `scripts/` directory to activate the virtual environment for different shells. This is the Powershell sample.*

1. Install the project's requirements:

    ```powershell
    .\.venv\Scripts\pip.exe install -r requirements.txt
    ```

1. Ensure you have a `.env` file with the following variables set:

    ```
    FOUNDRY_ENDPOINT=<your_foundry_endpoint>
    FOUNDRY_API_KEY=<your_api_key>
    FOUNDRY_API_VERSION=<api_version>
    FLUX_DEPLOYMENT_NAME=<flux_deployment>
    GPT_DEPLOYMENT_NAME=<gpt_deployment>
    ```

1. Start the MCP server (this exposes the `image2image` tool):

    You can start the server using the `mcp` CLI. Example (Server-Sent Events transport):

    ```powershell
    mcp start .\mcp_server.py -t sse
    ```

    This will start an MCP server that listens for MCP client connections. You can adjust the transport (`-t`) and host/port as needed. Below is an example `mcp.json` (editor integration) and a sample prompt for testing.

1. Add the mcp server to your favourite tool.

1. Attach and image, and you can use these prompts as references to trigger the image2image tool.

    Below are example prompts you can use when invoking the `image2image` tool. They assume you attach an input image (for example `02-bruno.jpg`) and request a transform.

- Anime (90s) - Use this to get a cel-shaded, dramatic anime look:

    *Use the attached image and create a new one with a format like an anime from the 90s: bright cel-shaded colors, dramatic rim lighting, halftone accents, slightly exaggerated facial features, and subtle film grain; keep the subject's pose and expression recognizable.*

- Mountain running (flux) - Photorealistic action composite using the `flux` model:

    *Generate a new image that uses the attached image and makes the person in the image to be running in the mountains, use the flux model for this.*

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

## Editor integration / mcp.json example

If your editor integrates with MCP, use an `mcp.json` file like the example below. It matches the Server-Sent Events transport shown above:

```json
{
    "servers": {
        "image2imagelabs": {
            "url": "http://0.0.0.0:8000/sse",
            "type": "http"
        }
    },
    "inputs": []
}
```
