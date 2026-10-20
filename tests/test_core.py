import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError, ConflictError, digest


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Instrument(self.temp.name)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_revision_preserves_previous_and_requires_expected_head(self):
        old = self.db.put("design:A", "design", {"name": "A"})
        with self.assertRaises(ConflictError):
            self.db.put("design:A", "design", {"name": "B"})
        new = self.db.put("design:A", "design", {"name": "B"}, expected=old["id"], reason="correction")
        self.assertEqual(self.db.get(old["id"])["payload"]["name"], "A")
        self.assertEqual(new["previous_id"], old["id"])
        with self.assertRaises(ConflictError):
            self.db.put("design:A", "design", {}, expected=old["id"])

    def test_multi_input_lineage_is_not_single_parent(self):
        a = self.db.put("design:A", "design", {})
        b = self.db.put("design:B", "design", {})
        activity = self.db.put("activity:1", "activity", {}, dependencies=[
            {"role": "recipient", "version_id": a["id"]},
            {"role": "donor", "version_id": b["id"]}])
        self.assertEqual(len(activity["dependencies"]), 2)
        self.assertEqual(self.db.conn.execute("SELECT count(*) FROM edges").fetchone()[0], 2)

    def test_unknown_and_duplicate_dependencies_rejected(self):
        with self.assertRaises(IntegrityError):
            self.db.put("a", "design", {}, dependencies=[{"role": "input", "version_id": "missing"}])
        a = self.db.put("a", "design", {})
        dep = {"role": "input", "version_id": a["id"]}
        with self.assertRaises(IntegrityError):
            self.db.put("b", "design", {}, dependencies=[dep, dep])

    def test_sql_write_cannot_overwrite_or_delete_history(self):
        a = self.db.put("a", "design", {})
        for sql in ["UPDATE versions SET sha256='x'", "DELETE FROM versions", "UPDATE entities SET kind='strain'"]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.conn.execute(sql)
        self.assertEqual(self.db.get(a["id"])["payload"], {})

    def test_atomic_batch_rolls_back(self):
        with self.assertRaises(IntegrityError):
            with self.db.atomic():
                self.db.put("a", "design", {})
                self.db.put("bad/id", "design", {})
        self.assertEqual(self.db.versions(), [])

    def test_nan_and_mutated_python_inputs_do_not_change_stored_data(self):
        with self.assertRaises(IntegrityError):
            self.db.put("a", "design", {"x": float("nan")})
        payload = {"x": [1]}
        a = self.db.put("a", "design", payload)
        payload["x"].append(2)
        self.assertEqual(self.db.get(a["id"])["payload"], {"x": [1]})

    def test_audit_finds_direct_tampering_after_trigger_removed(self):
        a = self.db.put("a", "design", {})
        self.db.conn.execute("DROP TRIGGER versions_no_update")
        self.db.conn.execute("UPDATE versions SET record=? WHERE id=?", (json.dumps({**a, "actor": "changed"}), a["id"]))
        self.assertFalse(self.db.verify()["ok"])

    def test_clean_audit_and_kind_conflict(self):
        a = self.db.put("a", "design", {})
        with self.assertRaises(ConflictError):
            self.db.put("a", "strain", {}, expected=a["id"])
        self.assertTrue(self.db.verify()["ok"])

if __name__ == "__main__":
    unittest.main()
