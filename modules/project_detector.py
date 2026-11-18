import re
from pathlib import Path


CPP_SOURCE_EXTENSIONS = {".cpp", ".cc", ".cxx", ".c"}
CPP_HEADER_EXTENSIONS = {".h", ".hh", ".hpp", ".hxx"}

IGNORED_DIRECTORIES = {
    ".git", ".svn", ".hg",
    "build", "cmake-build-debug", "cmake-build-release",
    "debug", "release",
    "node_modules", "venv", ".venv",
    "__pycache__", ".idea", ".vscode"
}

TEST_DIRECTORY_NAMES = {
    "test", "tests", "unittest", "unittests",
    "unit_tests", "integration_tests"
}

BUILD_FILES = {
    "CMakeLists.txt": "CMake",
    "Makefile": "Make",
    "makefile": "Make",
    "GNUmakefile": "Make",
    "meson.build": "Meson",
    "BUILD": "Bazel",
    "BUILD.bazel": "Bazel",
    "WORKSPACE": "Bazel",
    "WORKSPACE.bazel": "Bazel"
}


def _is_ignored(path):
    return any(
        part.lower() in IGNORED_DIRECTORIES
        for part in path.parts
    )


def _collect_files(root):
    files = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(root)

        if _is_ignored(relative_path):
            continue

        files.append(path)

    return files


def _contains_project_files(directory):
    if not directory.is_dir():
        return False

    for path in directory.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(directory)

        if _is_ignored(relative_path):
            continue

        if path.suffix.lower() in CPP_SOURCE_EXTENSIONS:
            return True

        if path.name in BUILD_FILES:
            return True

    return False


def _resolve_project_root(project_path):
    root = Path(project_path).resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError(
            f"Project directory does not exist: {root}"
        )

    # Handle ZIP files containing one wrapper directory.
    root_files = _collect_files(root)

    has_root_project_files = any(
        path.suffix.lower() in CPP_SOURCE_EXTENSIONS
        or path.name in BUILD_FILES
        for path in root_files
        if path.parent == root
    )

    child_directories = [
        path for path in root.iterdir()
        if path.is_dir()
        and path.name.lower() not in IGNORED_DIRECTORIES
    ]

    if not has_root_project_files and len(child_directories) == 1:
        child = child_directories[0]

        if _contains_project_files(child):
            return child.resolve()

    return root


def _is_test_file(path, relative_path):
    parts = {
        part.lower()
        for part in relative_path.parts[:-1]
    }

    filename = path.stem.lower()

    return (
        bool(parts.intersection(TEST_DIRECTORY_NAMES))
        or "test" in filename
    )


def _is_main_entry_point(path):
    if path.stem.lower() == "main":
        return True

    try:
        content = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )[:2 * 1024 * 1024]

        return bool(
            re.search(r"\bmain\s*\(", content)
        )

    except OSError:
        return False


def detect_cpp_project_structure(project_path):
    root = _resolve_project_root(project_path)
    files = _collect_files(root)

    source_files = []
    header_files = []
    test_files = []
    entry_points = []
    build_files = []
    source_directories = set()
    include_directories = set()
    test_directories = set()

    for path in files:
        relative_path = path.relative_to(root)
        relative_name = relative_path.as_posix()
        extension = path.suffix.lower()

        if path.name in BUILD_FILES:
            build_files.append(relative_name)

        if extension in CPP_HEADER_EXTENSIONS:
            header_files.append(relative_name)
            include_directories.add(
                relative_path.parent.as_posix()
            )

        elif extension in CPP_SOURCE_EXTENSIONS:

            if _is_test_file(path, relative_path):
                test_files.append(relative_name)
                test_directories.add(
                    relative_path.parent.as_posix()
                )
            else:
                source_files.append(relative_name)
                source_directories.add(
                    relative_path.parent.as_posix()
                )

                if _is_main_entry_point(path):
                    entry_points.append(relative_name)

    detected_build_systems = sorted({
        BUILD_FILES[Path(name).name]
        for name in build_files
    })

    if not detected_build_systems:
        detected_build_systems = ["Unknown / Manual"]

    return {
        "project_root": str(root),
        "total_files": len(files),
        "source_files": sorted(source_files),
        "header_files": sorted(header_files),
        "test_files": sorted(test_files),
        "source_directories": sorted(source_directories),
        "include_directories": sorted(include_directories),
        "test_directories": sorted(test_directories),
        "entry_points": sorted(entry_points),
        "build_files": sorted(build_files),
        "build_systems": detected_build_systems
    }
