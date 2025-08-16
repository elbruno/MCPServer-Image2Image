import os
import base64
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import tempfile
import logging
from pathlib import Path
from typing import Optional, List

load_dotenv()

# Configure basic logging. The level can be overridden with the MCP_SERVER_LOGLEVEL env var.
LOG_LEVEL = os.getenv("MCP_SERVER_LOGLEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mcp.image2image")

# Environment variables (same names used in image2image.py)
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")
FOUNDRY_API_VERSION = os.getenv("FOUNDRY_API_VERSION")
FLUX_DEPLOYMENT_NAME = os.getenv("FLUX_DEPLOYMENT_NAME")
GPT_DEPLOYMENT_NAME = os.getenv("GPT_DEPLOYMENT_NAME")

# Create an MCP server
mcp = FastMCP("Image2Image")


def validate_env() -> None:
    """Validate required environment variables and log helpful messages for new users."""
    missing = []
    for var in ("FOUNDRY_ENDPOINT", "FOUNDRY_API_KEY", "FOUNDRY_API_VERSION", "FLUX_DEPLOYMENT_NAME", "GPT_DEPLOYMENT_NAME"):
        if not os.getenv(var):
            missing.append(var)
    if missing:
        logger.warning(
            "The following environment variables are not set: %s.\n" \
            "The MCP tool may not work until these are configured. You can set them in a .env file or in your environment.",
            ", ".join(missing),
        )
    else:
        logger.debug("All required environment variables appear to be set.")

def call_foundry_edit(image_path: str, prompt: str, model: str = "gpt") -> List[str]:
    """Call the Foundry images/edit endpoint with given image file path and prompt.

    Returns the list of generated image file paths.
    """
    logger.info("Preparing request to Foundry for model=%s prompt='%s' image=%s", model, prompt, image_path)

    deployment = GPT_DEPLOYMENT_NAME if model == "gpt" else FLUX_DEPLOYMENT_NAME

    base_path = f"openai/deployments/{deployment}/images"
    params = f"?api-version={FOUNDRY_API_VERSION}"
    edit_url = f"{FOUNDRY_ENDPOINT}{base_path}/edits{params}"

    request_body = {
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }

    if model == "gpt":
        request_body["input_fidelity"] = "high"
        request_body["quality"] = "high"
    else:
        request_body["quality"] = "hd"

    # Use context manager to ensure file is closed promptly
    with open(image_path, "rb") as img_file:
        files = {"image": (Path(image_path).name, img_file)}
        logger.debug("POST %s headers=(Api-Key, x-ms-model-mesh-model-name=%s) data=%s files=%s", edit_url, deployment, {k: request_body[k] for k in request_body}, "<binary image>")
        resp = requests.post(
            edit_url,
            headers={"Api-Key": FOUNDRY_API_KEY, "x-ms-model-mesh-model-name": deployment},
            data=request_body,
            files=files,
        )
    try:
        resp.raise_for_status()
    except Exception as exc:
        logger.error("Foundry returned an error: %s - response: %s", exc, getattr(resp, "text", "<no body>"))
        raise

    resp_json = resp.json()
    logger.debug("Foundry response JSON keys: %s", list(resp_json.keys()))

    # ensure output directory
    out_dir = Path.cwd() / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)

    saved_files: List[str] = []
    for idx, item in enumerate(resp_json.get("data", [])):
        b64_img = item.get("b64_json")
        if not b64_img:
            logger.warning("Response entry %d did not contain 'b64_json', skipping", idx)
            continue
        image = Image.open(BytesIO(base64.b64decode(b64_img)))
        filename = out_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{model}_{idx+1}.png"
        image.save(filename)
        logger.info("Saved generated image: %s", filename)
        saved_files.append(str(filename))

    if not saved_files:
        logger.warning("No generated images were returned from Foundry.")

    return saved_files

def save_base64_to_file(b64_string: str) -> str:
    """Decode base64 image content and write to a temporary file. Return the file path."""
    header_sep = b64_string.find(",")
    if header_sep != -1:
        # remove data url prefix
        b64_string = b64_string[header_sep + 1 :]

    data = base64.b64decode(b64_string)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(data)
    tmp.flush()
    tmp.close()
    logger.info("Wrote temporary image file: %s", tmp.name)
    return tmp.name


@mcp.tool()
def image2image(
    model: str = "gpt",
    prompt: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_path: Optional[str] = None,
) -> List[str]:
    """MCP tool that converts an image using gpt or flux and the desired prompt.

    Parameters:
      - model: 'gpt' or 'flux' (default 'gpt')
      - prompt: text prompt (default pirate style)
      - image_base64: base64-encoded image data OR
      - image_path: server-local path to an image file

    Returns a list of generated image file paths.
    """
    model = (model or "gpt").lower()
    prompt = prompt or "update this image to be set in a pirate era"

    logger.info("image2image called with model=%s prompt='%s' image_base64=%s image_path=%s", model, prompt, bool(image_base64), image_path)

    tmp_created = False
    img_path: Optional[str] = None

    if image_base64:
        img_path = save_base64_to_file(image_base64)
        tmp_created = True
    elif image_path:
        candidate = Path(os.path.expanduser(image_path))
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if not candidate.is_file():
            logger.error("image_path not found: %s", candidate)
            raise FileNotFoundError(f"image_path not found: {candidate}")
        img_path = str(candidate)
    else:
        logger.error("No image provided to image2image tool")
        raise ValueError("No image provided. Please provide 'image_base64' or 'image_path'.")

    try:
        logger.debug("Calling Foundry edit with image=%s", img_path)
        saved = call_foundry_edit(img_path, prompt, model=model)
        logger.info("image2image completed, %d files saved", len(saved))
        return saved
    finally:
        if tmp_created and img_path and Path(img_path).exists():
            try:
                Path(img_path).unlink()
                logger.debug("Removed temporary file: %s", img_path)
            except Exception:
                logger.exception("Failed to remove temporary image file: %s", img_path)


if __name__ == '__main__':
    mcp.run()    