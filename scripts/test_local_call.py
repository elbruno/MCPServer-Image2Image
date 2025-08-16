import os
import sys

# Ensure project root is on sys.path when run from scripts/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import mcp_server


def fake_call_foundry_edit(image_path, prompt, model='gpt'):
    """Fake replacement for call_foundry_edit for local testing.

    Returns a list with the absolute path to the input image so callers can
    verify the function returns file paths without making HTTP requests.
    """
    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Test image not found: {abs_path}")
    return [abs_path]


def main():
    # Replace the real network call with our fake for a dry-run
    mcp_server.call_foundry_edit = fake_call_foundry_edit

    test_image = os.path.join(ROOT, '02-bruno.jpg')
    print('Calling image2image with local test image:', test_image)
    out = mcp_server.image2image(image_path=test_image)
    print('image2image returned:', out)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Test failed:', e)
        raise
