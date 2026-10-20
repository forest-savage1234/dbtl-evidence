"""Local content-addressed bytes; large files stay outside SQL rows."""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import re
import tempfile

from .core import IntegrityError


class ObjectStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise IntegrityError("Artifact key must be a lowercase SHA-256 digest")
        path = self.root / key
        if path.is_symlink():
            raise IntegrityError("Artifact symlinks are forbidden")
        return path

    def verify(self, key: str) -> Path:
        path = self.path(key)
        try:
            with path.open("rb") as stream:
                h = sha256()
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
        except OSError as exc:
            raise IntegrityError(f"Artifact unavailable: {key}") from exc
        if h.hexdigest() != key:
            raise IntegrityError(f"Artifact bytes changed: {key}")
        return path

    def add(self, source: str | Path) -> str:
        source = Path(source)
        before = source.stat()
        if not source.is_file():
            raise IntegrityError("Evidence source must be a regular file")
        fd, temporary = tempfile.mkstemp(prefix="capture-", dir=self.root)
        temporary = Path(temporary)
        try:
            h = sha256()
            with os.fdopen(fd, "wb") as output, source.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    output.write(block)
                    h.update(block)
                output.flush()
                os.fsync(output.fileno())
            after = source.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise IntegrityError("Source changed during capture; retry after acquisition finishes")
            key = h.hexdigest()
            target = self.path(key)
            try:
                os.link(temporary, target)
            except FileExistsError:
                self.verify(key)
            self.verify(key)
            if os.name == "posix":
                descriptor = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            return key
        finally:
            temporary.unlink(missing_ok=True)
