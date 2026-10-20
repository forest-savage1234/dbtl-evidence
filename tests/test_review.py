from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.datasets import freeze, replay
from dbtl.review import findings, acknowledge, recalibrate, refresh_cohort
from .test_datasets import dataset_fixture


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Instrument(Path(self.temp.name) / "registry")
        self.parts, self.imported, self.cohort, self.policy, self.dataset = dataset_fixture(self.db, self.temp.name)
        self.decision = self.db.capture("decision:test", "decision", {"dataset_version": self.dataset["id"],
            "selected_strain_versions": [self.parts["strain"]["id"]], "rationale": "Synthetic descriptive selection; no inference"})

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def correct(self, slope="4"):
        old = self.db.latest(self.parts["calibration"]["entity_id"])
        return self.db.capture(old["entity_id"], "calibration", {**old["payload"], "slope": slope},
                               expected=old["id"], reason="synthetic standard correction")

    def test_only_affected_current_outputs_are_flagged_with_paths(self):
        self.db.put("unrelated", "design", {})
        self.correct()
        queue = findings(self.db)
        self.assertEqual({f["target_kind"] for f in queue}, {"dataset", "decision"})
        self.assertEqual(len(queue), 2)
        self.assertTrue(all(f["path"][0]["source"] == self.parts["calibration"]["id"] for f in queue))
        self.assertEqual(len(next(f["path"] for f in queue if f["target_kind"] == "decision")), 4)

    def test_acknowledgement_does_not_rewrite_or_make_evidence_current(self):
        self.correct()
        finding = findings(self.db)[0]
        review = acknowledge(self.db, finding["finding_id"], disposition="retain_historical", note="Retain original record for audit; do not reuse as current", actor="reviewer:synthetic")
        self.assertEqual(len(findings(self.db)), 1)
        self.assertEqual(review["payload"]["target_version"], finding["target_version"])
        self.assertTrue(replay(self.db, self.dataset["id"])["ok"])
        with self.assertRaises(IntegrityError):
            self.db.capture("decision:stale", "decision", self.decision["payload"])

    def test_next_correction_creates_a_new_review_obligation(self):
        self.correct()
        for finding in findings(self.db):
            acknowledge(self.db, finding["finding_id"], disposition="retain_historical", note="historical only", actor="reviewer")
        self.assertEqual(findings(self.db), [])
        self.correct("8")
        self.assertEqual(len(findings(self.db)), 2)

    def test_explicit_recalibration_and_refresh_create_new_dataset(self):
        calibration = self.correct()
        m = self.imported["measurement_versions"][0]
        updated = recalibrate(self.db, m, calibration["id"], actor="reviewer", reason="apply corrected standard")
        self.assertEqual(self.db.get(m)["payload"]["calibration_version"], self.parts["calibration"]["id"])
        cohort = refresh_cohort(self.db, self.cohort["id"], actor="reviewer", reason="replace revised members")
        dataset = freeze(self.db, self.dataset["entity_id"], cohort["id"], self.policy["id"], expected=self.dataset["id"], reason="recomputed after correction")
        self.assertEqual(dataset["payload"]["result"]["included"][0]["titer_g_l"], "0.25")
        self.assertTrue(replay(self.db, self.dataset["id"])["ok"])
        self.assertTrue(replay(self.db, dataset["id"])["ok"])
        self.assertTrue(any(f["target_kind"] == "decision" for f in findings(self.db)))

    def test_review_cannot_claim_unrelated_dependency_or_empty_reason(self):
        self.correct()
        finding = findings(self.db)[0]
        with self.assertRaises(IntegrityError):
            acknowledge(self.db, finding["finding_id"], disposition="retain_historical", note="", actor="reviewer")
        with self.assertRaises(IntegrityError):
            acknowledge(self.db, "nonexistent", disposition="retire", note="note", actor="reviewer")

    def test_new_independent_results_require_explicit_cohort_membership(self):
        before = self.dataset["payload"]["result_sha256"]
        self.db.put("independent:report", "design", {"note": "not yet adjudicated into this cohort"})
        self.assertEqual(findings(self.db), [])
        self.assertEqual(replay(self.db, self.dataset["id"])["result_sha256"], before)

    def test_new_decision_cannot_select_a_strain_outside_the_dataset(self):
        other = self.db.put("strain:other", "strain", {})
        with self.assertRaises(IntegrityError):
            self.db.capture("decision:bad", "decision", {**self.decision["payload"], "selected_strain_versions": [other["id"]]})
