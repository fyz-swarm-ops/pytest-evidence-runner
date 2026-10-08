from __future__ import annotations

import glob
import hashlib
from pathlib import Path

from .models import FileHash


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_files(workdir: Path, patterns: list[str]) -> list[FileHash]:
    """Hash files matching glob patterns relative to workdir."""
    results: list[FileHash] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for match in glob.glob(str(workdir / pattern), recursive=True):
            path = Path(match)
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rel = path.relative_to(workdir).as_posix()
            results.append(FileHash(path=rel, sha256=digest, size_bytes=path.stat().st_size))
    return sorted(results, key=lambda item: item.path)
