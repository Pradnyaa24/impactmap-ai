"""Run tests for a locally uploaded external C++ project through GitHub Actions."""
import io
import json
import os
import time
import uuid
import zipfile
import urllib.request
import urllib.error
from pathlib import Path

from dotenv import load_dotenv
from modules.github_actions_runner import (
    API_BASE,
    github_headers,
    github_request,
    get_failed_job_details,
    extract_test_statuses,
)

load_dotenv()

MAX_UPLOAD_BYTES = 90 * 1024 * 1024
IGNORED_DIRS = {
    ".git", ".svn", ".hg", "venv", "venv312", ".venv",
    "__pycache__", "node_modules", "build", "cmake-build-debug",
    "cmake-build-release", "dist", ".idea", ".vs",
}


def _make_project_zip(project_root):
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise ValueError("External project folder does not exist.")

    buffer = io.BytesIO()
    total_uncompressed = 0
    count = 0

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in IGNORED_DIRS for part in relative.parts):
                continue
            if path.is_symlink():
                continue
            size = path.stat().st_size
            total_uncompressed += size
            if total_uncompressed > 400 * 1024 * 1024:
                raise ValueError("External project exceeds the 400 MB packaged file limit.")
            archive.write(path, relative.as_posix())
            count += 1
            if count > 10000:
                raise ValueError("External project contains more than 10,000 files.")

    payload = buffer.getvalue()
    if not payload:
        raise ValueError("The external project folder is empty.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError("Compressed project ZIP exceeds GitHub's 90 MB upload limit.")
    return payload


def _upload_release_asset(release_id, payload, token, request_id):
    url = (
        f"https://uploads.github.com/repos/Pradnyaa24/impactmap-ai/"
        f"releases/{release_id}/assets?name=impactmap-{request_id}.zip"
    )
    headers = github_headers(token)
    headers["Content-Type"] = "application/zip"
    request = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_release_asset(asset_id, token):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    url = f"{API_BASE}/releases/assets/{asset_id}"
    request = urllib.request.Request(
        url,
        headers={
            **github_headers(token),
            "Accept": "application/octet-stream",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise
        redirect_url = error.headers.get("Location")
        if not redirect_url:
            raise RuntimeError("GitHub did not provide the release asset download URL.")
        with urllib.request.urlopen(
            urllib.request.Request(redirect_url, method="GET"),
            timeout=120,
        ) as response:
            return response.read()


def run_external_cpp_tests(
    project_root,
    proposed_code,
    source_file,
    test_files=None,
    include_dir="include",
    project_name="External C++ Project",
    generated_test_code="",
    timeout=300,
    poll_interval=5,
):
    """Package an external project, upload it as a temporary release asset and run it."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"status": "ERROR", "message": "GITHUB_TOKEN is missing from .env.", "run_url": None}

    release_id = None
    request_id = uuid.uuid4().hex
    tests = list(test_files or [])

    try:
        root = Path(project_root).resolve()
        source = Path(source_file)
        if source.is_absolute():
            source = source.resolve().relative_to(root)
        source = source.as_posix()
        if not source.lower().endswith((".cpp", ".cc", ".cxx")):
            raise ValueError("Selected source must be a C++ source file.")
        if not (root / source).is_file():
            raise ValueError(f"Selected source file does not exist: {source}")

        normalized_tests = []
        for item in tests:
            candidate = Path(item)
            if candidate.is_absolute():
                candidate = candidate.resolve().relative_to(root)
            candidate = candidate.as_posix()
            if (root / candidate).is_file() and candidate.lower().endswith((".cpp", ".cc", ".cxx")):
                normalized_tests.append(candidate)

        inc = Path(include_dir)
        if inc.is_absolute():
            inc = inc.resolve().relative_to(root)
        inc = inc.as_posix()
        if not (root / inc).is_dir():
            inc = "."

        payload = _make_project_zip(root)

        release = github_request(
            f"{API_BASE}/releases",
            method="POST",
            data={
                "tag_name": f"impactmap-external-{request_id}",
                "name": f"Temporary ImpactMap upload {request_id}",
                "draft": True,
                "prerelease": True,
            },
            token=token,
        )
        release_id = release["id"]

        asset = _upload_release_asset(release_id, payload, token, request_id)
        asset_id = asset["id"]

        workflow_url = f"{API_BASE}/actions/workflows/external-cpp-tests.yml/dispatches"
        github_request(
            workflow_url,
            method="POST",
            data={
                "ref": "main",
                "inputs": {
                    "request_id": request_id,
                    "project_name": str(project_name)[:100],
                    "release_id": str(release_id),
                    "asset_id": str(asset_id),
                    "source_file": source,
                    "include_dir": inc,
                    "test_files": "\n".join(normalized_tests),
                    "proposed_code": proposed_code,
                    "generated_test_code": generated_test_code or "",
                },
            },
            token=token,
        )

        expected_title = f"ImpactMap External C++ Tests - {request_id}"
        runs_url = (
            f"{API_BASE}/actions/workflows/external-cpp-tests.yml/runs"
            f"?branch=main&event=workflow_dispatch&per_page=20"
        )
        started = time.time()
        matching = None
        while time.time() - started < timeout:
            data = github_request(runs_url, token=token)
            matching = next(
                (run for run in data.get("workflow_runs", [])
                 if run.get("display_title") == expected_title),
                None,
            )
            if matching and matching.get("status") == "completed":
                break
            time.sleep(poll_interval)

        if not matching or matching.get("status") != "completed":
            return {
                "status": "TIMEOUT",
                "message": "External C++ workflow is still running. The temporary upload was retained so the workflow can finish.",
                "run_url": matching.get("html_url") if matching else None,
                "existing_test_status": "UNKNOWN",
                "generated_test_status": "UNKNOWN",
            }

        run_url = matching.get("html_url")
        conclusion = matching.get("conclusion")
        logs = get_failed_job_details(matching["id"], token) if conclusion != "success" else ""
        existing_status, generated_status = extract_test_statuses(logs) if logs else (
            "PASSED" if normalized_tests else "NOT_AVAILABLE",
            "PASSED" if generated_test_code else "NOT_GENERATED",
        )
        github_request(f"{API_BASE}/releases/{release_id}", method="DELETE", token=token)
        release_id = None

        return {
            "status": "PASSED" if conclusion == "success" else "FAILED",
            "existing_test_status": existing_status,
            "generated_test_status": generated_status,
            "message": (
                "External C++ project tests completed successfully."
                if conclusion == "success"
                else f"External C++ tests failed.\n\n{logs}"
            ),
            "run_url": run_url,
        }

    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        return {
            "status": "ERROR",
            "message": f"GitHub API error HTTP {error.code}: {detail}",
            "run_url": None,
            "existing_test_status": "UNKNOWN",
            "generated_test_status": "UNKNOWN",
        }
    except Exception as error:
        return {
            "status": "ERROR",
            "message": str(error),
            "run_url": None,
            "existing_test_status": "UNKNOWN",
            "generated_test_status": "UNKNOWN",
        }
