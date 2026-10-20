from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.assessments import DIMENSIONS, assess, summary


def dimensions(status="open", evidence=None):
    return {d: {"status": status, "basis": "SYNTHETIC bounded review", "evidence_versions": evidence or []}
            for d in DIMENSIONS}


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state"
        self.db = Instrument(self.path)
        self.subject = self.db.capture("design:subject", "design", {"name": "SYNTHETIC"})

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_no_assessment_stays_open(self):
        self.assertTrue(all(x["status"] == "open" for x in summary(self.db, self.subject["id"])["dimensions"].values()))

    def test_arithmetic_support_does_not_promote_other_dimensions(self):
        ds = dimensions()
        ds["arithmetic"].update(status="supported", evidence_versions=[self.subject["id"]])
        assess(self.db, "assessment:1", self.subject["id"], ds, criteria_id="synthetic:1")
        result = summary(self.db, self.subject["id"])
        self.assertEqual(result["dimensions"]["arithmetic"]["status"], "supported")
        self.assertEqual(result["dimensions"]["measurement"]["status"], "open")
        self.assertNotIn("verified", result)

    def test_omitted_dimension_is_rejected(self):
        ds = dimensions(); ds.pop("measurement")
        with self.assertRaises(IntegrityError):
            assess(self.db, "assessment:1", self.subject["id"], ds, criteria_id="synthetic:1")

    def test_unsupported_global_status_and_evidenceless_support_are_rejected(self):
        for ds in [dimensions("verified"), dimensions("supported")]:
            with self.assertRaises(IntegrityError):
                assess(self.db, "assessment:1", self.subject["id"], ds, criteria_id="synthetic:1")

    def test_conflict_is_preserved_across_reviewers(self):
        assess(self.db, "assessment:1", self.subject["id"], dimensions("supported", [self.subject["id"]]), criteria_id="synthetic:1")
        assess(self.db, "assessment:2", self.subject["id"], dimensions("conflict"), criteria_id="synthetic:1")
        self.assertEqual(summary(self.db, self.subject["id"])["dimensions"]["arithmetic"]["status"], "conflict")

    def test_superseded_evidence_reopens_supported_assessment(self):
        assess(self.db, "assessment:1", self.subject["id"], dimensions("supported", [self.subject["id"]]), criteria_id="synthetic:1")
        self.db.capture(self.subject["entity_id"], "design", {"name": "corrected"}, expected=self.subject["id"])
        self.assertEqual(summary(self.db, self.subject["id"])["dimensions"]["arithmetic"]["status"], "open")

    def test_additive_upgrade_does_not_rewrite_storage_or_old_records(self):
        old = self.db.get(self.subject["id"])
        self.db.close(); self.db = Instrument(self.path)
        assess(self.db, "assessment:1", self.subject["id"], dimensions(), criteria_id="synthetic:1")
        self.assertEqual(self.db.get(old["id"]), old)
        self.assertEqual(self.db.conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0], "1")
        self.assertTrue(self.db.verify()["ok"])
