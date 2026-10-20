"""Verified portable state snapshots. Restore never extracts arbitrary ZIP paths."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import tempfile
import zipfile

from . import __version__
from .core import Instrument, IntegrityError, canonical

FORMAT = "dbtl-state-backup:1"
LIMIT = 1024 * 1024 * 1024


def file_hash(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect_archive(archive):
    infos = archive.infolist()
    names = [i.filename for i in infos]
    if len(names) != len(set(names)) or "backup.json" not in names or "registry.sqlite" not in names:
        raise IntegrityError("Backup has missing or duplicate members")
    if sum(i.file_size for i in infos) > LIMIT:
        raise IntegrityError("Backup exceeds the v1 uncompressed-size limit of 1 GiB")
    for info in infos:
        if info.filename not in {"backup.json", "registry.sqlite"} and not re.fullmatch(r"objects/[0-9a-f]{64}", info.filename):
            raise IntegrityError("Unexpected or unsafe backup member")
        if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
            raise IntegrityError("Backup directories/symlinks are not accepted")
    if archive.getinfo("backup.json").file_size > 10 * 1024 * 1024:
        raise IntegrityError("Backup manifest is too large")
    try:
        manifest = json.loads(archive.read("backup.json"))
    except (UnicodeError, ValueError) as exc:
        raise IntegrityError("Invalid backup manifest") from exc
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT or manifest.get("schema") != 1:
        raise IntegrityError("Unsupported backup format/schema")
    members = manifest.get("members")
    if not isinstance(members, dict) or set(members) != set(names) - {"backup.json"}:
        raise IntegrityError("Backup membership differs from manifest")
    for name, expected in members.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise IntegrityError("Invalid backup digest")
        if name.startswith("objects/") and name.split("/")[1] != expected:
            raise IntegrityError("Artifact identity and digest disagree")
    return manifest


def verify_members(archive, manifest, destination=None):
    for name, expected in manifest["members"].items():
        output = None
        if destination is not None:
            target = Path(destination) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            output = target.open("xb")
        h, count = sha256(), 0
        try:
            with archive.open(name) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    count += len(block)
                    if count > LIMIT:
                        raise IntegrityError("Expanded backup member exceeds size limit")
                    h.update(block)
                    if output:
                        output.write(block)
            if h.hexdigest() != expected:
                raise IntegrityError("Backup member digest mismatch: " + name)
        finally:
            if output:
                output.close()


def backup(db, destination):
    if db.conn.in_transaction:
        raise IntegrityError("Finish the current write transaction before taking a committed-state backup")
    destination = Path(destination).resolve()
    if destination.exists():
        raise IntegrityError("Backup destination already exists; choose a new filename")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dbtl-backup-", dir=destination.parent) as staging:
        staging = Path(staging)
        with db.atomic():
            audit = db.verify()
            if not audit["ok"]:
                raise IntegrityError("Backup refused because registry integrity failed")
            snapshot = staging / "registry.sqlite"
            # A second read connection avoids SQLite backup deadlock on a source
            # connection holding an active write transaction. The reserved write
            # lock prevents concurrent registry commits during this snapshot.
            with sqlite3.connect((db.root / "registry.sqlite").as_uri() + "?mode=ro", uri=True) as source:
                with sqlite3.connect(snapshot) as target:
                    source.backup(target)
            artifacts = sorted({key for r in db.versions() for key in r["artifacts"]})
            members = {"registry.sqlite": file_hash(snapshot), **{"objects/" + key: key for key in artifacts}}
            manifest = {"format": FORMAT, "schema": 1, "source_release": __version__,
                        "created_at": datetime.now(timezone.utc).isoformat(), "members": members}
            temporary = staging / "snapshot.zip"
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "registry.sqlite")
                for key in artifacts:
                    archive.write(db.objects.verify(key), "objects/" + key)
                archive.writestr("backup.json", canonical(manifest))
            with zipfile.ZipFile(temporary) as archive:
                verify_members(archive, inspect_archive(archive))
            try:
                os.link(temporary, destination)
            except FileExistsError as exc:
                raise IntegrityError("Backup destination appeared during creation; not overwritten") from exc
    return {"backup": str(destination), "sha256": file_hash(destination), "artifacts": len(artifacts), "format": FORMAT}


def restore(source, destination):
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise IntegrityError("Restore destination must not already exist")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="dbtl-restore-", dir=destination.parent))
    try:
        with zipfile.ZipFile(source) as archive:
            manifest = inspect_archive(archive)
            verify_members(archive, manifest, staging)
        with Instrument(staging) as db:
            audit = db.verify()
            if not audit["ok"]:
                raise IntegrityError("Restored registry failed integrity verification")
        if destination.exists() or destination.is_symlink():
            raise IntegrityError("Restore destination appeared during verification; not overwritten")
        os.rename(staging, destination)
        return {"restored": str(destination), "audit": audit, "format": manifest["format"]}
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise IntegrityError("Backup is damaged or unsupported") from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging)
