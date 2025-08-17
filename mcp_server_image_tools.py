"""Image conversion tools for MCP (local shim compatible).

This module provides two small utilities exposed as MCP tools:

- `local_image_to_base64(image_path: str) -> str`:
    Convert a local image file to a base64-encoded data URL string.

- `base64_to_image(base64_string: str, output_path: str) -> str`:
    Decode a base64 data URL or raw base64 string and write it to disk.

Parameters and conventions used by the tool functions
- image_path: path to an existing image file. Can be relative or absolute.
    If relative, it is resolved against the current working directory.
- base64_string: either a full data URL (e.g. "data:image/png;base64,...")
    or a raw base64-encoded payload. The function will strip any leading
    data URL header before decoding.
- output_path: filesystem path where the decoded image will be written.
    If not absolute, it will be resolved against the current working
    directory. Parent directories will be created as needed.

Return values
- Both tools return strings. `local_image_to_base64` returns a data URL
    string. `base64_to_image` returns the absolute path to the written file.

Errors
- Functions raise `ValueError` for missing required parameters and
    `FileNotFoundError` when the input file cannot be found. Base64 decoding
    errors will propagate as `binascii.Error` / `ValueError`.
"""

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
def local_image_to_base64(image_path: str) -> str:
    """Convert a local image file to a base64 data URL string.

    Parameters
    - image_path (str): Path to the image file to encode. May be absolute
      or relative to the current working directory. Supported file suffixes
      are recognized for setting the MIME type (e.g. .jpg/.jpeg -> image/jpeg,
      .png -> image/png). Unknown suffixes will use application/octet-stream.

    Returns
    - str: A data URL string in the format 'data:<mime>;base64,<payload>'.

    Raises
    - ValueError: if `image_path` is falsy.
    - FileNotFoundError: if the resolved path does not exist.
    """
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
        """Decode a base64 data URL or raw base64 payload and write an image file.

        Parameters
        - base64_string (str): Either a full data URL (e.g. 'data:image/png;base64,...')
            or a raw base64 string. If a data URL header is present the header will be
            stripped before decoding.
        - output_path (str): Destination path for the decoded image. If a relative
            path is provided it will be resolved against the current working directory.
            Parent directories will be created if they do not exist.

        Returns
        - str: The absolute path to the file that was written as a string.

        Raises
        - ValueError: if either parameter is falsy.
        - binascii.Error / ValueError: if the base64 payload is invalid.
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
        print(local_image_to_base64(args.image_path))
    elif args.cmd == "from-base64":
        print(base64_to_image(args.base64_string, args.output_path))
    else:
        parser.print_help()
