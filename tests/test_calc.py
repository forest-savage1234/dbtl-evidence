from pathlib import Path
import tempfile
import unittest

from dbtl.core import Instrument, IntegrityError
from dbtl.calc import evaluate, titer
from dbtl.ingest import ingest_csv
from .support import setup_assay, write_csv, policy_payload


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Instrument(Path(self.temp.name) / "registry")
        self.parts = setup_assay(self.db)
        self.csv = Path(self.temp.name) / "x.csv"

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def measurement(self, parts=None, **changes):
        parts = parts or self.parts
        base = write_csv(self.csv, parts)
        write_csv(self.csv, parts, rows=[{**base, **changes}])
        return self.db.get(ingest_csv(self.db, self.csv)["measurement_versions"][0])

    def compare(self, measurements, **policy_changes):
        cohort = self.db.capture("cohort:test", "cohort", {"measurement_versions": [m["id"] for m in measurements]})
        policy = self.db.capture("policy:test", "policy", policy_payload(self.parts, **policy_changes))
        return evaluate(self.db, cohort["id"], policy["id"])

    def test_known_calibration_converts_to_g_l(self):
        m = self.measurement()
        self.assertEqual(titer(self.db, m), __import__("decimal").Decimal("0.5"))
        result = self.compare([m])
        self.assertEqual(result["included"][0]["titer_g_l"], "0.5")
        self.assertFalse(result["summaries"][0]["eligible_for_descriptive_ranking"])

    def test_unit_conversion_and_dilution_have_independent_expected_values(self):
        for unit, slope, response, expected in [("g/L", "2", "11", "1"), ("mg/L", "2", "1010", "1"), ("ug/L", "0.002", "1010", "1")]:
            with self.subTest(unit=unit):
                cal = self.db.capture("cal:" + unit.replace("/", ""), "calibration", {**self.parts["calibration"]["payload"], "concentration_unit": unit, "slope": slope})
                parts = {**self.parts, "calibration": cal}
                m = self.measurement(parts, measurement_id="m:" + unit.replace("/", ""), dilution="2", response=response, run_id="run:" + unit.replace("/", ""))
                self.assertEqual(titer(self.db, m), __import__("decimal").Decimal(expected))

    def test_technical_repeats_do_not_inflate_biological_n(self):
        a = self.measurement()
        b = self.measurement(measurement_id="m:tech2", technical_replicate_id="tech:2", response="2010")
        result = self.compare([a, b])
        summary = result["summaries"][0]
        self.assertEqual(summary["biological_n"], 1)
        self.assertEqual(summary["cultures"][0]["technical_n"], 2)
        self.assertEqual(summary["mean_g_l"], "0.75")
        self.assertNotIn("rank", summary)

    def test_two_cultures_are_counted_and_technical_means_weighted_equally(self):
        a = self.measurement()
        bparts = setup_assay(self.db, "B", strain=self.parts["strain"], calibration=self.parts["calibration"], protocol=self.parts["protocol"], extraction=self.parts["extraction"])
        b = self.measurement(bparts, response="2010")
        result = self.compare([a, b])
        self.assertEqual(result["summaries"][0]["biological_n"], 2)
        self.assertEqual(result["summaries"][0]["mean_g_l"], "0.75")
        self.assertEqual(result["summaries"][0]["rank"], 1)

    def test_censored_values_are_excluded_instead_of_replaced_with_zero(self):
        m = self.measurement(quantification="below_loq")
        result = self.compare([m])
        self.assertEqual(result["included"], [])
        self.assertIn("quantification:below_loq", result["excluded"][0]["reasons"])

    def test_out_of_range_values_are_excluded(self):
        m = self.measurement(response="10001")
        result = self.compare([m])
        self.assertIn("outside_declared_calibration_range", result["excluded"][0]["reasons"])

    def test_cross_batch_or_unknown_context_is_not_silently_pooled(self):
        a = self.measurement()
        bparts = setup_assay(self.db, "B", protocol=self.parts["protocol"], extraction=self.parts["extraction"], batch="other", vessel=None)
        b = self.measurement(bparts)
        result = self.compare([a, b])
        self.assertEqual(len(result["included"]), 1)
        self.assertEqual(result["excluded"][0]["reasons"], ["context_mismatch:batch", "missing_context:vessel"])

    def test_fail_qc_and_unverified_genotype_remain_visible(self):
        m = self.measurement(qc="fail")
        result = self.compare([m], genotype_requirement="asserted_verified")
        self.assertIn("qc:fail", result["excluded"][0]["reasons"])
        self.assertIn("genotype_evidence_not_asserted_verified", result["excluded"][0]["reasons"])

    def test_policy_cannot_claim_unimplemented_metric_or_hidden_context(self):
        for changes in [{"metric": "yield"}, {"context": {"medium": "x"}}, {"technical_aggregation": "pooled"}]:
            with self.assertRaises(IntegrityError):
                self.db.capture("policy:bad", "policy", policy_payload(self.parts, **changes))

    def test_duplicate_revision_membership_is_rejected(self):
        m = self.measurement()
        newer = self.db.capture(m["entity_id"], "measurement", m["payload"], expected=m["id"], reason="QC review")
        with self.assertRaises(IntegrityError):
            self.db.capture("cohort:bad", "cohort", {"measurement_versions": [m["id"], newer["id"]]})
