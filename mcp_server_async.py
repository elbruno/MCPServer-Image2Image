import os
import uuid
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from mcp.server.fastmcp import FastMCP

# Reuse helper functions from the existing sync server file.
from mcp_server import call_foundry_edit, save_base64_to_file, validate_env


LOG = logging.getLogger("mcp.image2image.async")

# Basic config -- let mcp_server.py control global logging level, but ensure the logger exists
if not logging.getLogger().handlers:
    logging.basicConfig(level=os.getenv("MCP_SERVER_LOGLEVEL", "INFO"))


# Where we persist job records
JOBS_DIR = Path.cwd() / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Lock to protect job file writes
_jobs_lock = threading.Lock()


mcp = FastMCP("Image2ImageAsync")


def _job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def _save_job(job: Dict[str, Any]) -> None:
    path = _job_path(job["job_id"])
    with _jobs_lock:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(job, fh, ensure_ascii=False, indent=2, default=str)


def _load_job(job_id: str) -> Optional[Dict[str, Any]]:
    path = _job_path(job_id)
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _start_job_thread(job: Dict[str, Any]) -> None:
    """Persist job and start a background thread to process it immediately."""
    _save_job(job)
    t = threading.Thread(target=_process_job, args=(job,), daemon=True, name=f"mcp-job-{job['job_id']}")
    t.start()


def _process_job(job: Dict[str, Any]) -> None:
    """Process a single job in its own thread. Updates job status on disk."""
    job_id = job.get("job_id")
    LOG.info("Starting processing job %s", job_id)

    job["status"] = "running"
    job["updated_at"] = datetime.utcnow().isoformat()
    _save_job(job)

    tmp_created = False
    img_path: Optional[str] = None

    try:
        # prepare image
        if job.get("image_base64"):
            img_path = save_base64_to_file(job["image_base64"])
            tmp_created = True
        elif job.get("image_path"):
            candidate = Path(os.path.expanduser(job["image_path"]))
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            if not candidate.is_file():
                raise FileNotFoundError(f"image_path not found: {candidate}")
            img_path = str(candidate)
        else:
            raise ValueError("No image provided")

        # call the existing Foundry edit function with a timeout so the worker doesn't hang
        LOG.debug("Calling call_foundry_edit for job %s image=%s", job_id, img_path)
        result_paths: List[str] = []

        # Timeout in seconds (default 60)
        timeout_seconds = int(os.getenv("IMAGE_JOB_CALL_TIMEOUT", "60"))

        def _call_target():
            nonlocal result_paths
            result_paths = call_foundry_edit(img_path, job.get("prompt", ""), model=job.get("model", "gpt"))

        call_thread = threading.Thread(target=_call_target, daemon=True)
        call_thread.start()
        call_thread.join(timeout=timeout_seconds)
        if call_thread.is_alive():
            raise TimeoutError(f"call_foundry_edit did not complete within {timeout_seconds}s")

        job["status"] = "completed"
        job["result_paths"] = result_paths
        job["updated_at"] = datetime.utcnow().isoformat()
        _save_job(job)
        LOG.info("Job %s completed: %s", job_id, result_paths)

    except Exception as exc:  # capture job failure
        LOG.exception("Job %s failed", job_id)
        job["status"] = "failed"
        job["error"] = str(exc)
        job["updated_at"] = datetime.utcnow().isoformat()
        _save_job(job)

    finally:
        if tmp_created and img_path:
            try:
                Path(img_path).unlink()
                LOG.debug("Removed temporary file for job %s: %s", job_id, img_path)
            except Exception:
                LOG.exception("Failed to remove temporary image file for job %s: %s", job_id, img_path)


# Note: we start a dedicated thread for each job when `image2image_async` is called.


@mcp.tool()
def image2image_async(
    model: str = "gpt",
    prompt: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Dict[str, str]:
    """Start an image2image job and return immediately with a job_id."""
    model = (model or "gpt").lower()
    prompt = prompt or "update this image to be set in a pirate era"

    LOG.info("image2image_async called model=%s prompt=%s image_base64=%s image_path=%s", model, prompt, bool(image_base64), image_path)

    # minimal validation
    if not image_base64 and not image_path:
        raise ValueError("No image provided. Please provide 'image_base64' or 'image_path'.")

    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    job: Dict[str, Any] = {
        "job_id": job_id,
        "created_at": now,
        "updated_at": now,
        "status": "queued",
        "model": model,
        "prompt": prompt,
        "image_base64": image_base64,
        "image_path": image_path,
        "result_paths": [],
        "error": None,
    }

    # persist and start processing immediately in a per-job thread
    _start_job_thread(job)
    LOG.info("Started job %s", job_id)
    return {"job_id": job_id}


@mcp.tool()
def image2image_status(job_id: str) -> Dict[str, Any]:
    """Return job status and results for a given job_id."""
    job = _load_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job not found: {job_id}")
    # Map internal statuses to the user-facing responses required:
    # - If the job is queued or running -> return status 'working'
    # - If completed -> return status 'completed' and include generated path(s)
    # - If failed -> return status 'failed' and include the error
    internal_status = job.get("status")
    if internal_status in ("queued", "running"):
        return {
            "job_id": job.get("job_id"),
            "status": "working",
            "path": None,
            "result_paths": job.get("result_paths", []),
            "error": None,
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        }

    if internal_status == "completed":
        paths = job.get("result_paths", []) or []
        first_path = paths[0] if paths else None
        return {
            "job_id": job.get("job_id"),
            "status": "completed",
            "path": first_path,
            "result_paths": paths,
            "error": None,
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        }

    # fallback (failed or unknown)
    return {
        "job_id": job.get("job_id"),
        "status": "failed",
        "path": None,
        "result_paths": job.get("result_paths", []),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }


@mcp.tool()
def image2image_sync(
    model: str = "gpt",
    prompt: Optional[str] = None,
    image_base64: Optional[str] = None,
    image_path: Optional[str] = None,
) -> List[str]:
    """Synchronous image2image tool (re-implemented here so this server exposes both sync and async tools)."""
    model = (model or "gpt").lower()
    prompt = prompt or "update this image to be set in a pirate era"

    LOG.info("image2image_sync called model=%s prompt=%s image_base64=%s image_path=%s", model, prompt, bool(image_base64), image_path)

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
            LOG.error("image_path not found: %s", candidate)
            raise FileNotFoundError(f"image_path not found: {candidate}")
        img_path = str(candidate)
    else:
        LOG.error("No image provided to image2image_sync tool")
        raise ValueError("No image provided. Please provide 'image_base64' or 'image_path'.")

    try:
        LOG.debug("Calling call_foundry_edit (sync) with image=%s", img_path)
        saved = call_foundry_edit(img_path, prompt, model=model)
        LOG.info("image2image_sync completed, %d files saved", len(saved))
        return saved
    finally:
        if tmp_created and img_path and Path(img_path).exists():
            try:
                Path(img_path).unlink()
                LOG.debug("Removed temporary file: %s", img_path)
            except Exception:
                LOG.exception("Failed to remove temporary image file: %s", img_path)


if __name__ == '__main__':
    # Validate environment and run the MCP server
    validate_env()
    mcp.run()
