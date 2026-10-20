from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from dbtl.backup import backup, restore
from dbtl.core import Instrument, IntegrityError
from dbtl.datasets import replay
from .test_datasets import dataset_fixture


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = Instrument(self.root / "state")
        self.parts, self.imported, _, _, self.dataset = dataset_fixture(self.db, self.root)
        self.archive = self.root / "backup.zip"

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_roundtrip_preserves_records_bytes_and_replay(self):
        saved = backup(self.db, self.archive)
        report = restore(self.archive, self.root / "restored")
        self.assertTrue(report["audit"]["ok"])
        self.assertEqual(saved["sha256"], sha256(self.archive.read_bytes()).hexdigest())
        with Instrument(self.root / "restored") as db:
            self.assertEqual(db.versions(), self.db.versions())
            self.assertEqual(replay(db, self.dataset["id"])["result_sha256"], self.dataset["payload"]["result_sha256"])

    def test_existing_destinations_are_not_overwritten(self):
        backup(self.db, self.archive)
        with self.assertRaises(IntegrityError): backup(self.db, self.archive)
        target = self.root / "exists"; target.mkdir(); (target / "keep").write_text("keep")
        with self.assertRaises(IntegrityError): restore(self.archive, target)
        self.assertEqual((target / "keep").read_text(), "keep")

    def test_path_traversal_is_rejected_before_any_extraction(self):
        backup(self.db, self.archive)
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("../outside", "bad")
        with self.assertRaises(IntegrityError): restore(self.archive, self.root / "bad")
        self.assertFalse((self.root / "outside").exists())
        self.assertFalse((self.root / "bad").exists())

    def test_changed_backup_member_fails_digest_check(self):
        backup(self.db, self.archive)
        corrupted = self.root / "changed.zip"
        with zipfile.ZipFile(self.archive) as old, zipfile.ZipFile(corrupted, "w") as new:
            for name in old.namelist():
                new.writestr(name, b"changed" if name == "registry.sqlite" else old.read(name))
        with self.assertRaises(IntegrityError): restore(corrupted, self.root / "bad")
        self.assertFalse((self.root / "bad").exists())

    def test_missing_evidence_prevents_backup(self):
        imported = self.db.get(self.imported["import_version"])
        self.db.objects.path(imported["payload"]["source_digest"]).unlink()
        with self.assertRaises(IntegrityError): backup(self.db, self.archive)
        self.assertFalse(self.archive.exists())

    def test_uncommitted_state_is_not_silently_omitted_from_backup(self):
        with self.db.atomic():
            self.db.put("not-yet-committed", "design", {})
            with self.assertRaises(IntegrityError): backup(self.db, self.archive)
        self.assertFalse(self.archive.exists())


class PackageTests(unittest.TestCase):
    def test_source_package_runs_in_a_clean_directory_without_installed_dependencies(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "code.zip"
            build = subprocess.run([sys.executable, str(source / "tools/package.py"), "--no-history", "--output", str(archive)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            with zipfile.ZipFile(archive) as zipped:
                zipped.extractall(Path(temp) / "extracted")
            extracted = Path(temp) / "extracted/dbtl-evidence"
            manifest = json.loads((extracted / "PACKAGE_MANIFEST.json").read_text())
            for name, expected in manifest["sha256"].items():
                self.assertEqual(sha256((extracted / name).read_bytes()).hexdigest(), expected)
            result = subprocess.run([sys.executable, "-m", "dbtl", "demo", "--output", str(Path(temp) / "demo")], cwd=extracted, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["audit"]["ok"])
