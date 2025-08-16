import os
import base64
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import tempfile
import traceback
import sys

load_dotenv()

# Environment variables (same names used in image2image.py)
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")
FOUNDRY_API_VERSION = os.getenv("FOUNDRY_API_VERSION")
FLUX_DEPLOYMENT_NAME = os.getenv("FLUX_DEPLOYMENT_NAME")
GPT_DEPLOYMENT_NAME = os.getenv("GPT_DEPLOYMENT_NAME")

# Create an MCP server
mcp = FastMCP("Image2Image")


def call_foundry_edit(image_path, prompt, model='gpt'):
    """Call the Foundry images/edit endpoint with given image file path and prompt.

    Returns the list of generated image file paths.
    """
    if model == 'gpt':
        deployment = GPT_DEPLOYMENT_NAME
    else:
        deployment = FLUX_DEPLOYMENT_NAME

    base_path = f'openai/deployments/{deployment}/images'
    params = f'?api-version={FOUNDRY_API_VERSION}'
    edit_url = f"{FOUNDRY_ENDPOINT}{base_path}/edits{params}"

    request_body = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }

    if model == 'gpt':
        request_body["input_fidelity"] = "high"
        request_body["quality"] = "high"
    else:
        request_body["quality"] = "hd"

    files = {"image": (os.path.basename(image_path), open(image_path, "rb"))}

    resp = requests.post(
        edit_url,
        headers={'Api-Key': FOUNDRY_API_KEY, 'x-ms-model-mesh-model-name': deployment},
        data=request_body,
        files=files
    )
    resp.raise_for_status()
    resp_json = resp.json()

    # ensure output directory
    out_dir = os.path.join(os.getcwd(), "generated")
    os.makedirs(out_dir, exist_ok=True)

    saved_files = []
    for idx, item in enumerate(resp_json.get('data', [])):
        b64_img = item.get('b64_json')
        if not b64_img:
            continue
        image = Image.open(BytesIO(base64.b64decode(b64_img)))
        filename = os.path.join(out_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{model}_{idx+1}.png")
        image.save(filename)
        saved_files.append(filename)

    return saved_files


def save_base64_to_file(b64_string):
    """Decode base64 image content and write to a temporary file. Return the file path."""
    header_sep = b64_string.find(',')
    if header_sep != -1:
        # remove data url prefix
        b64_string = b64_string[header_sep+1:]

    data = base64.b64decode(b64_string)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    tmp.write(data)
    tmp.flush()
    tmp.close()
    return tmp.name


@mcp.tool()
def image2image(model: str = 'gpt', prompt: str | None = None, image_base64: str | None = None, image_path: str | None = None) -> list:
    """MCP tool that wraps the original /image2image Flask endpoint logic.

    Parameters:
      - model: 'gpt' or 'flux' (default 'gpt')
      - prompt: text prompt (default pirate style)
      - image_base64: base64-encoded image data OR
      - image_path: server-local path to an image file

    Returns a list of generated image file paths.
    """
    model = (model or 'gpt').lower()
    prompt = prompt or "update this image to be set in a pirate era"

    tmp_created = False
    img_path = None

    if image_base64:
        img_path = save_base64_to_file(image_base64)
        tmp_created = True
    elif image_path:
        candidate = os.path.expanduser(image_path)
        if not os.path.isabs(candidate):
            candidate = os.path.join(os.getcwd(), candidate)
        if not os.path.isfile(candidate):
            raise FileNotFoundError(f"image_path not found: {candidate}")
        img_path = candidate
    else:
        raise ValueError("No image provided. Please provide 'image_base64' or 'image_path'.")

    try:
        saved = call_foundry_edit(img_path, prompt, model=model)
        return saved
    finally:
        if tmp_created and img_path and os.path.exists(img_path):
            try:
                os.unlink(img_path)
            except Exception:
                pass


if __name__ == '__main__':
    # Run the MCP server. This will expose tools (like `image2image`) via MCP.
    try:
        mcp.run()
    except KeyboardInterrupt:
        # When a user or environment interrupts the process (Ctrl+C), exit cleanly.
        # Printing may fail if stdout/stderr were closed by the runtime, so guard it.
        try:
            print("MCP server interrupted by user. Shutting down.")
        except Exception:
            pass
        sys.exit(0)
    except Exception:
        # Log unexpected exceptions and exit with a non-zero code so callers know it failed.
        try:
            print("MCP server encountered an unexpected exception:")
            traceback.print_exc()
        except Exception:
            # If printing fails (streams closed), ensure we still exit with error
            pass
        sys.exit(1)
