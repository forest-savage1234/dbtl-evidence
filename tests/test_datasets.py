from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dbtl.core import Instrument, IntegrityError
from dbtl.ingest import ingest_csv
from dbtl.datasets import freeze, replay, source_manifest
from dbtl.calc import evaluate
from .support import setup_assay, write_csv, policy_payload


def dataset_fixture(db, root):
    parts = setup_assay(db)
    path = Path(root) / "x.csv"
    write_csv(path, parts)
    imported = ingest_csv(db, path)
    cohort = db.capture("cohort:test", "cohort", {"measurement_versions": imported["measurement_versions"]})
    policy = db.capture("policy:test", "policy", policy_payload(parts, min_biological_replicates=1))
    dataset = freeze(db, "dataset:test", cohort["id"], policy["id"])
    return parts, imported, cohort, policy, dataset


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Instrument(Path(self.temp.name) / "registry")
        self.parts, self.imported, self.cohort, self.policy, self.dataset = dataset_fixture(self.db, self.temp.name)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_exact_replay_has_same_fingerprint(self):
        report = replay(self.db, self.dataset["id"])
        self.assertTrue(report["ok"])
        self.assertEqual(report["result_sha256"], self.dataset["payload"]["result_sha256"])
        self.assertEqual(report["stale_inputs"], [])

    def test_calibration_correction_preserves_historical_replay_but_blocks_current_reuse(self):
        old = self.parts["calibration"]
        self.db.capture(old["entity_id"], "calibration", {**old["payload"], "slope": "4"}, expected=old["id"], reason="corrected standard")
        report = replay(self.db, self.dataset["id"])
        self.assertTrue(report["ok"])
        self.assertIn(old["id"], [s["old"] for s in report["stale_inputs"]])
        with self.assertRaises(IntegrityError):
            evaluate(self.db, self.cohort["id"], self.policy["id"])

    def test_wrong_implementation_blocks_replay_even_if_numbers_happen_to_match(self):
        different = {**source_manifest(), "algorithm_id": "something-else"}
        with patch("dbtl.datasets.source_manifest", return_value=different):
            with self.assertRaises(IntegrityError):
                replay(self.db, self.dataset["id"])

    def test_corrupt_raw_artifact_blocks_replay(self):
        raw = self.db.get(self.imported["import_version"])["payload"]["source_digest"]
        self.db.objects.path(raw).write_text("changed")
        with self.assertRaises(IntegrityError):
            replay(self.db, self.dataset["id"])

    def test_manually_forged_result_cannot_be_registered_as_dataset(self):
        payload = {**self.dataset["payload"], "result_sha256": "0" * 64}
        with self.assertRaises(IntegrityError):
            self.db.capture("dataset:forged", "dataset", payload, artifacts=self.dataset["artifacts"])

    def test_excluded_candidate_remains_in_dependency_closure(self):
        from dbtl.graph import closure
        members = {r["id"] for r in closure(self.db, self.dataset["id"])}
        self.assertTrue(set(self.imported["measurement_versions"]) <= members)

    def test_protocol_references_are_sealed_into_policy_graph(self):
        from dbtl.graph import closure
        self.assertIn(self.parts["protocol"]["id"], {r["id"] for r in closure(self.db, self.policy["id"])})
