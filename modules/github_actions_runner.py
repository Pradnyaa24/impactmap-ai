
import os
import json
import time
import uuid
import re
import io
import zipfile
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


def github_headers(token):
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    }


def github_request(url, method="GET", data=None, token=None):
    """Send a GitHub API request and return JSON."""

    headers = github_headers(token)
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



def github_request_bytes(url, token):
    """
    Download GitHub Actions job logs.

    First authenticate with the GitHub API.
    Then follow its temporary redirect without forwarding
    the GitHub authorization token to external storage.
    """

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(
            self,
            req,
            fp,
            code,
            msg,
            headers,
            newurl
        ):
            return None

    request = urllib.request.Request(
        url,
        headers=github_headers(token),
        method="GET"
    )

    opener = urllib.request.build_opener(
        NoRedirectHandler
    )

    try:
        with opener.open(request, timeout=60) as response:
            return response.read()

    except urllib.error.HTTPError as error:

        # GitHub normally redirects log downloads to temporary storage.
        if error.code in (301, 302, 303, 307, 308):

            redirect_url = error.headers.get("Location")

            if not redirect_url:
                raise RuntimeError(
                    "GitHub returned a log redirect without a download URL."
                )

            # Do not send GitHub's token to the external storage URL.
            download_request = urllib.request.Request(
                redirect_url,
                method="GET"
            )

            with urllib.request.urlopen(
                download_request,
                timeout=60
            ) as response:
                return response.read()

        raise


    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def validate_repo_path(path, field_name):
    """Validate that a path is relative to the GitHub repository."""

    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"{field_name} cannot be empty.")

    path = path.strip().replace("\\", "/")

    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(f"{field_name} must be repository-relative.")

    parts = path.split("/")

    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"Invalid {field_name}: {path}")

    return path


def classify_failure(log_text):
    """Identify the likely category of a C++ build or test failure."""

    text = log_text.lower()

    if (
        "undefined reference" in text
        or "multiple definition" in text
        or "collect2: error" in text
        or "ld returned" in text
    ):
        return "LINKING ERROR"

    if (
        "fatal error:" in text
        or re.search(r"\berror:.*", text)
        or "no such file or directory" in text
    ):
        return "COMPILATION ERROR"

    if (
        "generated_test_failure" in text
        or "assertion `" in text
        or "assertion '" in text
        or "assertion failed" in text
        or "assert(" in text
    ):
        return "UNIT TEST FAILURE"

    if (
        "segmentation fault" in text
        or "core dumped" in text
        or "terminate called" in text
        or "runtime error" in text
        or "aborted" in text
    ):
        return "RUNTIME ERROR"

    return "BUILD OR WORKFLOW FAILURE"


def extract_relevant_log_lines(log_text, max_lines=12):
    """Extract useful compiler, linker, assertion and runtime messages."""

    patterns = [
        r"fatal error:",
        r"\berror:",
        r"undefined reference",
        r"multiple definition",
        r"collect2: error",
        r"ld returned",
        r"generated_test_failure",
        r"generated_test_passed",
        r"baseline_reference",
        r"assertion.*failed",
        r"assertion [`']",
        r"segmentation fault",
        r"core dumped",
        r"terminate called",
        r"runtime error",
        r"aborted",
        r"process completed with exit code",
        r"make: \*\*\*",
    ]

    lines = log_text.splitlines()
    findings = []

    for index, line in enumerate(lines):
        if any(
            re.search(pattern, line, re.IGNORECASE)
            for pattern in patterns
        ):
            cleaned = line.strip()

            if cleaned and cleaned not in findings:
                findings.append(cleaned)

            if len(findings) >= max_lines:
                break

    return findings




def get_failed_job_details(run_id, token):
    """Retrieve failed job steps and analyze ZIP or plain-text logs."""

    jobs_url = (
        f"{API_BASE}/actions/runs/{run_id}/jobs"
        "?per_page=100"
    )

    try:
        response = github_request(
            jobs_url,
            token=token
        )

        jobs = response.get("jobs", [])

    except Exception as error:
        return (
            "Could not retrieve job details from GitHub. "
            f"Reason: {error}"
        )

    failed_jobs = [
        job for job in jobs
        if job.get("conclusion") not in ("success", None)
    ]

    if not failed_jobs:
        return (
            "GitHub Actions reported a failure, but no failed job "
            "details were returned."
        )

    report = []

    for job in failed_jobs:

        job_name = job.get("name", "Unknown job")
        report.append(f"Failed job: {job_name}")

        failed_steps = [
            step for step in job.get("steps", [])
            if step.get("conclusion") not in ("success", None)
        ]

        if failed_steps:
            report.append("Failed step(s):")

            for step in failed_steps:
                report.append(
                    f"- {step.get('name', 'Unknown step')} "
                    f"({step.get('conclusion', 'unknown')})"
                )

        job_id = job.get("id")

        if not job_id:
            report.append("Job ID was not returned by GitHub.")
            continue

        logs_url = f"{API_BASE}/actions/jobs/{job_id}/logs"

        try:
            log_data = github_request_bytes(
                logs_url,
                token
            )

            if not log_data:
                report.append("GitHub returned an empty log response.")
                continue

            if not isinstance(log_data, bytes):
                report.append("Invalid log response format.")
                continue

            archive_stream = io.BytesIO(log_data)

            # Handle ZIP archive responses.
            if zipfile.is_zipfile(archive_stream):

                archive_stream.seek(0)

                with zipfile.ZipFile(archive_stream) as archive:

                    all_log_text = []

                    for filename in archive.namelist():

                        if filename.lower().endswith(".txt"):
                            try:
                                content = archive.read(filename).decode(
                                    "utf-8-sig",
                                    errors="replace"
                                )

                                all_log_text.append(content)

                            except Exception:
                                continue

                    combined_logs = "\n".join(all_log_text)

            # Handle plain-text responses.
            else:
                combined_logs = log_data.decode(
                    "utf-8-sig",
                    errors="replace"
                )

            if not combined_logs.strip():
                report.append("No readable job logs were found.")
                continue

            report.append("Job logs retrieved successfully.")

            failure_category = classify_failure(combined_logs)

            report.append(
                f"Detected failure category: {failure_category}"
            )

            findings = extract_relevant_log_lines(
                combined_logs
            )

            if findings:
                report.append("Relevant error details:")

                for finding in findings:
                    report.append(f"- {finding}")
            else:
                report.append(
                    "No specific compiler or test error pattern "
                    "was found in the available logs."
                )

        except Exception as error:
            report.append(
                f"Could not download or process job logs: {error}"
            )

    return "\n".join(report)



def run_github_cpp_tests(
    proposed_code,
    source_file="sample_projects/EmployeeManagementSystem/src/Salary.cpp",
    test_files=None,
    include_dir="sample_projects/EmployeeManagementSystem/include",
    project_name="Employee Management System",
    generated_test_code="",
    timeout=180,
    poll_interval=5
):
    """
    Submit proposed C++ code, project paths and optional generated tests
    to GitHub Actions.

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

        if generated_test_code and len(generated_test_code) > 30000:
            raise ValueError("Generated test code exceeds the 30,000 character limit.")

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
        f"{API_BASE}/actions/workflows/{WORKFLOW_FILE}/runs"
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
            "request_id": request_id,
            "generated_test_code": generated_test_code or ""
        }
    }

    try:
        github_request(
            workflow_url,
            method="POST",
            data=dispatch_payload,
            token=token
        )

        start_time = time.time()

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

                    run_id = matching_run.get("id")

                    failure_details = get_failed_job_details(
                        run_id,
                        token
                    )

                    message = (
                        "GitHub Actions tests failed.\n\n"
                        f"Workflow conclusion: {conclusion}\n\n"
                        "Failure Analysis:\n"
                        f"{failure_details}"
                    )

                    return {
                        "status": "FAILED",
                        "message": message,
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
