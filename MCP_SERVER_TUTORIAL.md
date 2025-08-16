# MCP Server Tutorial for Image-to-Image with AIFoundry

This tutorial shows how to create and run a minimal MCP-style HTTP server that accepts a model name (default `gpt`), an input image (either a server-local path or base64-encoded), and a prompt (default: apply a pirate style). The server forwards the request to the AIFoundry images/edit endpoint using the same environment variables as the existing `image2image.py` script.

Files added:

- `mcp_server.py` — Flask-based MCP server that exposes a `/image2image` POST endpoint.

Prerequisites

- Python 3.8+
- The repository already contains `requirements.txt`. Make sure the following packages are installed: `flask`, `requests`, `pillow`, `python-dotenv`.

1) Prepare environment

- Copy `.env.example` to `.env` at the repository root and set the following variables (these names match `image2image.py`):
  - `FOUNDRY_ENDPOINT` - the base endpoint for your Foundry instance (e.g. <https://your-foundry-host/>)
  - `FOUNDRY_API_KEY` - API key to call Foundry
  - `FOUNDRY_API_VERSION` - API version string used by Foundry
  - `FLUX_DEPLOYMENT_NAME` - flux deployment name
  - `GPT_DEPLOYMENT_NAME` - gpt deployment name

2) Install dependencies

Open a terminal (PowerShell) and create/activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3) Inspect `mcp_server.py`

The server exposes a single endpoint:

POST /image2image

Accepted inputs (JSON or form data):

- `model` (optional): `gpt` or `flux` (default: `gpt`)
- `prompt` (optional): text prompt (default: "update this image to be set in a pirate era")
- `image_base64` (either this) — full base64-encoded image string (optionally a data URL)
- `image_path` (or this) — server-local path pointing to an image file

Response: JSON with `generated` list containing file paths of produced images (saved under `generated/`).

4) Run the server for development

```powershell
python mcp_server.py
```

By default the server runs on port 5000. For production use, run behind a WSGI server like Gunicorn (on Linux) or another process manager.

5) Example requests

- Using `curl` (PowerShell) with a local image file path:

```powershell
$body = @{ model='gpt'; prompt='make this image pirate style'; image_path='01-lautaro.jpg' }
Invoke-RestMethod -Method Post -Uri http://localhost:5000/image2image -Body $body
```

- Using base64 payload (PowerShell example to encode a file and send JSON):

```powershell
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes('01-lautaro.jpg'))
$payload = @{ model='gpt'; prompt='make this image pirate style'; image_base64=$b64 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:5000/image2image -Body $payload -ContentType 'application/json'
```

6) Notes and troubleshooting

- The server expects the same environment variables used by `image2image.py`. If any are missing, calls to Foundry will fail.
- The generated images are saved into the `generated/` folder at the repository root.
- The endpoint returns the full server paths to the generated images. You can modify the server to instead return URLs or stream images back.
- This server is intended as a minimal MCP-style example. For production:
  - Add authentication.
  - Add request rate limiting, logging, and proper error handling.
  - Run behind a production WSGI server.

7) Next steps (optional enhancements)

- Add an OpenAPI (Swagger) spec and UI.
- Add health and readiness endpoints to conform with MCP server expectations.
- Add unit tests for the request handling and Foundry call wrapper.

That's it — you now have a minimal MCP server that wraps `image2image.py` logic and exposes it over HTTP.
