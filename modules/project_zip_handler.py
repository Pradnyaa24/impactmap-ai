import io
import shutil
import stat
import uuid
import zipfile

from pathlib import Path, PurePosixPath, PureWindowsPath


MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_BYTES = 500 * 1024 * 1024
MAX_FILES = 10000
MAX_COMPRESSION_RATIO = 200
CHUNK_SIZE = 1024 * 1024

CPP_EXTENSIONS = {
    ".cpp", ".cc", ".cxx", ".c", ".h", ".hh", ".hpp", ".hxx"
}


def _safe_member_path(member_name, destination):
    normalized = member_name.replace("\\", "/")
    posix_path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(normalized)

    if (
        not normalized
        or normalized.startswith("/")
        or windows_path.is_absolute()
        or windows_path.drive
        or ".." in posix_path.parts
    ):
        raise ValueError("ZIP contains an unsafe file path.")

    target = (destination / Path(*posix_path.parts)).resolve()

    try:
        target.relative_to(destination.resolve())
    except ValueError:
        raise ValueError(
            "ZIP contains a path outside the extraction folder."
        )

    return target


def extract_cpp_project_zip(uploaded_file, storage_directory):
    archive_bytes = uploaded_file.getvalue()

    if not archive_bytes:
        raise ValueError("The uploaded ZIP file is empty.")

    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError("ZIP file exceeds the 100 MB upload limit.")

    storage_directory = Path(storage_directory).resolve()
    storage_directory.mkdir(parents=True, exist_ok=True)

    project_id = uuid.uuid4().hex
    destination = storage_directory / project_id
    destination.mkdir(parents=True, exist_ok=False)

    extracted_size = 0
    extracted_files = 0
    seen_paths = set()

    try:
        # Open from memory so upload stream position cannot cause issues.
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            members = archive.infolist()

            if len(members) > MAX_FILES:
                raise ValueError("ZIP contains too many files.")

            for member in members:
                target = _safe_member_path(
                    member.filename,
                    destination
                )

                mode = member.external_attr >> 16
                file_type = stat.S_IFMT(mode)

                if stat.S_ISLNK(mode):
                    raise ValueError(
                        "ZIP symbolic links are not supported."
                    )

                if file_type and file_type not in {
                    stat.S_IFREG,
                    stat.S_IFDIR
                }:
                    raise ValueError(
                        "ZIP contains an unsupported special file."
                    )

                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                if member.flag_bits & 0x1:
                    raise ValueError(
                        "Encrypted ZIP files are not supported."
                    )

                if member.file_size < 0 or member.compress_size < 0:
                    raise ValueError("ZIP contains an invalid file size.")

                if target in seen_paths:
                    raise ValueError(
                        "ZIP contains duplicate file paths."
                    )

                seen_paths.add(target)

                if member.file_size > MAX_EXTRACTED_BYTES:
                    raise ValueError(
                        "An individual ZIP entry exceeds the size limit."
                    )

                if member.file_size > 0:
                    ratio = (
                        member.file_size /
                        max(member.compress_size, 1)
                    )

                    if ratio > MAX_COMPRESSION_RATIO:
                        raise ValueError(
                            "ZIP contains a suspicious compression ratio."
                        )

                target.parent.mkdir(parents=True, exist_ok=True)

                copied = 0

                with archive.open(member, "r") as source:
                    with target.open("wb") as output:
                        while True:
                            chunk = source.read(CHUNK_SIZE)

                            if not chunk:
                                break

                            copied += len(chunk)
                            extracted_size += len(chunk)

                            if copied > member.file_size:
                                raise ValueError(
                                    "ZIP entry exceeded its declared size."
                                )

                            if extracted_size > MAX_EXTRACTED_BYTES:
                                raise ValueError(
                                    "Extracted project exceeds the 500 MB limit."
                                )

                            output.write(chunk)

                if copied != member.file_size:
                    raise ValueError(
                        "ZIP entry size validation failed."
                    )

                extracted_files += 1

                if extracted_files > MAX_FILES:
                    raise ValueError(
                        "ZIP contains too many extracted files."
                    )

        cpp_files = [
            path
            for path in destination.rglob("*")
            if path.is_file()
            and path.suffix.lower() in CPP_EXTENSIONS
        ]

        source_files = [
            path for path in cpp_files
            if path.suffix.lower() in {
                ".cpp", ".cc", ".cxx", ".c"
            }
        ]

        if not source_files:
            raise ValueError(
                "No C++ source files (.cpp, .cc, .cxx or .c) were found."
            )

        return {
            "project_path": str(destination),
            "project_id": project_id,
            "file_count": extracted_files,
            "cpp_file_count": len(cpp_files),
            "cpp_files": [
                path.relative_to(destination).as_posix()
                for path in cpp_files
            ],
        }

    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
