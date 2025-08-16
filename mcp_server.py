import os
import base64
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
import tempfile
import traceback

load_dotenv()

# Environment variables (same names used in image2image.py)
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.getenv("FOUNDRY_API_KEY")
FOUNDRY_API_VERSION = os.getenv("FOUNDRY_API_VERSION")
FLUX_DEPLOYMENT_NAME = os.getenv("FLUX_DEPLOYMENT_NAME")
GPT_DEPLOYMENT_NAME = os.getenv("GPT_DEPLOYMENT_NAME")

app = Flask(__name__)


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


@app.route('/image2image', methods=['POST'])
def image2image():
    """MCP-style server endpoint.

    Expected JSON (application/json) or form data:
      - model: 'gpt' or 'flux' (optional, default 'gpt')
      - prompt: text prompt (optional, default pirate style)
      - image_base64: base64-encoded image data OR
      - image_path: server-local path to an image file

    Returns JSON with generated image paths.
    """
    try:
        # Accept both JSON and form-encoded data
        if request.is_json:
            payload = request.get_json()
        else:
            payload = request.form.to_dict()

        model = (payload.get('model') or 'gpt').lower()
        prompt = payload.get('prompt') or "update this image to be set in a pirate era"

        image_path = None
        cleanup_tmp = False

        if 'image_base64' in payload and payload.get('image_base64'):
            image_path = save_base64_to_file(payload.get('image_base64'))
            cleanup_tmp = True
        elif 'image_path' in payload and payload.get('image_path'):
            candidate = payload.get('image_path')
            candidate = os.path.expanduser(candidate)
            if not os.path.isabs(candidate):
                candidate = os.path.join(os.getcwd(), candidate)
            if not os.path.isfile(candidate):
                return jsonify({'error': f"image_path not found: {candidate}"}), 400
            image_path = candidate
        else:
            return jsonify({'error': "No image provided. Please provide 'image_base64' or 'image_path'."}), 400

        saved = call_foundry_edit(image_path, prompt, model=model)

        # cleanup temp file if one was created
        if cleanup_tmp and image_path and os.path.exists(image_path):
            try:
                os.unlink(image_path)
            except Exception:
                pass

        return jsonify({'generated': saved})

    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({'error': str(e), 'trace': tb}), 500


if __name__ == '__main__':
    # Run a simple development server for local testing.
    app.run(host='0.0.0.0', port=5000, debug=True)
