"""Immutable version records; SQLite is a local transactional reference backend.

The dependency graph represents evidence derivation, not metabolic causality.
Dependencies are sealed inside each hashed record, not mutable side tables.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Iterator
from uuid import uuid4


class IntegrityError(ValueError):
    """Evidence is malformed, unavailable, changed, or inconsistent."""


class ConflictError(IntegrityError):
    """An optimistic revision precondition failed."""


def canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise IntegrityError("Record must be finite, JSON-serializable data") from exc


def digest(value: object) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value):
        raise IntegrityError("Invalid identifier; use 1–128 ASCII letters, digits, _, ., :, -")
    return value


KINDS = frozenset({"design", "strain", "activity", "protocol", "culture", "sample",
                   "calibration", "measurement", "import", "cohort", "policy",
                   "dataset", "decision", "review", "model", "assessment", "pool", "pool_snapshot",
                   "availability", "watch", "watch_review", "quantity", "quantity_result"})

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO metadata VALUES ('schema_version','1');
CREATE TABLE IF NOT EXISTS entities(
    id TEXT PRIMARY KEY, kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS versions(
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(id),
    revision INTEGER NOT NULL CHECK(revision > 0),
    previous_id TEXT REFERENCES versions(id),
    record TEXT NOT NULL CHECK(json_valid(record)),
    sha256 TEXT NOT NULL,
    UNIQUE(entity_id, revision)
);
CREATE INDEX IF NOT EXISTS versions_entity ON versions(entity_id, revision DESC);
CREATE INDEX IF NOT EXISTS measurement_acquisition ON versions(
 json_extract(record,'$.payload.sample_version'),
 json_extract(record,'$.payload.analyte_id'),
 json_extract(record,'$.payload.run_id'),
 json_extract(record,'$.payload.technical_replicate_id')
) WHERE json_extract(record,'$.kind')='measurement';
CREATE VIEW IF NOT EXISTS heads AS
 SELECT v.* FROM versions v
 WHERE NOT EXISTS (SELECT 1 FROM versions n
                   WHERE n.entity_id=v.entity_id AND n.revision>v.revision);
CREATE VIEW IF NOT EXISTS edges AS
 SELECT v.id AS dependent_id,
        json_extract(j.value,'$.version_id') AS source_id,
        json_extract(j.value,'$.role') AS role
 FROM versions v, json_each(v.record,'$.dependencies') j;
CREATE TRIGGER IF NOT EXISTS versions_no_update BEFORE UPDATE ON versions
 BEGIN SELECT RAISE(ABORT, 'Versions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS versions_no_delete BEFORE DELETE ON versions
 BEGIN SELECT RAISE(ABORT, 'Versions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS entities_no_update BEFORE UPDATE ON entities
 BEGIN SELECT RAISE(ABORT, 'Entity identity is immutable'); END;
CREATE TRIGGER IF NOT EXISTS entities_no_delete BEFORE DELETE ON entities
 BEGIN SELECT RAISE(ABORT, 'Entity identity is immutable'); END;
"""


class Instrument:
    def __init__(self, root: str | Path):
        if sqlite3.sqlite_version_info < (3, 38, 0):
            raise IntegrityError("SQLite >=3.38 with JSON support is required")
        from .storage import ObjectStore
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        database = self.root / "registry.sqlite"
        existing = database.exists()
        if existing:
            try:
                with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as probe:
                    metadata = probe.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
                    if metadata is None or metadata[0] != "1":
                        raise IntegrityError("Unsupported storage schema; refused before modifying it")
                    tables = {r[0] for r in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if not {"metadata", "versions", "entities"} <= tables:
                        raise IntegrityError("Incomplete registry schema; refused before modifying it")
            except sqlite3.Error as exc:
                raise IntegrityError("Existing file is not a supported DBTL registry") from exc
        self.objects = ObjectStore(self.root / "objects")
        self.conn = sqlite3.connect(database, isolation_level=None,
                                    timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        if not existing:
            self.conn.executescript(SCHEMA)
        version = self.conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        if version[0] != "1":
            self.conn.close()
            raise IntegrityError("Unsupported storage schema; no automatic destructive migration")

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @contextmanager
    def atomic(self) -> Iterator[None]:
        nested = self.conn.in_transaction
        savepoint = "s_" + uuid4().hex
        self.conn.execute(f"SAVEPOINT {savepoint}" if nested else "BEGIN IMMEDIATE")
        try:
            yield
            self.conn.execute(f"RELEASE {savepoint}" if nested else "COMMIT")
        except BaseException:
            if nested:
                self.conn.execute(f"ROLLBACK TO {savepoint}")
                self.conn.execute(f"RELEASE {savepoint}")
            else:
                self.conn.execute("ROLLBACK")
            raise

    def get(self, version_id: str) -> dict:
        row = self.conn.execute("SELECT * FROM versions WHERE id=?", (version_id,)).fetchone()
        if row is None:
            raise IntegrityError(f"Unknown version: {version_id}")
        record = json.loads(row["record"])
        if digest(record) != row["sha256"]:
            raise IntegrityError(f"Record digest mismatch: {version_id}")
        if (record["id"], record["entity_id"], record["revision"], record["previous_id"]) != (
                row["id"], row["entity_id"], row["revision"], row["previous_id"]):
            raise IntegrityError(f"Record index mismatch: {version_id}")
        return record

    def latest(self, entity_id: str) -> dict:
        row = self.conn.execute("SELECT id FROM heads WHERE entity_id=?", (entity_id,)).fetchone()
        if row is None:
            raise IntegrityError(f"Unknown entity: {entity_id}")
        return self.get(row["id"])

    def versions(self, kind: str | None = None, heads_only: bool = False) -> list[dict]:
        table = "heads" if heads_only else "versions"
        sql = f"SELECT v.id FROM {table} v JOIN entities e ON e.id=v.entity_id"
        params = ()
        if kind is not None:
            sql += " WHERE e.kind=?"
            params = (kind,)
        sql += " ORDER BY v.entity_id,v.revision"
        return [self.get(row["id"]) for row in self.conn.execute(sql, params)]

    def put(self, entity_id: str, kind: str, payload: dict, *,
            dependencies: list[dict] | None = None, artifacts: list[str] | None = None,
            expected: str | None = None, actor: str = "local-operator",
            reason: str = "initial capture") -> dict:
        identifier(entity_id)
        if kind not in KINDS or not isinstance(payload, dict):
            raise IntegrityError("Unknown kind or non-object payload")
        if not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or not reason.strip():
            raise IntegrityError("Actor and reason are required assertions")
        deps = dependencies or []
        for dep in deps:
            if not isinstance(dep, dict) or set(dep) != {"role", "version_id"}:
                raise IntegrityError("Dependencies need exactly role and version_id")
            identifier(dep["role"])
            identifier(dep["version_id"])
        deps = sorted(deps, key=lambda x: (x["role"], x["version_id"]))
        if len({(d["role"], d["version_id"]) for d in deps}) != len(deps):
            raise IntegrityError("Duplicate dependency")
        artifacts = sorted(set(artifacts or []))
        canonical(payload)
        with self.atomic():
            row = self.conn.execute("SELECT id FROM heads WHERE entity_id=?", (entity_id,)).fetchone()
            previous = self.get(row["id"]) if row else None
            if expected != (previous["id"] if previous else None):
                raise ConflictError("Revision must name the exact current version")
            if previous and previous["kind"] != kind:
                raise ConflictError("An entity cannot change kind")
            for dep in deps:
                self.get(dep["version_id"])
            for key in artifacts:
                self.objects.verify(key)
            self.validate(kind, payload, deps, artifacts, entity_id)
            record = {"id": "v_" + uuid4().hex, "entity_id": entity_id, "kind": kind,
                      "revision": previous["revision"] + 1 if previous else 1,
                      "previous_id": previous["id"] if previous else None,
                      "payload": payload, "dependencies": deps, "artifacts": artifacts,
                      "actor": actor, "reason": reason,
                      "recorded_at": datetime.now(timezone.utc).isoformat(), "schema": 1}
            self.conn.execute("INSERT OR IGNORE INTO entities VALUES (?,?)", (entity_id, kind))
            self.conn.execute("INSERT INTO versions VALUES (?,?,?,?,?,?)",
                              (record["id"], entity_id, record["revision"], record["previous_id"],
                               canonical(record), digest(record)))
            return json.loads(canonical(record))

    def validate(self, kind: str, payload: dict, deps: list[dict], artifacts: list[str], entity_id: str):
        from .domain import validate
        validate(self, kind, payload, deps, artifacts, entity_id)

    def capture(self, entity_id: str, kind: str, payload: dict, **kwargs) -> dict:
        """Populate known typed references without inferring biological metadata."""
        from .domain import dependencies
        return self.put(entity_id, kind, payload, dependencies=dependencies(kind, payload), **kwargs)

    def verify(self) -> dict:
        from .audit import audit
        return audit(self)

    def _basic_verify(self) -> dict:
        errors = []
        artifacts = set()
        check = self.conn.execute("PRAGMA quick_check").fetchone()[0]
        if check != "ok":
            errors.append(check)
        for row in self.conn.execute("SELECT id FROM versions ORDER BY rowid"):
            try:
                record = self.get(row[0])
                for dep in record["dependencies"]:
                    self.get(dep["version_id"])
                for key in record["artifacts"]:
                    if key not in artifacts:
                        self.objects.verify(key)
                        artifacts.add(key)
            except (IntegrityError, KeyError, ValueError) as exc:
                errors.append(str(exc))
        return {"ok": not errors, "version_count": self.conn.execute("SELECT count(*) FROM versions").fetchone()[0],
                "artifact_count": len(artifacts), "errors": errors}
