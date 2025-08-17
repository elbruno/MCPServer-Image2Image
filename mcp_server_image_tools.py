import os
import base64
import logging
from pathlib import Path
from typing import Optional

# FastMCP shim for local use if real package is not installed
try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    class FastMCP:
        def __init__(self, name: str):
            self.name = name

        def tool(self):
            def decorator(fn):
                return fn
            return decorator

        def run(self):
            raise NotImplementedError("FastMCP.run() is not implemented in the local shim")


logging.basicConfig(level=os.getenv("MCP_SERVER_LOGLEVEL", "INFO"))
logger = logging.getLogger("image.tools")

# create MCP instance named ImageTools
mcp = FastMCP("ImageTools")


def _read_image_as_base64(path: Path) -> str:
    with path.open("rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif suffix == ".png":
        mime = "image/png"
    else:
        mime = "application/octet-stream"
    return f"data:{mime};base64,{b64}"


def _save_base64_as_image(b64_string: str, out_path: Path) -> Path:
    header_sep = b64_string.find(",")
    if header_sep != -1:
        b64_string = b64_string[header_sep + 1 :]
    data = base64.b64decode(b64_string)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        f.write(data)
    return out_path


@mcp.tool()
def image_to_base64(image_path: str) -> str:
    """Convert a local image file to a base64 data URL string."""
    if not image_path:
        raise ValueError("image_path must be provided")
    candidate = Path(image_path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if not candidate.exists():
        raise FileNotFoundError(f"image_path not found: {candidate}")
    logger.info("Converting image to base64: %s", candidate)
    return _read_image_as_base64(candidate)


@mcp.tool()
def base64_to_image(base64_string: str, output_path: str) -> str:
    """Convert a base64 data URL or raw base64 string to an image file at output_path.

    Returns the path to the written file as a string.
    """
    if not base64_string:
        raise ValueError("base64_string must be provided")
    if not output_path:
        raise ValueError("output_path must be provided")
    out = Path(output_path)
    if not out.is_absolute():
        out = Path.cwd() / out
    saved = _save_base64_as_image(base64_string, out)
    logger.info("Saved image from base64 to %s", saved)
    return str(saved)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Image tools: convert image <-> base64")
    sub = parser.add_subparsers(dest="cmd")

    p1 = sub.add_parser("to-base64", help="Convert image to base64")
    p1.add_argument("image_path")

    p2 = sub.add_parser("from-base64", help="Convert base64 to image")
    p2.add_argument("base64_string")
    p2.add_argument("output_path")

    args = parser.parse_args()
    if args.cmd == "to-base64":
        print(image_to_base64(args.image_path))
    elif args.cmd == "from-base64":
        print(base64_to_image(args.base64_string, args.output_path))
    else:
        parser.print_help()
