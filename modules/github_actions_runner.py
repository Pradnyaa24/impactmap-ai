
import os
import json
import time
import uuid
import re
import urllib.request
import urllib.error

from dotenv import load_dotenv


load_dotenv()

GITHUB_OWNER = "Pradnyaa24"
GITHUB_REPO = "impactmap-ai"
WORKFLOW_FILE = "cpp-tests.yml"
BRANCH = "main"

API_BASE = (
    f"https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}"
)


def github_request(url, method="GET", data=None, token=None):
    """Send an authenticated request to the GitHub API."""

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    }

    body = None

    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method
    )

    with urllib.request.urlopen(request, timeout=30) as response:

        response_body = response.read().decode("utf-8")

        if response_body:
            return json.loads(response_body)

        return None


def validate_repo_path(path, field_name):
    """
    Validate that a path is relative to the GitHub repository.
    Prevent absolute paths and directory traversal.
    """

    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"{field_name} cannot be empty.")

    path = path.strip().replace("\\", "/")

    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(f"{field_name} must be repository-relative.")

    parts = path.split("/")

    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"Invalid {field_name}: {path}")

    return path


def run_github_cpp_tests(
    proposed_code,
    source_file="sample_projects/EmployeeManagementSystem/src/Salary.cpp",
    test_files=None,
    include_dir="sample_projects/EmployeeManagementSystem/include",
    project_name="Employee Management System",
    timeout=180,
    poll_interval=5
):
    """
    Submit proposed C++ code and project paths to GitHub Actions.

    All paths must refer to files already committed to the GitHub repository.

    Returns:
        {
            "status": "...",
            "message": "...",
            "run_url": "..."
        }
    """

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        return {
            "status": "ERROR",
            "message": "GITHUB_TOKEN is missing. Check your .env file.",
            "run_url": None
        }

    if not proposed_code or not proposed_code.strip():
        return {
            "status": "ERROR",
            "message": "Proposed C++ code cannot be empty.",
            "run_url": None
        }

    try:

        source_file = validate_repo_path(
            source_file,
            "Source file"
        )

        include_dir = validate_repo_path(
            include_dir,
            "Include directory"
        )

        if test_files is None:
            test_files = [
                "sample_projects/EmployeeManagementSystem/tests/SalaryTest.cpp"
            ]

        if isinstance(test_files, str):
            test_files = [
                path.strip()
                for path in test_files.splitlines()
                if path.strip()
            ]

        if not test_files:
            raise ValueError("At least one C++ test file is required.")

        test_files = [
            validate_repo_path(path, "Test file")
            for path in test_files
        ]

        if len(test_files) > 20:
            raise ValueError("Maximum 20 test files are supported.")

        if not project_name or not project_name.strip():
            raise ValueError("Project name cannot be empty.")

    except ValueError as error:

        return {
            "status": "ERROR",
            "message": str(error),
            "run_url": None
        }

    request_id = uuid.uuid4().hex

    expected_title = f"ImpactMap AI C++ Tests - {request_id}"

    workflow_url = (
        f"{API_BASE}/actions/workflows/"
        f"{WORKFLOW_FILE}/dispatches"
    )

    runs_url = (
        f"{API_BASE}/actions/workflows/"
        f"{WORKFLOW_FILE}/runs"
        f"?branch={BRANCH}&event=workflow_dispatch&per_page=20"
    )

    dispatch_payload = {
        "ref": BRANCH,
        "inputs": {
            "proposed_code": proposed_code,
            "source_file": source_file,
            "test_files": "\n".join(test_files),
            "include_dir": include_dir,
            "project_name": project_name,
            "request_id": request_id
        }
    }

    try:

        # Submit the project details and proposed code.
        github_request(
            workflow_url,
            method="POST",
            data=dispatch_payload,
            token=token
        )

        start_time = time.time()

        # Wait for the matching workflow run.
        while time.time() - start_time < timeout:

            response = github_request(
                runs_url,
                token=token
            )

            workflow_runs = response.get("workflow_runs", [])

            matching_run = next(
                (
                    run for run in workflow_runs
                    if run.get("display_title") == expected_title
                ),
                None
            )

            if matching_run:

                run_url = matching_run.get("html_url")

                if matching_run.get("status") == "completed":

                    conclusion = matching_run.get("conclusion")

                    if conclusion == "success":

                        return {
                            "status": "PASSED",
                            "message": (
                                "Proposed C++ code passed "
                                "GitHub Actions tests."
                            ),
                            "run_url": run_url
                        }

                    return {
                        "status": "FAILED",
                        "message": (
                            "GitHub Actions tests failed. "
                            f"Workflow conclusion: {conclusion}"
                        ),
                        "run_url": run_url
                    }

            time.sleep(poll_interval)

        return {
            "status": "TIMEOUT",
            "message": (
                "GitHub Actions did not finish within "
                f"{timeout} seconds. Check the Actions page."
            ),
            "run_url": None
        }

    except urllib.error.HTTPError as error:

        details = error.read().decode(
            "utf-8",
            errors="replace"
        )

        return {
            "status": "ERROR",
            "message": (
                f"GitHub API error: HTTP {error.code}. {details}"
            ),
            "run_url": None
        }

    except Exception as error:

        return {
            "status": "ERROR",
            "message": f"GitHub testing error: {error}",
            "run_url": None
        }
