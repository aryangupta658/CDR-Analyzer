import hashlib
from pathlib import Path


def calculate_sha256(
    file_path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    """
    Calculates the SHA-256 hash of a file.

    The file is read in 1 MB chunks so large files
    do not need to be loaded completely into memory.
    """

    sha256_object = hashlib.sha256()

    with file_path.open("rb") as file_object:
        while True:
            chunk = file_object.read(
                chunk_size
            )

            if not chunk:
                break

            sha256_object.update(
                chunk
            )

    return sha256_object.hexdigest()