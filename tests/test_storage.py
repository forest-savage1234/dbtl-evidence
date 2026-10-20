from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Instrument(Path(self.temp.name) / "registry")
        self.source = Path(self.temp.name) / "raw.bin"
        self.source.write_bytes(bytes(range(256)) * 1024)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_copy_is_exact_deduplicated_and_independent_of_source(self):
        key = self.db.objects.add(self.source)
        self.assertEqual(self.db.objects.add(self.source), key)
        self.source.unlink()
        self.assertEqual(self.db.objects.verify(key).stat().st_size, 256 * 1024)
        self.assertEqual(len(list(self.db.objects.root.iterdir())), 1)

    def test_corrupted_existing_object_is_not_silently_overwritten(self):
        key = self.db.objects.add(self.source)
        self.db.objects.path(key).write_bytes(b"bad")
        with self.assertRaises(IntegrityError):
            self.db.objects.add(self.source)
        self.assertEqual(self.db.objects.path(key).read_bytes(), b"bad")

    def test_missing_or_changed_evidence_fails_audit_and_registration(self):
        key = self.db.objects.add(self.source)
        self.db.put("raw", "design", {}, artifacts=[key])
        self.db.objects.path(key).unlink()
        self.assertFalse(self.db.verify()["ok"])
        with self.assertRaises(IntegrityError):
            self.db.put("next", "design", {}, artifacts=[key])

    def test_paths_and_symlinks_are_rejected(self):
        with self.assertRaises(IntegrityError):
            self.db.objects.path("../raw.bin")
        key = "a" * 64
        self.db.objects.root.joinpath(key).symlink_to(self.source)
        with self.assertRaises(IntegrityError):
            self.db.objects.verify(key)

    def test_registered_artifact_audits_clean(self):
        key = self.db.objects.add(self.source)
        self.db.put("raw", "design", {}, artifacts=[key])
        report = self.db.verify()
        self.assertTrue(report["ok"])
        self.assertEqual(report["artifact_count"], 1)
