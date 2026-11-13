
import shutil
import subprocess
from pathlib import Path


def run_cpp_tests(project_path, timeout=30):

    project_root = Path(project_path).resolve()

    test_file = project_root / "tests" / "SalaryTest.cpp"
    source_file = project_root / "src" / "Salary.cpp"
    include_dir = project_root / "include"

    # --------------------------------------------------
    # STEP 1: VALIDATE PROJECT FILES
    # --------------------------------------------------

    for file_path in [test_file, source_file]:

        if not file_path.is_file():

            return {
                "status": "ERROR",
                "message": f"Required file not found: {file_path}"
            }

    if not include_dir.is_dir():

        return {
            "status": "ERROR",
            "message": "Include directory not found."
        }

    # --------------------------------------------------
    # STEP 2: CHECK C++ COMPILER
    # --------------------------------------------------

    compiler = shutil.which("g++")

    if not compiler:

        return {
            "status": "ERROR",
            "message": "g++ compiler not found."
        }

    # --------------------------------------------------
    # STEP 3: CREATE BUILD DIRECTORY
    # --------------------------------------------------

    build_dir = project_root / "impactmap_build"
    build_dir.mkdir(exist_ok=True)

    executable = build_dir / "salary_test.exe"

    compile_command = [
        compiler,
        "-std=c++17",
        "-fno-lto",
        f"-I{include_dir}",
        str(test_file),
        str(source_file),
        "-o",
        str(executable)
    ]

    stage = "compilation"

    try:

        # --------------------------------------------------
        # STEP 4: COMPILE C++ TEST
        # --------------------------------------------------

        compile_result = subprocess.run(
            compile_command,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if compile_result.returncode != 0:

            return {
                "status": "COMPILE_FAILED",
                "stage": stage,
                "message": "C++ compilation failed.",
                "compile_errors": compile_result.stderr
            }

        # --------------------------------------------------
        # STEP 5: EXECUTE C++ TEST
        # --------------------------------------------------

        stage = "execution"

        test_result = subprocess.run(
            [str(executable)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if test_result.returncode == 0:

            return {
                "status": "PASSED",
                "stage": stage,
                "message": "All Salary tests passed.",
                "compile_output": compile_result.stdout,
                "test_output": test_result.stdout,
                "test_errors": test_result.stderr,
                "return_code": test_result.returncode
            }

        return {
            "status": "FAILED",
            "stage": stage,
            "message": "Salary tests failed.",
            "test_output": test_result.stdout,
            "test_errors": test_result.stderr,
            "return_code": test_result.returncode
        }

    # --------------------------------------------------
    # STEP 6: HANDLE TIMEOUT
    # --------------------------------------------------

    except subprocess.TimeoutExpired:

        return {
            "status": "TIMEOUT",
            "stage": stage,
            "message": f"Build or test execution exceeded {timeout} seconds."
        }

    # --------------------------------------------------
    # STEP 7: HANDLE WINDOWS EXECUTION POLICY
    # --------------------------------------------------

    except OSError as error:

        if stage == "execution":

            return {
                "status": "EXECUTION_BLOCKED",
                "stage": stage,
                "message": str(error)
            }

        return {
            "status": "ERROR",
            "stage": stage,
            "message": str(error)
        }

    # --------------------------------------------------
    # STEP 8: HANDLE OTHER ERRORS
    # --------------------------------------------------

    except Exception as error:

        return {
            "status": "ERROR",
            "stage": stage,
            "message": str(error)
        }
