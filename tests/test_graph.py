from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.graph import closure, impact, verify_closure
from dbtl.ingest import ingest_csv
from .support import setup_assay, write_csv


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Instrument(self.temp.name)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def link(self, name, *parents):
        return self.db.put(name, "design", {}, dependencies=[{"role": "input", "version_id": p["id"]} for p in parents])

    def test_diamond_counts_descendant_once_and_excludes_unrelated(self):
        a = self.link("a")
        b, c = self.link("b", a), self.link("c", a)
        d = self.link("d", b, c)
        self.link("unrelated")
        result = impact(self.db, a["id"])
        self.assertEqual({r["record"]["entity_id"] for r in result}, {"b", "c", "d"})
        self.assertEqual(len(next(x["path"] for x in result if x["record"]["id"] == d["id"])), 2)
        self.assertEqual(len(closure(self.db, d["id"])), 3)

    def test_forward_or_self_reference_cannot_introduce_cycle(self):
        with self.assertRaises(IntegrityError):
            self.db.put("a", "design", {}, dependencies=[{"role": "input", "version_id": "a"}])
        self.assertEqual(self.db.versions(), [])

    def test_construction_roles_distinguish_strain_from_donor_design(self):
        strain = self.db.put("strain:a", "strain", {})
        donor = self.link("donor")
        with self.assertRaises(IntegrityError):
            self.db.put("activity:bad", "activity", {"operation": "edit"}, dependencies=[{"role": "recipient", "version_id": donor["id"]}])
        activity = self.db.put("activity:ok", "activity", {"operation": "edit"}, dependencies=[
            {"role": "recipient", "version_id": strain["id"]}, {"role": "donor", "version_id": donor["id"]}])
        output = self.db.put("strain:output", "strain", {}, dependencies=[{"role": "built_by", "version_id": activity["id"]}])
        self.assertEqual(len(closure(self.db, output["id"])), 3)

    def test_sample_revision_does_not_allow_duplicate_acquisition(self):
        parts = setup_assay(self.db)
        path = Path(self.temp.name) / "x.csv"
        base = write_csv(path, parts)
        ingest_csv(self.db, path)
        parts["sample"] = self.db.capture(parts["sample"]["entity_id"], "sample", parts["sample"]["payload"], expected=parts["sample"]["id"], reason="metadata correction")
        write_csv(path, parts, rows=[{**base, "sample_version": parts["sample"]["id"], "measurement_id": "renamed"}])
        with self.assertRaises(IntegrityError):
            ingest_csv(self.db, path)

    def test_upstream_missing_evidence_fails_closure_check(self):
        path = Path(self.temp.name) / "raw"
        path.write_text("raw")
        key = self.db.objects.add(path)
        a = self.db.put("a", "design", {}, artifacts=[key])
        b = self.link("b", a)
        self.db.objects.path(key).unlink()
        with self.assertRaises(IntegrityError):
            verify_closure(self.db, b["id"])
